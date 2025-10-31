# RMS + FFT Service

A real-time signal processing microservice for Industrial IoT (IIoT) applications that processes vibration sensor data from Azure Event Hubs and extracts meaningful features for machine health monitoring.

## 📋 Overview

This service reads vibration data from Azure Event Hubs, performs signal processing calculations (RMS and FFT analysis), and stores the computed features in InfluxDB for time-series analysis and monitoring.

### Key Features

- **Real-time Processing**: Consumes vibration data streams from Azure Event Hubs
- **Dual Processing Modes**:
  - **Mode A**: Processes pre-computed features (feature_1, feature_2, etc.)
  - **Mode B**: Computes RMS and FFT features from raw accelerometer signals (ax, ay, az)
- **Signal Processing**: 
  - Root Mean Square (RMS) calculation for vibration intensity
  - Fast Fourier Transform (FFT) analysis for frequency domain features
  - Peak frequency detection
  - Band energy calculation (configurable frequency range)
- **Time-series Storage**: Writes processed features to InfluxDB
- **Flexible Data Format**: Supports various JSON structures for accelerometer data
- **Containerized**: Ready for deployment with Docker

## 🏗️ Architecture

```
Azure Event Hubs → RMS+FFT Service → InfluxDB
     (Raw Data)      (Processing)     (Features)
```

## 🚀 Quick Start

### Prerequisites

- Docker (for containerized deployment)
- Azure Event Hubs instance
- InfluxDB instance
- Python 3.11+ (for local development)

### Environment Variables

Configure the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `EVENT_HUBS_CONN` | Azure Event Hubs connection string | *Required* |
| `EVENT_HUBS_TOPIC` | Event Hub name/topic | `sensors/vibration` |
| `INFLUX_URL` | InfluxDB server URL | *Required* |
| `INFLUX_TOKEN` | InfluxDB authentication token | *Required* |
| `INFLUX_ORG` | InfluxDB organization | *Required* |
| `INFLUX_BUCKET` | InfluxDB bucket name | `machine_health` |
| `MEASUREMENT_NAME` | InfluxDB measurement name | `signal_features` |
| `BAND_LOW_HZ` | Lower frequency bound for band energy | `0` |
| `BAND_HIGH_HZ` | Upper frequency bound for band energy | `200` |

### Docker Deployment

1. **Build the Docker image:**
   ```bash
   docker build -t rms-fft-service .
   ```

2. **Run the container:**
   ```bash
   docker run -e EVENT_HUBS_CONN="your_connection_string" \
              -e INFLUX_URL="http://your_influx_host:8086" \
              -e INFLUX_TOKEN="your_token" \
              -e INFLUX_ORG="your_org" \
              rms-fft-service
   ```

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables and run:**
   ```bash
   export EVENT_HUBS_CONN="your_connection_string"
   export INFLUX_URL="http://localhost:8086"
   # ... set other required variables
   python app.py
   ```

## 📊 Data Processing

### Input Data Formats

#### Mode A: Pre-computed Features
```json
{
  "device_id": "sensor_001",
  "feature_1": 0.125,
  "feature_2": 0.089,
  "feature_3": 0.156
}
```

#### Mode B: Raw Accelerometer Data
```json
{
  "device_id": "sensor_001",
  "fs": 6400,
  "ax": [0.1, 0.2, -0.1, 0.05, ...],
  "ay": [0.05, -0.15, 0.2, 0.1, ...],
  "az": [9.8, 9.75, 9.82, 9.78, ...]
}
```

Alternative nested format:
```json
{
  "device_id": "sensor_001",
  "fs": 6400,
  "axes": {
    "x": [0.1, 0.2, -0.1, ...],
    "y": [0.05, -0.15, 0.2, ...],
    "z": [9.8, 9.75, 9.82, ...]
  }
}
```

### Output Features

For raw signal processing (Mode B), the service computes:

| Feature | Description |
|---------|-------------|
| `rms_ax`, `rms_ay`, `rms_az` | Root Mean Square values for each axis |
| `peak_freq_ax`, `peak_freq_ay`, `peak_freq_az` | Dominant frequency for each axis |
| `bandE0_200_ax`, `bandE0_200_ay`, `bandE0_200_az` | Energy in 0-200 Hz band for each axis |

## 🔧 Configuration

### Frequency Band Analysis

Adjust the frequency range for band energy calculation:

```bash
# Focus on low-frequency vibrations (0-50 Hz)
export BAND_LOW_HZ=0
export BAND_HIGH_HZ=50

# Focus on high-frequency vibrations (100-500 Hz)
export BAND_LOW_HZ=100
export BAND_HIGH_HZ=500
```

### Sampling Rate

The service expects a `fs` field in the JSON data specifying the sampling frequency in Hz. Default is 6400 Hz if not provided.

## 📝 Logging

The service provides detailed logging:

- ✅ **Success**: Feature computation and storage
- ⚠️ **Warnings**: Skipped events due to invalid data
- ❌ **Errors**: Processing failures
- ℹ️ **Info**: Validation messages

## 🛠️ Dependencies

- **azure-eventhub**: Azure Event Hubs client
- **influxdb-client**: InfluxDB time-series database client
- **numpy**: Numerical computing for signal processing
- **pandas**: Data manipulation (if needed for future enhancements)
- **scipy**: Scientific computing library

## 🔍 Monitoring

Monitor the service through:

1. **Container logs**: Real-time processing status
2. **InfluxDB**: Query stored features and processing rates
3. **Azure Event Hubs metrics**: Message consumption rates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is part of an Industrial IoT solution for machine health monitoring.

---

**Note**: This service is designed to run continuously and process real-time data streams. For batch processing or historical data analysis, consider the data replayer service in the parent project.

