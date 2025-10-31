# ⚙️ IIoT Machine Health Monitoring System

A **real-time Industrial IoT (IIoT) anomaly-detection and machine-health monitoring system** built with Azure Container Apps, Event Hubs, InfluxDB Cloud, and Grafana Cloud.

The system continuously streams vibration data from industrial sensors, processes it with an ML model (Isolation Forest), and visualizes anomaly scores for predictive maintenance.

---

## 📋 Overview

This project demonstrates a **cloud-native, end-to-end IIoT pipeline** for monitoring machine health.  
It leverages Azure Container Apps for scalable compute, Event Hubs for streaming, and InfluxDB + Grafana Cloud for time-series analytics and dashboards.

---

## 🏗️ Architecture

### 🔹 Data Flow

1. **Replayer** → Streams historical or simulated sensor data from Parquet to **Azure Event Hubs**  
2. **Scorer** → Consumes events, applies an **Isolation Forest model**, writes anomaly scores to **InfluxDB Cloud**  
3. **Grafana Cloud** → Visualizes live data and anomaly trends  
4. **Azure Blob Storage** → Hosts the trained ML model artifact

### 🔹 Deployment Benefits

- **Scalable & Cloud-native** – Automatic scaling via Azure Container Apps  
- **Secure** – Uses Managed Identity to access Azure Blob Storage  
- **Modular** – Each service runs independently as a container  
- **Cost-efficient** – Pay only for runtime and storage

---

## 🧩 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Cloud Platform** | Microsoft Azure | Hosting & orchestration |
| **Messaging** | Azure Event Hubs | Real-time data ingestion |
| **Compute** | Azure Container Apps | Modular services (Replayer, Scorer) |
| **Storage** | Azure Blob Storage | Model artifact storage |
| **Database** | InfluxDB Cloud | Time-series data storage |
| **Visualization** | Grafana Cloud | Real-time dashboards |
| **Machine Learning** | scikit-learn (Isolation Forest) | Unsupervised anomaly detection |
| **Language** | Python 3.10 | Core analytics & microservices |

---

## 📁 Project Structure

```
iiot_machine_health/
├── replayer/              # Streams Parquet → Event Hubs
├── scorer/                # Loads model → writes anomaly scores → InfluxDB
├── notebooks/             # Data analysis & model training (e.g., rms_analysis.ipynb)
├── models/                # Documentation (model stored in Azure Blob)
├── infra/                 # Optional: Azure Container Apps YAML definitions
├── data/                  # Example or local datasets
└── README.md
```

---

## 🤖 Machine Learning Model

- **Model Type:** Isolation Forest (`sklearn.ensemble.IsolationForest`)  
- **Pipeline:** `StandardScaler → IsolationForest`  
- **Trained On:** Vibration feature dataset (RMS, Peak-to-Peak, Band Energy, FFT)  
- **Stored In:** Azure Blob Storage  
  - 🔗 [iforest_final.joblib](https://iiotpocstorage.blob.core.windows.net/models/iforest_final.joblib)
- **Loaded By:** `iiotpoc-scorer-final` container via Managed Identity authentication  
- **Output:** Continuous anomaly score (float), lower values = more anomalous  

---

## 🧠 Core Microservices

### Azure Container Apps

| App | Description |
|-----|-------------|
| **iiotpoc-replayer** | Reads Parquet data and streams events to Event Hubs |
| **iiotpoc-scorer-final** | Consumes events, loads the Isolation Forest model, and writes anomaly scores to InfluxDB |
| **Grafana Cloud Dashboard** | Displays real-time machine health and anomaly trends |

---

## 🛠️ Prerequisites

- ✅ Azure Subscription  
- ✅ Azure CLI + Docker installed  
- ✅ InfluxDB Cloud account & token  
- ✅ Grafana Cloud account (for visualization)  
- ✅ Python 3.10 + requirements installed locally

---

## 🚀 Deployment

### Quick Start with Azure CLI

```bash
# Login to Azure
az login

# Create resource group
az group create \
  --name iiot-poc-rg \
  --location northeurope

# Create Container Apps environment
az containerapp env create \
  --name iiot-env-public \
  --resource-group iiot-poc-rg \
  --location northeurope

# Deploy scorer container app
az containerapp create \
  --name iiotpoc-scorer-final \
  --resource-group iiot-poc-rg \
  --environment iiot-env-public \
  --image iiotpocacr.azurecr.io/scorer:v4.5 \
  --cpu 0.5 \
  --memory 1.0Gi
```

---

## 💻 Usage

### Workflow

1. **Replayer:** Streams vibration data (Parquet) to Event Hubs
2. **Scorer:** Receives events → computes anomaly scores → saves to InfluxDB
3. **Grafana:** Displays live metrics and anomaly trend charts
4. **Notebooks:** Used for feature engineering & model training
5. **(Optional)** Re-train model → upload new `.joblib` to Blob Storage

---

## 📓 Jupyter Notebooks

The repository includes notebooks for:

- ✨ Exploratory data analysis (EDA)
- ✨ Feature engineering and RMS/FFT computation
- ✨ Isolation Forest model training & validation
- ✨ InfluxDB/Grafana integration examples

---

## 🧰 Local Development

```bash
# Clone repository
git clone https://github.com/siffror/iiot_machine_health.git
cd iiot_machine_health

# Install dependencies
pip install -r requirements.txt

# Run Jupyter notebooks
jupyter lab
```

---

## 📈 Visualization

Data is streamed in real-time to **InfluxDB Cloud**, then visualized in **Grafana Cloud** using Flux queries.

### Example Flux Query

```flux
from(bucket: "iiot_rms")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "anomaly_score")
  |> filter(fn: (r) => r._field == "score")
  |> aggregateWindow(every: 10s, fn: mean, createEmpty: false)
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License – see the LICENSE file for details.

---

## 📧 Contact

**Author:** Zakaria  
**GitHub:** [@siffror](https://github.com/siffror)  
**Project Link:** [https://github.com/siffror/iiot_machine_health](https://github.com/siffror/iiot_machine_health)

---

## 🙏 Acknowledgments

- Microsoft Azure IoT and Container Apps documentation
- InfluxData & Grafana Cloud teams
- Industrial IoT community and open-source contributors
- scikit-learn development team

---

<div align="center">

### 💡 *"Industrial data without insight is just noise — Machine Health turns it into action."*

</div>
