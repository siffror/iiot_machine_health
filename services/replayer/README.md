# Data Replayer Service

A data replay microservice for Industrial IoT (IIoT) applications that loads feature data from Azure Blob Storage (Parquet files) and streams it to Azure Event Hubs to simulate live sensor data streams.

## 📋 Overview

This service enables you to replay historical sensor data stored in Parquet format, making it appear as live streaming data. It's perfect for testing, development, and demonstration of real-time analytics pipelines without requiring physical sensors.

### Key Features

- **Parquet Data Source**: Loads feature data from Azure Blob Storage
- **Event Hub Publishing**: Streams data to Azure Event Hubs in real-time
- **Flexible Feature Selection**: 
  - Manual feature column specification
  - Automatic numeric column detection
  - Configurable feature count limits
- **Sensor ID Management**: Round-robin across multiple sensor IDs or read from data
- **Timestamp Handling**: Supports various timestamp formats (seconds, ms, μs, ns)
- **Batch Processing**: Configurable batch sizes for optimal throughput
- **Continuous Loop**: Option to replay data continuously for long-running tests
- **Azure Authentication**: Uses DefaultAzureCredential for secure access

## 🏗️ Architecture

```
Azure Blob Storage → Data Replayer → Azure Event Hubs → Downstream Services
   (Parquet Files)    (Streaming)     (Live Events)    (Analytics/ML)
```

## 🚀 Quick Start

### Prerequisites

- Docker (for containerized deployment)
- Azure Blob Storage account with Parquet data
- Azure Event Hubs instance
- Azure authentication configured (Service Principal, Managed Identity, or Azure CLI)
- Python 3.10+ (for local development)

### Environment Variables

Configure the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `EVENT_HUB_NAMESPACE_FQDN` | Event Hubs namespace FQDN | *Required* |
| `EVENT_HUB_NAME` | Event Hub name to publish to | `sensor-data-stream` |
| `STORAGE_ACCOUNT_NAME` | Azure Storage account name | `iiotpocstorage` |
| `SENSOR_CONTAINER_NAME` | Blob container name | `sensor-data` |
| `SENSOR_FILE_PATH` | Path to Parquet file in container | `features_train.parquet` |
| `FEATURE_KEYS` | Comma-separated feature column names | *Auto-detect* |
| `FEATURE_COUNT` | Number of features (if auto-detecting) | `0` (all numeric) |
| `BATCH_SIZE` | Events per batch to Event Hubs | `100` |
| `DELAY_SEC` | Delay between batches (seconds) | `0.5` |
| `LOOP` | Continuously replay data | `true` |
| `SENSOR_IDS` | Comma-separated sensor IDs | `sim-1` |
| `SENSOR_ID_COLUMN` | Column name for sensor ID | *Use round-robin* |
| `TIMESTAMP_COLUMN` | Column name for timestamp | *Use current time* |
| `OUTPUT_FEATURE_PREFIX` | Prefix for feature keys | `feature_` |

### Docker Deployment

1. **Build the Docker image:**
   ```bash
   docker build -t data-replayer .
   ```

2. **Run the container:**
   ```bash
   docker run -e EVENT_HUB_NAMESPACE_FQDN="your-namespace.servicebus.windows.net" \
              -e EVENT_HUB_NAME="your-event-hub" \
              -e STORAGE_ACCOUNT_NAME="your-storage-account" \
              data-replayer
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
   # ... set other variables as needed
   python replayer_eventhub_from_parquet.py
   ```

## 📊 Data Processing

### Input Data Format (Parquet)

The service expects Parquet files with numeric feature columns. Example structure:

| timestamp | sensor_01_temp | sensor_01_pressure | sensor_02_vibration | ... |
|-----------|----------------|--------------------|--------------------|-----|
| 1698765432 | 23.5 | 101.3 | 0.02 | ... |
| 1698765433 | 23.7 | 101.1 | 0.03 | ... |

### Output Event Format (JSON to Event Hubs)

```json
{
  "sensor_id": "sim-1",
  "timestamp": 1698765432.0,
  "feature_1": 23.5,
  "feature_2": 101.3,
  "feature_3": 0.02
}
```

### Feature Selection Modes

#### 1. Manual Feature Selection
```bash
export FEATURE_KEYS="temperature,pressure,vibration_x,vibration_y"
```

#### 2. Automatic Selection (First N Features)
```bash
export FEATURE_COUNT=10  # Use first 10 numeric columns
```

#### 3. Automatic Selection (All Features)
```bash
# Leave FEATURE_KEYS empty and FEATURE_COUNT=0
# Uses all numeric columns automatically
```

## 🔧 Configuration Examples

### High-Throughput Streaming
```bash
export BATCH_SIZE=1000
export DELAY_SEC=0.1
export LOOP=true
```

### Slow Simulation for Testing
```bash
export BATCH_SIZE=10
export DELAY_SEC=2.0
export LOOP=false
```

### Multiple Sensor Simulation
```bash
export SENSOR_IDS="pump-01,pump-02,motor-01,motor-02"
```

### Using Existing Sensor IDs from Data
```bash
export SENSOR_ID_COLUMN="device_id"
```

### Custom Timestamp Handling  
```bash
export TIMESTAMP_COLUMN="event_time"
# Supports: seconds, milliseconds, microseconds, nanoseconds
```

## 📝 Logging

The service provides detailed logging:

- **I!** **Info**: General status and progress messages
- **W!** **Warning**: Non-critical issues (empty data, etc.)
- **Error**: Critical failures that stop processing

Example log output:
```
I! Reading Parquet from https://storage.blob.core.windows.net/sensor-data/features_train.parquet
I! Parquet loaded: shape=(10000, 15), columns=['timestamp', 'temp', 'pressure', ...]
I! Features to send (12): ['temp', 'pressure', 'vibration_x', ...]
I! Output keys in event: feature_1..feature_12
I! Sensors: ['sim-1']; LOOP=True, BATCH_SIZE=100, DELAY_SEC=0.5
I! Replay starting: total_rows=10000, batch_size=100, batches=100
I! Sent batch 1/100 (events=100)
```

## 🛠️ Dependencies

- **pandas**: Data manipulation and Parquet reading
- **azure-eventhub**: Azure Event Hubs client for publishing events
- **azure-identity**: Azure authentication (DefaultAzureCredential)
- **azure-storage-blob**: Azure Blob Storage client for data access
- **pyarrow**: Parquet file format support for pandas

## 🔍 Monitoring

Monitor the replayer through:

1. **Container logs**: Real-time streaming status and batch progress
2. **Azure Event Hubs metrics**: Message publishing rates and throughput
3. **Azure Blob Storage logs**: Data access patterns and performance

### Key Metrics to Track

- **Events per second**: `(BATCH_SIZE / DELAY_SEC)`
- **Total replay time**: `(total_rows / BATCH_SIZE) * DELAY_SEC`
- **Memory usage**: Depends on batch size and feature count

## 🚨 Troubleshooting

### Authentication Issues
- Verify DefaultAzureCredential can access both Storage and Event Hubs
- Check RBAC roles: `Storage Blob Data Reader`, `Azure Event Hubs Data Sender`

### Performance Issues
- Increase `BATCH_SIZE` for higher throughput
- Decrease `DELAY_SEC` for faster streaming
- Monitor Event Hubs throttling limits

### Data Issues
- Verify Parquet file structure matches expected schema
- Check feature column names and data types
- Ensure numeric columns contain valid values

## 🎯 Use Cases

- **Pipeline Testing**: Test downstream analytics with realistic data volumes
- **Development**: Develop against consistent, repeatable data streams  
- **Demonstrations**: Show real-time capabilities without physical sensors
- **Load Testing**: Stress-test Event Hubs and downstream services
- **Model Validation**: Replay historical data for ML model evaluation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is part of an Industrial IoT solution for machine health monitoring.

---

**Note**: This service is designed to complement the RMS+FFT Service by providing test data streams. For production data ingestion, use actual sensor hardware or IoT device simulators.
