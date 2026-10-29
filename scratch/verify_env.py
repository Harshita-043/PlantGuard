# Verify environment imports and versions
import sys
import importlib

def safe_import(name):
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", None)
        if version is None and hasattr(module, "__file__"):
            version = module.__file__
        print(f"{name}: {version}")
        return module
    except Exception as e:
        print(f"{name}: FAILED ({e})")
        return None

# Core packages
mods = [
    "torch",
    "torchvision",
    "transformers",
    "onnxruntime",
    "sam2",
    "mobile_sam",
    "fastapi",
    "sqlalchemy",
    "alembic",
    "psycopg2",
    "jwt",
    "jose",
]

for m in mods:
    safe_import(m)

# onnxruntime providers
try:
    import onnxruntime as ort
    print("onnxruntime providers:", ort.get_available_providers())
except Exception as e:
    print("onnxruntime providers: FAILED", e)
