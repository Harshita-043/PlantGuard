# PowerShell script to set up a clean Python 3.12 environment for PlantGuard
# -------------------------------------------------------------
# 1. Ensure Python 3.12 is installed and is on PATH.
#    You can download it from https://www.python.org/downloads/windows/
#    Verify with: python --version   (should show 3.12.x)
#
# 2. Delete any existing virtual environment to avoid conflicts.
Remove-Item -Recurse -Force backend\.venv

# 3. Create a new virtual environment using Python 3.12.
python -m venv backend\.venv

# 4. Activate the virtual environment.
#    In PowerShell:
. "backend\.venv\Scripts\Activate.ps1"

# 5. Upgrade pip and install required packages.
python -m pip install --upgrade pip

# 6. Install the exact torch version required by the model manifest (CPU build).
#    Note: torch 2.6.0 is only available for specific Python versions; for CPU use the following wheel URL.
#    You may need to adjust the URL if a newer wheel is published.
pip install "torch==2.6.0+cpu" -f https://download.pytorch.org/whl/torch_stable.html

# 7. Install remaining dependencies from the project's lockfile.
#    This will install everything else while respecting the torch version we just pinned.
pip install -r backend\requirements.txt

# 8. (Optional) Install SAM‑2 if you later decide to enable it.
# pip install "sam2==1.1.0"

# 9. Verify runtime capabilities – should now report python_supported=True and all models ready.
python -c "from backend.app.ml.variants import collect_runtime_capabilities; print(collect_runtime_capabilities())"

# 10. Run the test suite to ensure everything passes.
python -m pytest backend/tests

# -------------------------------------------------------------
# After the script finishes without errors, you can proceed with the next audit steps.

