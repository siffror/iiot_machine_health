# -*- coding: utf-8 -*-
"""
Replayer: publishes feature rows from a Parquet file to Azure Event Hubs.

Purpose
-------
- Load a Parquet file (from Azure Blob Storage) into a pandas DataFrame.
- Select feature columns either explicitly (FEATURE_KEYS) or automatically (numeric columns).
- Convert each row to an event payload and send in batches to Event Hubs.
- Optionally loop the entire dataset to simulate a live stream.

Environment variables
---------------------
- EVENT_HUB_NAMESPACE_FQDN: Event Hubs namespace FQDN (e.g., "example.servicebus.windows.net").
- EVENT_HUB_NAME: Event Hub name to publish to.
- STORAGE_ACCOUNT_NAME: Azure Storage account name hosting the Parquet blob.
- SENSOR_CONTAINER_NAME: Blob container name.
- SENSOR_FILE_PATH: Path to the Parquet blob (within the container).
- FEATURE_KEYS: Comma-separated list of column names to use as features. If empty, auto-detect.
- FEATURE_COUNT: If > 0 and FEATURE_KEYS is empty, pick the first N numeric columns.
- BATCH_SIZE: Number of events per batch to Event Hubs.
- DELAY_SEC: Sleep seconds between batches.
- LOOP: If true, replay the dataset continuously; otherwise stop after one pass.
- SENSOR_IDS: Comma-separated list of sensor IDs to round-robin across rows when no column provided.
- SENSOR_ID_COLUMN: Optional column name to read sensor_id from; if not set, round-robin is used.
- TIMESTAMP_COLUMN: Optional column name containing timestamp (seconds, ms, µs, or ns).
- OUTPUT_FEATURE_PREFIX: Prefix for output feature keys (e.g., "feature_" -> feature_1..feature_N).

Notes
-----
- Authentication uses DefaultAzureCredential; ensure your environment can authenticate to Azure.
- This module does not transform feature values beyond casting to float; upstream should ensure schema.
"""
import os, io, time, json, math
import numpy as np
import pandas as pd

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient
from azure.eventhub import EventHubProducerClient, EventData

# ===== ENV =====
EH_FQDN  = os.getenv("EVENT_HUB_NAMESPACE_FQDN", "")            # e.g., my-eh-namespace.servicebus.windows.net
EH_NAME  = os.getenv("EVENT_HUB_NAME", "sensor-data-stream")

STG_ACC  = os.getenv("STORAGE_ACCOUNT_NAME", "iiotpocstorage")
SRC_CONT = os.getenv("SENSOR_CONTAINER_NAME", "sensor-data")
SRC_BLOB = os.getenv("SENSOR_FILE_PATH", "features_train.parquet")

# Feature keys to publish (should match the scorer's expected FEATURE_KEYS).
# If empty → the first N numeric columns will be auto-detected.
FEATURE_KEYS = [k.strip() for k in os.getenv("FEATURE_KEYS", "").split(",") if k.strip()]
FEATURE_COUNT = int(os.getenv("FEATURE_COUNT", "0"))  # if > 0 and FEATURE_KEYS is empty → take that many numeric columns

# Replay schedule
BATCH_SIZE  = int(os.getenv("BATCH_SIZE", "100"))     # number of events per batch to Event Hubs
DELAY_SEC   = float(os.getenv("DELAY_SEC", "0.5"))    # pause between batches (seconds)
LOOP        = os.getenv("LOOP", "true").lower() in ("1","true","yes","y")  # loop the file continuously
SENSOR_IDS  = [s.strip() for s in os.getenv("SENSOR_IDS", "sim-1").split(",") if s.strip()]  # round-robin mapping of rows to sensor IDs
SENSOR_COL  = os.getenv("SENSOR_ID_COLUMN", "")       # if set, read sensor_id from this column
TS_COL      = os.getenv("TIMESTAMP_COLUMN", "")       # if set, read timestamp from this column; otherwise use time.time()

# The scorer expects keys feature_1..feature_N
OUTPUT_FEATURE_PREFIX = os.getenv("OUTPUT_FEATURE_PREFIX", "feature_")

credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)

def _download_parquet_to_df() -> pd.DataFrame:
    """Download the configured Parquet file from Azure Blob Storage and return it as a DataFrame."""
    print(f"I! Reading Parquet from https://{STG_ACC}.blob.core.windows.net/{SRC_CONT}/{SRC_BLOB}")
    bc = BlobClient(
        account_url=f"https://{STG_ACC}.blob.core.windows.net",
        container_name=SRC_CONT,
        blob_name=SRC_BLOB,
        credential=credential
    )
    data = bc.download_blob().readall()
    df = pd.read_parquet(io.BytesIO(data))
    print(f"I! Parquet loaded: shape={df.shape}, columns={list(df.columns)}")
    return df

def _select_feature_columns(df: pd.DataFrame) -> list[str]:
    """
    Choose which DataFrame columns will be published as features.

    Priority:
    1) If FEATURE_KEYS provided, validate and use them.
    2) Else if FEATURE_COUNT > 0, take the first N numeric columns.
    3) Else take all numeric columns.
    """
    if FEATURE_KEYS:
        missing = [c for c in FEATURE_KEYS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing feature columns in source file: {missing}")
        return FEATURE_KEYS

    # Auto: take numeric columns
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if FEATURE_COUNT > 0:
        if len(num_cols) < FEATURE_COUNT:
            raise ValueError(f"Found only {len(num_cols)} numeric columns but FEATURE_COUNT={FEATURE_COUNT}.")
        return num_cols[:FEATURE_COUNT]
    # Fallback: all numeric columns
    if not num_cols:
        raise ValueError("No numeric columns found. Provide FEATURE_KEYS or FEATURE_COUNT.")
    return num_cols

def _row_to_event(row: pd.Series, feature_cols: list[str], row_idx: int) -> dict:
    """
    Convert a DataFrame row to an event payload with schema:
    {
      "sensor_id": str,
      "timestamp": float (seconds),
      "feature_1": float,
      ...,
      "feature_N": float
    }

    - sensor_id: read from SENSOR_COL if present; otherwise round-robin across SENSOR_IDS.
    - timestamp: read from TS_COL if present; supports seconds/ms/µs/ns; otherwise time.time().
    - features: values from feature_cols cast to float; non-castable become 0.0.
    """
    # sensor_id
    if SENSOR_COL and SENSOR_COL in row.index and pd.notnull(row[SENSOR_COL]):
        sensor_id = str(row[SENSOR_COL])
    else:
        # Round-robin across configured SENSOR_IDS
        sensor_id = SENSOR_IDS[row_idx % len(SENSOR_IDS)]

    # timestamp
    if TS_COL and TS_COL in row.index and pd.notnull(row[TS_COL]):
        ts_val = row[TS_COL]
        # Support for ns/µs/ms/seconds. We normalize to seconds (float).
        try:
            ts = float(ts_val)
            # Heuristic: >1e12 → ns, >1e9 → ms, >1e6 → µs, otherwise seconds
            if ts > 1e12:
                ts = ts / 1e9
            elif ts > 1e9:
                ts = ts / 1e3
            elif ts > 1e6:
                ts = ts / 1e6
        except Exception:
            ts = time.time()
    else:
        ts = time.time()

    # Map features to feature_1..feature_N (or custom prefix)
    payload = {
        "sensor_id": sensor_id,
        "timestamp": ts
    }
    for i, col in enumerate(feature_cols, start=1):
        key = f"{OUTPUT_FEATURE_PREFIX}{i}"
        try:
            payload[key] = float(row[col])
        except Exception:
            payload[key] = 0.0

    return payload

def replay_once(df: pd.DataFrame, producer: EventHubProducerClient, feature_cols: list[str]):
    """Send the DataFrame rows once to Event Hubs in batches, preserving row order."""
    if df.empty:
        print("W! DataFrame is empty — nothing to send.")
        return

    total = len(df)
    batches = math.ceil(total / BATCH_SIZE)

    print(f"I! Replay starting: total_rows={total}, batch_size={BATCH_SIZE}, batches={batches}")
    idx = 0
    for b in range(batches):
        start = b * BATCH_SIZE
        end = min((b+1) * BATCH_SIZE, total)
        subset = df.iloc[start:end]

        events = []
        for _, row in subset.iterrows():
            event_dict = _row_to_event(row, feature_cols, idx)
            events.append(EventData(json.dumps(event_dict)))
            idx += 1

        if events:
            producer.send_batch(events)
            print(f"I! Sent batch {b+1}/{batches} (events={len(events)})")
        if DELAY_SEC > 0:
            time.sleep(DELAY_SEC)

def main():
    """Entry point: load data, select features, and start the replay loop."""
    df = _download_parquet_to_df()
    feature_cols = _select_feature_columns(df)
    print(f"I! Features to send ({len(feature_cols)}): {feature_cols}")
    print(f"I! Output keys in event: {OUTPUT_FEATURE_PREFIX}1..{OUTPUT_FEATURE_PREFIX}{len(feature_cols)}")
    print(f"I! Sensors: {SENSOR_IDS}; LOOP={LOOP}, BATCH_SIZE={BATCH_SIZE}, DELAY_SEC={DELAY_SEC}")

    producer = EventHubProducerClient(
        fully_qualified_namespace=EH_FQDN,
        eventhub_name=EH_NAME,
        credential=credential
    )

    try:
        while True:
            replay_once(df, producer, feature_cols)
            if not LOOP:
                break
            print("I! Replay complete — looping from start…")
    except KeyboardInterrupt:
        print("I! Stopping replayer (Ctrl+C).")
    finally:
        try: producer.close()
        except Exception: pass

if __name__ == "__main__":
    main()

