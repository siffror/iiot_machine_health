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
4. **Hugging Face** → Provides public access to training dataset

### 🔹 Deployment Benefits

- **Scalable & Cloud-native** – Automatic scaling via Azure Container Apps  
- **Secure** – Uses Managed Identity to access Azure resources
- **Modular** – Each service runs independently as a container  
- **Cost-efficient** – Pay only for runtime; training data hosted free on Hugging Face
- **Open Source** – Both model and training data publicly available

---

## 🧩 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Cloud Platform** | Microsoft Azure | Hosting & orchestration |
| **Messaging** | Azure Event Hubs | Real-time data ingestion |
| **Compute** | Azure Container Apps | Modular services (Replayer, Scorer) |
| **Data Storage** | GitHub repo + Hugging Face | Training data (~5.5GB) hosted on both platforms |
| **Model Storage** | GitHub repo | ML model artifact (812 KB) |
| **Database** | InfluxDB Cloud | Time-series data storage |
| **Visualization** | Grafana Cloud | Real-time dashboards |
| **Machine Learning** | scikit-learn (Isolation Forest) | Unsupervised anomaly detection |
| **Language** | Python 3.10 | Core analytics & microservices |

---

## 📁 Project Structure

```
iiot_machine_health/
├── .github/
│   └── workflows/           # CI/CD pipelines
├── data/
│   ├── README.md            # Data documentation
│   └── iiot_rms.csv         # Sample data (1.4 MB)
├── docker/
│   ├── Dockerfile_anomaly_scorer
│   ├── Dockerfile_replayer
│   └── Dockerfile_rms_fft
├── model/
│   ├── README.md            # Model documentation
│   └── iforest_final.joblib # Trained Isolation Forest model (812 KB)
├── notebooks/
│   ├── 01_femto_eda.ipynb   # Exploratory analysis
│   └── rms_analysis.ipynb   # Feature engineering
├── scripts/
│   ├── download_data.py     # Download from Hugging Face
│   └── setup.sh             # Environment setup
├── services/
│   ├── anomaly-scorer/      # Scoring service
│   ├── replayer/            # Data replay service
│   └── rms-fft-service/     # Feature extraction
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
├── README.md
└── requirements.txt
```

---

## 🤖 Machine Learning Model

- **Model Type:** Isolation Forest (`sklearn.ensemble.IsolationForest`)  
- **Pipeline:** `StandardScaler → IsolationForest`  
- **Trained On:** FEMTO bearing vibration dataset (RMS, Peak-to-Peak, Band Energy, FFT)  
- **Storage:**
  - 📦 **GitHub Repo:** `model/iforest_final.joblib` (812 KB - included in repo)
  - 📚 **Documentation:** `model/README.md`
- **Parameters:**
  - `n_estimators`: 100
  - `contamination`: 0.1
  - `max_samples`: auto
  - `random_state`: 42
- **Output:** Continuous anomaly score (float), lower values = more anomalous  

### Load Model

```python
import joblib

# Model is included in the repo
model = joblib.load('model/iforest_final.joblib')

# Use for prediction
predictions = model.predict(X_test)
anomaly_scores = model.score_samples(X_test)
```

---

## 📊 Dataset

### 🤗 Training Data Location

Training data (~5.5 GB) is **available from two sources**:

| Source | Size | Access | Best For |
|--------|------|--------|----------|
| **Hugging Face** 🤗 | 5.5 GB | Public, free download | Recommended - faster, permanent |
| **GitHub Repo** | Sample only (1.4 MB) | Included in repo | Quick testing |

**Full Dataset:** [Amgharr/FEMTO-ST_DATASET](https://huggingface.co/datasets/Amgharr/FEMTO-ST_DATASET)

### Dataset Details

- **Total Size:** ~5.5 GB
- **Format:** Parquet (features) + CSV (raw vibration data)
- **Splits:** Training (1GB), Validation (2.3GB), Test (2.3GB)
- **License:** MIT
- **Records:** ~8,331+ measurements
- **Source:** FEMTO Bearing Dataset (NASA PCoE)

### Download Full Dataset

```bash
# Option 1: Using Python script (recommended)
python scripts/download_data.py

# Option 2: Using Hugging Face CLI
pip install huggingface_hub
huggingface-cli download Amgharr/FEMTO-ST_DATASET --repo-type dataset --local-dir ./data

# Option 3: In Python code
from datasets import load_dataset
dataset = load_dataset("Amgharr/FEMTO-ST_DATASET")
```

### Dataset Structure (After Download)
```
data/
├── features_train.parquet   # 455 MB - Training features
├── features_val.parquet     # 934 MB - Validation features
├── features_test.parquet    # 800 MB - Test features
├── training/                # 573 MB - Raw training data
├── validation/              # 1.33 GB - Raw validation data
├── test/                    # 1.49 GB - Raw test data (15,687 files)
├── vibration_sample.csv     # 1 KB - Quick sample
└── iiot_rms.csv            # 1.4 MB - Sample (included in repo)
```

---

## 🧠 Core Microservices

### Azure Container Apps

| App | Description | Model/Data Source |
|-----|-------------|-------------------|
| **iiotpoc-replayer** | Reads Parquet data and streams events to Event Hubs | Uses downloaded HF data |
| **iiotpoc-scorer-final** | Consumes events, loads Isolation Forest model, writes anomaly scores to InfluxDB | Uses `model/iforest_final.joblib` from repo |
| **iiotpoc-rms-fft** | Extracts RMS and FFT features from raw vibration data | Feature engineering service |
| **Grafana Cloud Dashboard** | Displays real-time machine health and anomaly trends | Visualization |

---

## 🛠️ Prerequisites

- ✅ Azure Subscription (for deployment)
- ✅ Azure CLI + Docker installed  
- ✅ InfluxDB Cloud account & token  
- ✅ Grafana Cloud account (for visualization)  
- ✅ Python 3.10+ with pip
- ✅ ~6 GB free disk space (for full dataset download)

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/siffror/iiot_machine_health.git
cd iiot_machine_health
```

### 2. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### 3. Test with Sample Data (Quick)

```bash
# Model and sample data are already in the repo!
jupyter lab notebooks/rms_analysis.ipynb
```

### 4. Download Full Training Data (Optional)

```bash
# Only needed for full model training
python scripts/download_data.py
```

### 5. Local Testing with Docker

```bash
# Build services
docker build -f docker/Dockerfile_replayer -t replayer:latest .
docker build -f docker/Dockerfile_anomaly_scorer -t scorer:latest .

# Run with docker-compose
docker-compose up
```

---

## ☁️ Azure Deployment

### Deploy to Azure Container Apps

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

# Deploy scorer service (model from repo)
az containerapp create \
  --name iiotpoc-scorer-final \
  --resource-group iiot-poc-rg \
  --environment iiot-env-public \
  --image ghcr.io/siffror/iiot_machine_health/anomaly-scorer:latest \
  --cpu 0.5 \
  --memory 1.0Gi \
  --env-vars \
    EVENTHUB_CONNECTION_STRING=secretref:eventhub-conn \
    INFLUXDB_TOKEN=secretref:influx-token
```

---

## 💻 Usage

### Quick Test with Included Model & Sample Data

```python
import joblib
import pandas as pd
from sklearn.preprocessing import StandardScaler

# Load model from repo (no download needed!)
model = joblib.load('model/iforest_final.joblib')

# Load sample data from repo
df = pd.read_csv('data/iiot_rms.csv')

# Select features
features = ['rms', 'peak_to_peak', 'band_energy_low']
X = df[features]

# Predict
predictions = model.predict(X)
anomaly_scores = model.score_samples(X)

# Show results
df['is_anomaly'] = predictions == -1
df['anomaly_score'] = anomaly_scores

print(f"Found {(predictions == -1).sum()} anomalies")
print(df[df['is_anomaly']].head())
```

### Full Workflow with Downloaded Data

```python
from datasets import load_dataset
import joblib

# 1. Load full dataset from Hugging Face
dataset = load_dataset("Amgharr/FEMTO-ST_DATASET")
test_df = dataset['test'].to_pandas()

# 2. Load model from repo
model = joblib.load('model/iforest_final.joblib')

# 3. Select features
features = ['rms', 'peak_to_peak', 'band_energy_low', 
            'band_energy_mid', 'band_energy_high']
X_test = test_df[features]

# 4. Predict anomalies
predictions = model.predict(X_test)
scores = model.score_samples(X_test)

# 5. Analyze results
print(f"Anomaly rate: {(predictions == -1).mean() * 100:.2f}%")
```

---

## 📓 Jupyter Notebooks

The repository includes notebooks for:

- ✨ **01_femto_eda.ipynb** - Exploratory data analysis of FEMTO bearing dataset
- ✨ **rms_analysis.ipynb** - Feature engineering: RMS, FFT, band energy computation, model training

**Note:** Notebooks can run with the included sample data. Download full dataset for complete analysis.

---

## 📈 Visualization

Data is streamed in real-time to **InfluxDB Cloud**, then visualized in **Grafana Cloud**.

### Example Flux Query

```flux
from(bucket: "iiot_rms")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "anomaly_score")
  |> filter(fn: (r) => r._field == "score")
  |> aggregateWindow(every: 10s, fn: mean, createEmpty: false)
```

---

## 📦 Model & Data Storage Summary

| Asset | Size | Location | Access |
|-------|------|----------|--------|
| **ML Model** | 812 KB | `model/iforest_final.joblib` | ✅ Included in repo |
| **Sample Data** | 1.4 MB | `data/iiot_rms.csv` | ✅ Included in repo |
| **Full Dataset** | 5.5 GB | Hugging Face | 📥 Download required |

**You can start immediately** with the model and sample data included in the repo!  
**Download full dataset** only if you need to retrain or do extensive analysis.

---

## 🤝 Contributing

Contributions are welcome! This is a free and open project.

1. 🍴 Fork the repository
2. 🌿 Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. 💾 Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. 📤 Push to the branch (`git push origin feature/AmazingFeature`)
5. 🔀 Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📝 License

**This project is free and available for anyone to use.**

Licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Both the **code and trained model** are included under MIT License.  
The **training dataset** is also MIT licensed and available on Hugging Face.

---

## 📧 Contact

**Author:** Zakaria  
**GitHub:** [@siffror](https://github.com/siffror)  
**Project Link:** [https://github.com/siffror/iiot_machine_health](https://github.com/siffror/iiot_machine_health)  
**Dataset:** [https://huggingface.co/datasets/Amgharr/FEMTO-ST_DATASET](https://huggingface.co/datasets/Amgharr/FEMTO-ST_DATASET)

---

## 🙏 Acknowledgments

- FEMTO-ST Institute for the original bearing dataset
- NASA Prognostics Center of Excellence
- Microsoft Azure IoT and Container Apps documentation
- InfluxData & Grafana Cloud teams
- Hugging Face for free dataset hosting
- Industrial IoT community and open-source contributors
- scikit-learn development team

---

<div align="center">

### 💡 *"Industrial data without insight is just noise — Machine Health turns it into action."*

**⭐ If you find this project useful, please consider giving it a star!**

**🤗 [View Dataset on Hugging Face](https://huggingface.co/datasets/Amgharr/FEMTO-ST_DATASET)**

</div>
