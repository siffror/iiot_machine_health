# -*- coding: utf-8 -*-
"""
Anomaly Scoring Service for IIoT Vibration Data

This service:
1. Loads a pre-trained ML model from Azure Blob Storage
2. Consumes feature data from Azure Event Hubs
3. Scores each event for anomalies using the ML model
4. Writes anomaly scores to InfluxDB for monitoring and alerting

The service supports various ML model types (Isolation Forest, One-Class SVM, etc.)
and handles different feature configurations dynamically.
"""

import os, json, time, pickle
from io import BytesIO

import numpy as np
import pandas as pd
from joblib import load as joblib_load
from sklearn.pipeline import make_pipeline

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient
from azure.eventhub import EventHubConsumerClient

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ============================================================================
# FEATURE CONFIGURATION
# ============================================================================
# Comma-separated list of feature keys to extract from incoming events
# Example: "feature_1,feature_2,feature_3,feature_4,feature_5,feature_6"
FEATURE_KEYS = os.getenv("FEATURE_KEYS")

def _infer_expected_features(model):
    """
    Attempt to determine how many features the model was trained with.
    
    This function inspects the model object to find the expected number of input features.
    It handles both direct model objects and sklearn pipelines.
    
    Args:
        model: The ML model object (sklearn estimator or pipeline)
        
    Returns:
        int or None: Number of expected features, or None if cannot be determined
    """
    # Check if model has direct n_features_in_ attribute (sklearn 0.24+)
    if hasattr(model, "n_features_in_"):
        return int(model.n_features_in_)
    
    # For pipelines, check each step for n_features_in_
    if hasattr(model, "named_steps"):
        for step in model.named_steps.values():
            if hasattr(step, "n_features_in_"):
                return int(step.n_features_in_)
    
    return None

# ============================================================================
# ENVIRONMENT VARIABLE VALIDATION
# ============================================================================

def _getenv(name: str, required: bool = True, default=None):
    """
    Get environment variable with validation.
    
    Args:
        name: Environment variable name
        required: Whether the variable is required (raises error if missing)
        default: Default value if variable is not set
        
    Returns:
        str: The environment variable value
        
    Raises:
        ValueError: If required variable is missing
    """
    val = os.getenv(name, default)
    if required and not val:
        raise ValueError(f"Missing required environment variable: {name}")
    return val

# Azure Event Hubs configuration
EVENT_HUB_NAMESPACE_FQDN = _getenv("EVENT_HUB_NAMESPACE_FQDN")  # e.g., "mynamespace.servicebus.windows.net"
EVENT_HUB_NAME           = _getenv("EVENT_HUB_NAME")            # Event Hub name for feature data

# Azure Blob Storage configuration for ML model
STORAGE_ACCOUNT_NAME = _getenv("STORAGE_ACCOUNT_NAME")  # Storage account containing the model
MODEL_CONTAINER_NAME = _getenv("MODEL_CONTAINER_NAME")  # Container name (e.g., "models")
MODEL_FILE_PATH      = _getenv("MODEL_FILE_PATH")       # Path to model file (e.g., "iforest_final.joblib")

# InfluxDB configuration for anomaly score storage
INFLUXDB_URL    = _getenv("INFLUXDB_URL")     # InfluxDB instance URL
INFLUXDB_ORG    = _getenv("INFLUXDB_ORG")     # InfluxDB organization
INFLUXDB_BUCKET = _getenv("INFLUXDB_BUCKET")  # Bucket for anomaly scores
# Strip whitespace to avoid invalid headers due to line breaks
INFLUXDB_TOKEN  = _getenv("INFLUXDB_TOKEN").strip()

# Azure authentication credential (uses managed identity in production)
credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)

# ============================================================================
# MODEL HANDLING UTILITIES
# ============================================================================
def _normalize_model(model_obj):
    """
    Extract the actual model from various storage formats.
    
    ML models can be stored in different formats:
    - Direct model object
    - Dictionary with 'pipeline', 'model', or 'clf' keys
    - Dictionary with separate 'scaler' and 'clf' components
    
    Args:
        model_obj: The loaded model object (could be dict or direct model)
        
    Returns:
        The actual ML model object ready for scoring
    """
    if isinstance(model_obj, dict):
        # Try to extract pipeline first
        if model_obj.get("pipeline") is not None:
            return model_obj["pipeline"]
        
        # Try to extract direct model
        if model_obj.get("model") is not None:
            return model_obj["model"]
        
        # Try to build pipeline from separate scaler and classifier
        if "clf" in model_obj and "scaler" in model_obj and model_obj["clf"] is not None:
            return make_pipeline(model_obj["scaler"], model_obj["clf"])
        
        # Try to extract classifier only
        if model_obj.get("clf") is not None:
            return model_obj["clf"]
    
    # Return as-is if already a model object
    return model_obj

def _score_one(model, X):
    """
    Get anomaly score from various types of ML models.
    
    Different ML models have different scoring methods:
    - Isolation Forest: decision_function (negative values = more anomalous)
    - One-Class SVM: decision_function 
    - Local Outlier Factor: score_samples
    - Classification models: predict_proba
    - Generic models: predict
    
    Args:
        model: The ML model object
        X: Feature matrix (single row for one prediction)
        
    Returns:
        float: Anomaly score (interpretation depends on model type)
        
    Raises:
        TypeError: If model type is not supported
    """
    # Isolation Forest, One-Class SVM (higher values = more normal)
    if hasattr(model, "decision_function"):
        return float(model.decision_function(X)[0])
    
    # Local Outlier Factor (lower values = more anomalous)
    if hasattr(model, "score_samples"):
        return float(model.score_samples(X)[0])
    
    # Classification models with probability output
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[0]
        try:
            # For binary classification, return probability of anomaly class
            return float(proba[1])
        except Exception:
            # For single probability output
            return float(proba)
    
    # Generic prediction (regression or simple classification)
    if hasattr(model, "predict"):
        return float(model.predict(X)[0])
    
    raise TypeError(f"Unsupported model type: {type(model)}")

# ============================================================================
# MODEL LOADING FROM AZURE BLOB STORAGE
# ============================================================================

def load_ml_model():
    """
    Load the pre-trained ML model from Azure Blob Storage.
    
    The model can be stored in either joblib or pickle format.
    This function tries joblib first (recommended for sklearn models),
    then falls back to pickle if joblib fails.
    
    Returns:
        ML model object ready for scoring
        
    Raises:
        Exception: If model cannot be loaded with either method
    """
    print("🔄 Starting model loading...")
    blob_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{MODEL_CONTAINER_NAME}/{MODEL_FILE_PATH}"
    print(f"📍 Source: {blob_url}")

    # Create blob client with managed identity authentication
    blob_client = BlobClient(
        account_url=f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
        container_name=MODEL_CONTAINER_NAME,
        blob_name=MODEL_FILE_PATH,
        credential=credential,
    )
    
    # Download model data from blob storage
    model_data = blob_client.download_blob().readall()
    print(f"✅ Downloaded {len(model_data)} bytes from Blob Storage")

    # Try to load with joblib first (preferred for sklearn models)
    try:
        model = joblib_load(BytesIO(model_data))
        print("✅ Model loaded successfully with joblib")
    except Exception as e:
        print(f"⚠️  Joblib loading failed ({e}). Trying pickle...")
        # Fall back to pickle if joblib fails
        model = pickle.loads(model_data)
        print("✅ Model loaded successfully with pickle")

    # Normalize the model object (handle different storage formats)
    model = _normalize_model(model)
    print(f"✅ Normalized model type: {type(model)}")
    return model

def create_influxdb_writer():
    """
    Create InfluxDB client and write API for storing anomaly scores.
    
    Uses synchronous writing to ensure data is written immediately.
    This is important for real-time anomaly detection alerts.
    
    Returns:
        tuple: (InfluxDB client, write API object)
    """
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    return client, write_api

def process_event(event_data, model, write_api, expected_n=None):
    """
    Process a single event from Event Hubs and generate anomaly score.
    
    This function:
    1. Extracts features from the event data
    2. Validates feature count against model expectations
    3. Scores the features using the ML model
    4. Writes the anomaly score to InfluxDB
    
    Args:
        event_data: Event Hub event containing feature data
        model: Pre-trained ML model for scoring
        write_api: InfluxDB write API object
        expected_n: Expected number of features (for validation)
    """
    try:
        # Parse JSON data from Event Hub message
        data = json.loads(event_data.body_as_str())

        # Determine feature extraction order
        # Priority: FEATURE_KEYS env variable, then default feature_1..feature_32
        if FEATURE_KEYS:
            # Use explicitly configured feature keys
            feature_keys = [k.strip() for k in FEATURE_KEYS.split(",") if k.strip()]
        else:
            # Use default feature naming convention (up to 32 features)
            feature_keys = [f"feature_{i}" for i in range(1, 33)]

        # Extract feature values from event data (default to 0.0 if missing)
        feature_values = [float(data.get(key, 0.0)) for key in feature_keys]

        # Validate feature count against model expectations
        if expected_n is not None:
            if len(feature_values) < expected_n:
                raise ValueError(f"Got {len(feature_values)} features but model requires {expected_n}")
            if len(feature_values) > expected_n:
                print(f"⚠️  Got {len(feature_values)} features, model requires {expected_n}. Extra features ignored.")
            # Truncate to expected number of features
            feature_values = feature_values[:expected_n]

        # Create feature matrix for model input (single row)
        X = pd.DataFrame([feature_values])

        # Generate anomaly score using the ML model
        anomaly_score = _score_one(model, X)
        
        # Extract sensor identifier from event data
        sensor_id = str(data.get("sensor_id", "unknown"))

        print(f"📊 Scored event: Score={anomaly_score:.4f}, sensor={sensor_id}, features_used={len(feature_values)}")

        # Write anomaly score to InfluxDB
        # Note: No explicit timestamp - InfluxDB will use current write time
        point = (
            Point("anomaly_score")
            .tag("sensor_id", sensor_id)
            .field("score", float(anomaly_score))
        )
        write_api.write(bucket=INFLUXDB_BUCKET, record=point, write_precision=WritePrecision.NS)
        print("✅ Anomaly score written to InfluxDB")
        
    except Exception as e:
        print(f"❌ Failed to process event: {e}")

def run_ml_service():
    """
    Main service function that orchestrates the anomaly scoring pipeline.
    
    This function:
    1. Loads the ML model from Azure Blob Storage
    2. Sets up InfluxDB connection for score storage
    3. Creates Event Hub consumer for incoming feature data
    4. Processes events in batches for optimal performance
    5. Handles graceful shutdown on interruption
    """
    print("🚀 Starting ML Anomaly Scoring Service...")
    print(f"🔧 Configuration check:")
    print(f"   Event Hub: {EVENT_HUB_NAMESPACE_FQDN}/{EVENT_HUB_NAME}")
    print(f"   Storage: {STORAGE_ACCOUNT_NAME}/{MODEL_CONTAINER_NAME}/{MODEL_FILE_PATH}")
    print(f"   InfluxDB: {INFLUXDB_URL}/{INFLUXDB_BUCKET}")

    # Load and prepare the ML model
    model = load_ml_model()
    expected_features = _infer_expected_features(model)
    print(f"🧠 Model expects {expected_features} input features")

    # Set up InfluxDB connection for writing anomaly scores
    influx_client, write_api = create_influxdb_writer()

    # Create Event Hub consumer for feature data
    event_consumer = EventHubConsumerClient(
        fully_qualified_namespace=EVENT_HUB_NAMESPACE_FQDN,
        eventhub_name=EVENT_HUB_NAME,
        consumer_group="$Default",
        credential=credential,
    )

    def on_event_batch(partition_context, events):
        """
        Process a batch of events from Event Hubs.
        
        Batch processing improves throughput and allows for checkpoint updates
        after processing multiple events together.
        """
        if not events:
            return
        
        # Process each event in the batch
        for event in events:
            process_event(event, model, write_api, expected_n=expected_features)
        
        # Update checkpoint after processing the entire batch
        # This ensures we don't reprocess events if the service restarts
        partition_context.update_checkpoint(events[-1])

    print(f"👂 Listening for events on Event Hub: {EVENT_HUB_NAME}...")
    
    try:
        # Start consuming events in batch mode
        event_consumer.receive_batch(
            on_event_batch=on_event_batch,
            starting_position="-1",  # Start from the end (latest events)
            max_batch_size=100,      # Process up to 100 events per batch
            prefetch_count=1000,     # Prefetch events for better performance
        )
    except KeyboardInterrupt:
        print("🛑 Stopping ML Scoring Service (user interrupted)")
    finally:
        # Clean up resources
        print("🧹 Cleaning up resources...")
        try: 
            event_consumer.close()
        except Exception: 
            pass
        try: 
            influx_client.close()
        except Exception: 
            pass
        print("✅ Service stopped gracefully")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """
    Entry point for the anomaly scoring service.
    
    This service is designed to run as a containerized microservice in 
    Azure Container Instances or Kubernetes, continuously processing
    feature data and generating real-time anomaly scores.
    """
    run_ml_service()

