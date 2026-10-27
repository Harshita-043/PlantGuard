# Local CPU ML environment

## Phase 6 update — environment setup verified (2026-10-27)

The earlier Phase 3 status below records that setup was blocked at that time. Since then, `C:\PlantGuardEnvs\plantguard-vision-cpu` was created with Python 3.12.2. It now has CPU Torch 2.6.0+cpu, torchvision 0.21.0+cpu, Transformers 4.57.6, safetensors 0.8.0, NumPy 2.3.4, Pillow 12.3.0, and the dependencies from `backend/requirements.txt`. `pip check` reported no broken requirements; DINO architecture builders and the SegFormer class imported successfully. CUDA is unavailable, as expected on the Vivobook.

PowerShell activation was blocked by execution policy. No policy was changed; use `C:\PlantGuardEnvs\plantguard-vision-cpu\Scripts\python.exe` directly. This verifies the environment and imports only. No checkpoint bytes were read/hashed, no model was loaded, and no inference ran. Checkpoint paths still require hydration/integrity confirmation. WSL status also remains unverified after the user's reported feature enable/reboot; SAM2 setup and inference are not verified.

**Phase 3 status (2026-10-27): BLOCKED before installation.** Python 3.12.2 is installed, but no ML runtime packages are installed in that interpreter. The active Python 3.14.0 environment also has no PyTorch/Transformers/SAM2. The C: free-space query is denied, the workspace is under OneDrive, and all four checkpoint entries are marked Windows `ReparsePoint`. No package was installed and no checkpoint was read. First make a non-OneDrive working copy with enough free space and verified local checkpoint files.

## Supported versions and isolation

`backend/requirements-ml.txt` pins PyTorch 2.6.0, torchvision 0.21.0, Transformers 4.57.6, and SAM2 source v1.1.0. The repository runtime capability check expects Python 3.12. The official PyTorch previous-version page lists the 2.6.0/0.21.0 CPU wheel command for Windows. SAM2's installation guide recommends WSL with Ubuntu on Windows, so keep SAM in a separate WSL environment if its Windows source build fails. The DINOv2 and SegFormer smoke environment does not need SAM2.

References: [PyTorch 2.6.0 installation commands](https://docs.pytorch.org/get-started/previous-versions/), [SAM2 installation guide](https://github.com/facebookresearch/sam2/blob/main/INSTALL.md).

## Prepare a local workspace first

Do not install into `backend/.venv` or the Python 3.14 API environment. This checkout is inside OneDrive. Use a local, non-synced folder (or a local SSD) for real checkpoint bytes and the CPU smoke copy; ensure adequate free space before proceeding. Keep the existing OneDrive checkout untouched.

The Vivobook currently reports Python 3.12.2 from `py -0p`. Check free space in Windows Explorer on the destination drive before copying. The largest listed checkpoint is about 347 MB and all four together total about 774 MB, before Python wheels, environments, temporary copies, and model RAM. Leave several GB free; the required amount depends on pip cache and the model's runtime RAM. Do not start if free space or RAM headroom is unclear.

Copy the current code and only the required files into the new local workspace. Do not copy datasets or training caches. The source workspace already has the expected artifact paths; the model checkpoint source files must be independently confirmed as real local files before copying. Keep a second, untouched source copy on the RTX PC.

## Install DINOv2 and SegFormer CPU dependencies

From PowerShell in the new local workspace's `backend` folder, after confirming the files and disk budget:

```powershell
py -3.12 -m venv .venv-ml-cpu
.\.venv-ml-cpu\Scripts\python.exe -m pip install --upgrade pip
.\.venv-ml-cpu\Scripts\python.exe -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv-ml-cpu\Scripts\python.exe -m pip install numpy==2.3.4 pillow==12.3.0 transformers==4.57.6 "safetensors>=0.5,<1" "psutil>=5.9,<8" pydantic==2.12.5 pydantic-settings==2.11.0 python-dotenv==1.0.0
.\.venv-ml-cpu\Scripts\python.exe -m pip freeze | Set-Content -LiteralPath .\.venv-ml-cpu\packages.txt
```

This intentionally does not install `-r requirements-ml.txt`, because that file also installs SAM2 from source and can trigger a platform-specific extension build. The direct CPU torch and torchvision versions match the repository pins; do not upgrade Transformers independently of the pin. Record the output of `pip freeze` with the smoke report.

Verify runtime imports without touching checkpoints:

```powershell
.\.venv-ml-cpu\Scripts\python.exe -c "import importlib.metadata as m, torch, torchvision, transformers; print('torch',torch.__version__,'cuda_available',torch.cuda.is_available()); print('torchvision',torchvision.__version__,'transformers',transformers.__version__,'safetensors',m.version('safetensors'))"
```

Expected: torch 2.6.0 CPU build, torchvision 0.21.0, Transformers 4.57.6, safetensors version below 1, and `cuda_available False`. This verifies imports only, not model inference.

## SAM2 isolation

Do not install SAM2 in the DINO/SegFormer environment initially. On Windows, first prepare WSL2 Ubuntu and a separate Python 3.12 venv after disk/RAM checks. Install the same CPU PyTorch/torchvision pair there, then install the pinned repository dependency from the official SAM2 v1.1.0 source with the CUDA extension disabled for CPU:

```bash
SAM2_BUILD_CUDA=0 python -m pip install -e 'git+https://github.com/facebookresearch/sam2.git@v1.1.0#egg=SAM-2'
```

The exact editable-install URL syntax may need adjustment to the SAM2 tag's setup instructions; stop on build errors rather than switching versions silently. Verify `configs/sam2.1/sam2.1_hiera_b+.yaml` exists under the installed package before any model load. SAM CPU inference is not approved by this guide: require a separate written RAM/time budget and a killable process before attempting it. Prefer the documented RTX 5060 CUDA smoke for SAM.

## Reproducible environment capture

From the environment that actually runs a stage:

```powershell
.\.venv-ml-cpu\Scripts\python.exe --version
.\.venv-ml-cpu\Scripts\python.exe -m pip freeze
Get-ComputerInfo | Select-Object WindowsProductName,WindowsVersion,OsArchitecture
```

Append observed versions to `docs/CPU_MODEL_SMOKE_TESTS.md`; do not record secrets or user-specific environment values. Package install success does not make any variant validated or production-ready.
