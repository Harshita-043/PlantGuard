# PlantGuard AI — ML Runtime Manual Setup Guide

*Target Host: ASUS Vivobook 15/16 (Intel Core CPU, 16 GB RAM, Windows 11)*

This guide provides exact instructions to establish an isolated runtime for loading and executing the verified local model artifacts (`artifacts/dino_disease`, `artifacts/dino_leaf_filter`, `outputs/segformer_plantseg`).

---

## Prerequisites & Context

1. **Host Environment**: The current backend virtual environment (`backend\.venv`) is running **Python 3.14.0**.
2. **PyTorch Wheel Compatibility**: Official PyTorch, TorchVision, and HuggingFace Transformers wheels on Windows are built for Python 3.10–3.12 (with experimental 3.13 preview). Python 3.14 is currently unsupported by upstream binary wheels.
3. **CPU Execution on Vivobook**: The Vivobook uses Intel Iris Xe integrated graphics. We configure PyTorch for CPU mode with bounded thread usage (2–4 threads) to prevent laptop thermal throttling and preserve system responsiveness.

---

## Step-by-Step Setup: Dedicated Python 3.12 ML Environment

### 1. Computer & Directory
- **Computer**: ASUS Vivobook.
- **Directory**: `c:\Users\Asus\OneDrive\Desktop\PLANTGUARD AI`.

### 2. Verify Python 3.12 Installation
Open PowerShell in the project directory:
```powershell
py -3.12 --version
```
*Expected Output*: `Python 3.12.x` (If not installed, install Python 3.12 via python.org or `winget install Python.Python.3.12`).

### 3. Create Dedicated ML Virtual Environment
```powershell
py -3.12 -m venv .venv-ml
.venv-ml\Scripts\python.exe -m pip install --upgrade pip
```
*Expected Output*: Successfully installed updated pip.

### 4. Install CPU-Optimized PyTorch & Transformers
Install lightweight CPU wheels directly (no CUDA dependencies, saving ~3.5 GB of disk space):
```powershell
.venv-ml\Scripts\pip.exe install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv-ml\Scripts\pip.exe install transformers safetensors pillow numpy pydantic
```
*Expected Output*: Clean installation of PyTorch CPU and Transformers.

### 5. Verify Model Artifact Loading Smoke Test
Run this one-line verification command:
```powershell
.venv-ml\Scripts\python.exe -c "import torch, safetensors, transformers; print('PyTorch CPU ready:', torch.__version__); from app.ml.registry import model_registry; print('Readiness report:', model_registry.get_readiness_report()['components'])"
```
*Expected Output*:
- `PyTorch CPU ready: 2.x.x+cpu`
- `Readiness report: {'leaf_filter': {...}, 'disease_classifier': {...}, ...}`

### 6. Resource and Data-Loss Risk Assessment
- **Risk Level**: **Zero**.
- **Isolation**: The new virtual environment (`.venv-ml`) is isolated from `backend\.venv` and does not alter existing database schemas, migrations, or model weights.
- **Disk Usage**: Approx. 1.2 GB for the CPU environment.
