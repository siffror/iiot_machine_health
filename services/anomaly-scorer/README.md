# Anomaly Scorer Service

A real-time machine learning microservice for Industrial IoT (IIoT) applications that performs anomaly detection on sensor feature data using pre-trained ML models. The service consumes feature data from Azure Event Hubs, scores each event for anomalies, and stores results in InfluxDB for monitoring and alerting.

## 📋 Overview

This service acts as the intelligence layer in your IIoT pipeline, applying machine learning models to detect equipment anomalies in real-time. It's designed to work seamlessly with the RMS+FFT Service and Data Replayer to provide comprehensive machine health monitoring.

### Key Features

- **Real-time ML Scoring**: Processes feature streams from Azure Event Hubs
- **Multiple ML Model Support**: Works with various scikit-learn models (Isolation Forest, One-Class SVM, LOF, etc.)
- **Azure Blob Model Storage**: Loads pre-trained models from Azure Blob Storage
- **Flexible Feature Handling**: Supports configurable feature sets and automatic detection
- **Model Format Support**: Handles both joblib and pickle model formats
- **Batch Processing**: Optimized batch event processing with checkpointing
- **Time-series Storage**: Writes anomaly scores to InfluxDB with sensor tagging
- **Production Ready**: Built for containerized deployment with proper error handling

## 🏗️ Architecture

```
Azure Blob Storage → Anomaly Scorer ← Azure Event Hubs → InfluxDB
  (ML Models)         (Inference)      (Feature Data)    (Scores)
```

## 🚀 Quick Start

### Prerequisites

- Docker (for containerized deployment)
- Azure Blob Storage with trained ML model
- Azure Event Hubs with feature data stream
- InfluxDB instance for score storage
- Azure authentication configured (Service Principal, Managed Identity, or Azure CLI)
- Python 3.10+ (for local development)

### Environment Variables

Configure the following environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `EVENT_HUB_NAMESPACE_FQDN` | Event Hubs namespace FQDN | `myns.servicebus.windows.net` |
| `EVENT_HUB_NAME` | Event Hub name for feature data | `sensor-features` |
| `STORAGE_ACCOUNT_NAME` | Azure Storage account name | `iiotmodelstorage` |
| `MODEL_CONTAINER_NAME` | Blob container with ML model | `models` |
| `MODEL_FILE_PATH` | Path to model file in container | `iforest_final.joblib` |
| `INFLUXDB_URL` | InfluxDB server URL | `http://influxdb:8086` |
| `INFLUXDB_ORG` | InfluxDB organization | `iiot-org` |
| `INFLUXDB_BUCKET` | Bucket for anomaly scores | `anomaly-scores` |
| `INFLUXDB_TOKEN` | InfluxDB authentication token | `your-token` |
| `FEATURE_KEYS` | Comma-separated feature names | `feature_1,feature_2,feature_3` |

### Docker Deployment

1. **Build the Docker image:**
   ```bash
   docker build -t anomaly-scorer .
   ```

2. **Run the container:**
   ```bash
   docker run -e EVENT_HUB_NAMESPACE_FQDN="your-namespace.servicebus.windows.net" \
              -e EVENT_HUB_NAME="sensor-features" \
              -e STORAGE_ACCOUNT_NAME="your-storage-account" \
              -e MODEL_CONTAINER_NAME="models" \
              -e MODEL_FILE_PATH="your-model.joblib" \
              -e INFLUXDB_URL="http://your-influxdb:8086" \
              -e INFLUXDB_TOKEN="your-token" \
              -e INFLUXDB_ORG="your-org" \
              -e INFLUXDB_BUCKET="anomaly-scores" \
              anomaly-scorer
   ```

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Azure authentication:**
   ```bash
   # Option 1: Azure CLI
   az login
   
   # Option 2: Service Principal
   export AZURE_CLIENT_ID="your-client-id"
   export AZURE_CLIENT_SECRET="your-client-secret"
   export AZURE_TENANT_ID="your-tenant-id"
   ```

3. **Set environment variables and run:**
   ```bash
   export EVENT_HUB_NAMESPACE_FQDN="your-namespace.servicebus.windows.net"
   export STORAGE_ACCOUNT_NAME="your-storage-account"
   # ... set other required variables
   python anomaly_scorer.py
   ```

## 🤖 Machine Learning Models

### Supported Model Types

The service automatically detects and handles various ML model types:

| Model Type | Scoring Method | Score Interpretation |
|------------|----------------|---------------------|
| **Isolation Forest** | `decision_function()` | Higher values = more normal |
| **One-Class SVM** | `decision_function()` | Higher values = more normal |
| **Local Outlier Factor** | `score_samples()` | Lower values = more anomalous |
| **Classification Models** | `predict_proba()` | Probability of anomaly class |
| **Generic Models** | `predict()` | Direct prediction output |

### Model Storage Formats

The service supports multiple model storage formats:

#### 1. Direct Model Object
```python
# Simple joblib/pickle dump of the model
joblib.dump(isolation_forest_model, 'model.joblib')
```

#### 2. Dictionary with Pipeline
```python
# Model stored in dictionary with 'pipeline' key
model_dict = {
    'pipeline': make_pipeline(scaler, isolation_forest)
}
joblib.dump(model_dict, 'model.joblib')
```

#### 3. Dictionary with Separate Components
```python
# Model with separate scaler and classifier
model_dict = {
    'scaler': StandardScaler(),
    'clf': IsolationForest()
}
joblib.dump(model_dict, 'model.joblib')
```

## 📊 Data Processing

### Input Event Format (from Event Hubs)

```json
{
  "sensor_id": "pump-01",
  "timestamp": 1698765432.0,
  "feature_1": 0.125,
  "feature_2": 0.089,
  "feature_3": 0.156,
  "feature_4": -0.023,
  "feature_5": 0.267
}
```

### Output Score Format (to InfluxDB)

```influxql
anomaly_score,sensor_id=pump-01 score=-0.234 1698765432000000000
```

### Feature Configuration

#### Explicit Feature Keys
```bash
export FEATURE_KEYS="rms_ax,rms_ay,rms_az,peak_freq_ax,peak_freq_ay"
```

#### Default Feature Convention
If `FEATURE_KEYS` is not set, the service looks for `feature_1`, `feature_2`, ..., `feature_32`

## 🔧 Configuration Examples

### High-Performance Setup
```bash
# Use explicit feature keys for faster processing
export FEATURE_KEYS="feature_1,feature_2,feature_3,feature_4,feature_5"
```

### Multi-Model Deployment
Deploy multiple instances with different models:
```bash
# Instance 1: Vibration anomaly detection
export MODEL_FILE_PATH="vibration_iforest.joblib"
export INFLUXDB_BUCKET="vibration-anomalies"

# Instance 2: Temperature anomaly detection  
export MODEL_FILE_PATH="temperature_svm.joblib"
export INFLUXDB_BUCKET="temperature-anomalies"
```

## 📝 Logging

The service provides comprehensive logging with emoji indicators:

- **🚀** **Startup**: Service initialization and configuration
- **🔄** **Loading**: Model loading progress from Azure Blob Storage
- **✅** **Success**: Successful operations (model loaded, scores written)
- **📊** **Scoring**: Real-time scoring results with details
- **⚠️** **Warnings**: Non-critical issues (feature count mismatches)
- **❌** **Errors**: Critical failures requiring attention
- **🛑** **Shutdown**: Graceful service termination

Example log output:
```
🚀 Starting ML Anomaly Scoring Service...
🔧 Configuration check:
   Event Hub: myns.servicebus.windows.net/sensor-features
   Storage: storage/models/iforest_final.joblib
   InfluxDB: http://influxdb:8086/anomaly-scores
🔄 Starting model loading...
✅ Downloaded 1024576 bytes from Blob Storage
✅ Model loaded successfully with joblib
✅ Normalized model type: <class 'sklearn.ensemble._iforest.IsolationForest'>
🧠 Model expects 5 input features
👂 Listening for events on Event Hub: sensor-features...
📊 Scored event: Score=-0.234, sensor=pump-01, features_used=5
✅ Anomaly score written to InfluxDB
```

## 🛠️ Dependencies

### Core ML & Data Processing
- **numpy**: Numerical computing for feature arrays
- **pandas**: Data manipulation and feature handling
- **scikit-learn**: ML model support and utilities
- **joblib**: Optimized model serialization/loading

### Azure Services
- **azure-identity**: Authentication (DefaultAzureCredential)
- **azure-storage-blob**: ML model loading from Blob Storage
- **azure-eventhub**: Real-time feature data consumption

### Time-Series Database
- **influxdb-client**: Anomaly score storage and querying

## 🔍 Monitoring

### Service Health Metrics

Monitor the service through:

1. **Container logs**: Real-time processing status and throughput
2. **InfluxDB metrics**: Score distribution and processing rates
3. **Azure Event Hubs metrics**: Consumer lag and throughput
4. **Azure Blob Storage logs**: Model loading frequency and performance

### Key Performance Indicators

- **Processing Rate**: Events processed per second
- **Score Distribution**: Normal vs. anomalous score ranges  
- **Consumer Lag**: Delay between event creation and scoring
- **Model Performance**: Prediction latency and accuracy

### Alerting Setup

Set up alerts based on:
- High anomaly score values (potential equipment issues)
- Processing delays or failures
- Model loading errors
- InfluxDB write failures

## 🚨 Troubleshooting

### Authentication Issues
```bash
# Verify Azure credentials
az account show

# Check service principal permissions
# Required roles: Storage Blob Data Reader, Azure Event Hubs Data Receiver
```

### Model Loading Issues
```bash
# Verify model file exists and is accessible
az storage blob show --account-name <storage> --container-name <container> --name <model-file>

# Check model format compatibility
python -c "from joblib import load; model = load('your_model.joblib'); print(type(model))"
```

### Feature Mismatch Issues
```bash
# Check incoming event structure
# Ensure FEATURE_KEYS matches the event data schema
export FEATURE_KEYS="actual_feature_names_from_events"
```

### Performance Issues
- Increase Event Hub prefetch count for higher throughput
- Use explicit FEATURE_KEYS to avoid feature detection overhead
- Monitor InfluxDB write performance and batch settings

## 🎯 Use Cases

- **Predictive Maintenance**: Detect equipment anomalies before failures
- **Quality Control**: Identify process deviations in manufacturing
- **Asset Monitoring**: Monitor critical infrastructure health
- **Compliance**: Ensure operating parameters stay within safe ranges
- **Cost Optimization**: Prevent unplanned downtime and maintenance

## 🔄 Integration with Other Services

### With RMS+FFT Service
```bash
# RMS+FFT Service outputs features that this service consumes
EVENT_HUB_NAME="sensor-features"  # Same as RMS+FFT output hub
```

### With Data Replayer  
```bash
# Replayer provides test data for model validation
# Use same feature naming convention across services
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add support for new ML model types or features
4. Add tests for model loading and scoring
5. Submit a pull request

## 📄 License

This project is part of an Industrial IoT solution for machine health monitoring.

---

**Note**: This service requires pre-trained ML models. Use the accompanying Jupyter notebooks or your own training pipeline to create models compatible with this scoring service.
