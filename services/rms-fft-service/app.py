# =============================================
# RMS + FFT SERVICE
# ---------------------------------------------
# 1) Reads vibration data (ax, ay, az) from Azure Event Hubs
# 2) Calculates RMS and FFT features per axis
# 3) Writes results to InfluxDB (bucket: machine_health)
# =============================================

import os
import json
import numpy as np
from azure.eventhub import EventHubConsumerClient
from influxdb_client import InfluxDBClient, Point, WritePrecision

# ---------- 1) Environment Variables ----------
EVENT_HUBS_CONN = os.getenv("EVENT_HUBS_CONN")
EVENT_HUBS_TOPIC = os.getenv("EVENT_HUBS_TOPIC", "sensors/vibration")
INFLUX_URL      = os.getenv("INFLUX_URL")
INFLUX_TOKEN    = os.getenv("INFLUX_TOKEN")
INFLUX_ORG      = os.getenv("INFLUX_ORG")
INFLUX_BUCKET   = os.getenv("INFLUX_BUCKET", "machine_health")
MEASUREMENT_NAME= os.getenv("MEASUREMENT_NAME", "signal_features")
BAND_LOW_HZ     = int(os.getenv("BAND_LOW_HZ", 0))
BAND_HIGH_HZ    = int(os.getenv("BAND_HIGH_HZ", 200))

# ---------- 2) InfluxDB Client Setup ----------
influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx.write_api()

# ---------- 3) RMS & FFT Helper Functions ----------
def rms(x):
    """Calculate Root Mean Square (RMS) of a signal array."""
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else np.nan

def fft_features(sig, fs, band_low=BAND_LOW_HZ, band_high=BAND_HIGH_HZ):
    """
    Extract FFT features from a signal.
    
    Args:
        sig: Signal array
        fs: Sampling frequency in Hz
        band_low: Lower frequency bound for band energy calculation
        band_high: Upper frequency bound for band energy calculation
    
    Returns:
        tuple: (peak_frequency, band_energy)
    """
    sig = np.array(sig, dtype=float)
    if len(sig) == 0 or fs is None or fs <= 0:
        return np.nan, np.nan
    
    N = len(sig)
    freqs = np.fft.rfftfreq(N, d=1.0/fs)
    fft_vals = np.abs(np.fft.rfft(sig))
    
    # Find peak frequency (highest amplitude)
    peak_freq = float(freqs[np.argmax(fft_vals)])
    
    # Calculate energy in specified frequency band
    band_mask = (freqs >= band_low) & (freqs <= band_high)
    band_energy = float(np.sum(fft_vals[band_mask] ** 2))
    
    return peak_freq, band_energy

# ---------- 4) Event Handler ----------
def on_event(partition_context, event):
    """
    Process incoming Event Hub messages containing vibration data.
    Supports two modes:
    - Mode A: Pre-computed features (feature_1, feature_2, etc.)
    - Mode B: Raw signals (ax, ay, az) that need RMS/FFT calculation
    """
    try:
        data = json.loads(event.body_as_str())

        # Device ID fallback strategy - try multiple field names
        device_id = (
            data.get("device_id")
            or data.get("sensor_id")
            or data.get("id")
            or f"eh-partition-{partition_context.partition_id}"
        )

        # --------- MODE A: Pre-computed features (feature_1..N) ----------
        feature_keys = [k for k in data.keys() if k.startswith("feature_")]
        if feature_keys:
            # Sort features numerically (feature_1, feature_2, ...)
            feature_keys.sort(key=lambda k: int(k.split("_")[1]) if k.split("_")[1].isdigit() else 0)

            # Build field dictionary, keeping only finite numeric values
            fields = {}
            for k in feature_keys:
                v = data.get(k)
                if isinstance(v, (int, float)) and np.isfinite(v):
                    fields[k] = float(v)

            if not fields:
                print(f"⚠️  Skipped write (no numeric features) for {device_id} @ {event.enqueued_time}")
                return

            # Write pre-computed features to InfluxDB
            point = Point(MEASUREMENT_NAME).tag("device_id", device_id).time(event.enqueued_time, WritePrecision.NS)
            for k, v in fields.items():
                point = point.field(k, v)

            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            print(f"✅ Wrote {len(fields)} precomputed features for {device_id} @ {event.enqueued_time}")
            return  # Done processing this event

        # --------- MODE B: Raw signals (ax/ay/az) → compute RMS/FFT ----------
        fs = int(data.get("fs", 6400))  # Default sampling frequency: 6400 Hz

        def pick_axis(d, candidates):
            """
            Extract axis data from various possible JSON structures.
            Tries direct keys first, then nested structures.
            """
            # Try direct access to axis data
            for k in candidates:
                if k in d:
                    v = d[k]
                    if isinstance(v, list): return v
                    if isinstance(v, (int, float)): return [v]
            
            # Try nested structures (axes, acc, accel, acceleration)
            for parent in ("axes", "acc", "accel", "acceleration"):
                v = d.get(parent)
                if isinstance(v, dict):
                    for k in candidates:
                        if k in v:
                            vv = v[k]
                            if isinstance(vv, list): return vv
                            if isinstance(vv, (int, float)): return [vv]
            return []

        # Extract acceleration data for each axis
        ax = pick_axis(data, ("ax", "x"))
        ay = pick_axis(data, ("ay", "y"))
        az = pick_axis(data, ("az", "z"))

        nax, nay, naz = len(ax), len(ay), len(az)
        
        # Validation checks
        if fs <= 0:
            print(f"ℹ️ Skip: invalid sampling frequency fs={fs} for {device_id} @ {event.enqueued_time}; keys={list(data.keys())}")
            return
        if (nax + nay + naz) == 0:
            print(f"ℹ️ Skip: no signal samples found (keys={list(data.keys())}) for {device_id} @ {event.enqueued_time}")
            return

        # Calculate signal features for each axis
        rms_ax = rms(ax); rms_ay = rms(ay); rms_az = rms(az)
        peak_ax, band_ax = fft_features(ax, fs)
        peak_ay, band_ay = fft_features(ay, fs)
        peak_az, band_az = fft_features(az, fs)

        # Prepare data fields for InfluxDB
        fields = {
            "rms_ax": rms_ax, "rms_ay": rms_ay, "rms_az": rms_az,
            "peak_freq_ax": peak_ax, "peak_freq_ay": peak_ay, "peak_freq_az": peak_az,
            "bandE0_200_ax": band_ax, "bandE0_200_ay": band_ay, "bandE0_200_az": band_az,
        }
        
        # Filter out NaN and infinite values
        clean = {k: float(v) for k, v in fields.items() if v is not None and np.isfinite(v)}
        if not clean:
            print(f"⚠️  Skipped write for {device_id} (no finite fields) @ {event.enqueued_time}")
            return

        # Write computed features to InfluxDB
        point = Point(MEASUREMENT_NAME).tag("device_id", device_id).time(event.enqueued_time, WritePrecision.NS)
        for k, v in clean.items():
            point = point.field(k, v)

        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        print(f"✅ Wrote computed features for {device_id} @ {event.enqueued_time}")

    except Exception as e:
        print(f"❌ Error processing event: {e}")


# ---------- 5) Start Event Hub Listener ----------
if __name__ == "__main__":
    print("🚀 Starting RMS+FFT Service ...")
    consumer_client = EventHubConsumerClient.from_connection_string(
        conn_str=EVENT_HUBS_CONN,
        consumer_group="$Default",
        eventhub_name=EVENT_HUBS_TOPIC,
    )
    try:
        with consumer_client:
            consumer_client.receive(
                on_event=on_event,
                # ✅ Process only NEW events (not historical data)
                starting_position="@latest",
            )
    except KeyboardInterrupt:
        print("🛑 Stopped by user")
    finally:
        consumer_client.close()
        influx.close()

# Note: This duplicate function definition should be removed
# The main rms function is already defined above with proper error handling




