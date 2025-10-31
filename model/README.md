# 🧠 Machine Learning Model — Isolation Forest

## Overview
This directory documents the trained **Isolation Forest anomaly detection model** used in the IIoT Machine Health project.

The model file (`iforest_final.joblib`) is **not stored in this repository** to keep the repository lightweight and secure.  
Instead, it is hosted in **Azure Blob Storage** and automatically downloaded by the **Anomaly Scorer** container during runtime.

---

## 📦 Model Details

| Property | Description |
|-----------|--------------|
| **Model Type** | Isolation Forest (`sklearn.ensemble.IsolationForest`) |
| **Framework** | scikit-learn v1.7.2 |
| **Pipeline Components** | StandardScaler → IsolationForest |
| **Input Features** | Statistical & frequency-domain features extracted from vibration signals (e.g., RMS, Peak-to-Peak, Band Energy, FFT components) |
| **Output** | Anomaly score (float). Lower values indicate more anomalous behavior. |
| **Trained On** | Preprocessed vibration dataset derived from industrial machine sensors (IIoT 3.0 pipeline) |

---

## ☁️ Storage & Access

**Blob Storage Location:**

