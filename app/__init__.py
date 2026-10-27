"""Expose the FastAPI package when commands run from the repository root."""

from pathlib import Path

_BACKEND_APP = Path(__file__).resolve().parent.parent / "backend" / "app"
if not _BACKEND_APP.is_dir():
    raise ImportError("PlantGuard backend package directory is missing")

# Keep this top-level package as a thin namespace pointing at backend/app.
# Do not recursively import "app": this module is already registered under that name.
__path__ = [str(_BACKEND_APP)]
__file__ = str(_BACKEND_APP / "__init__.py")
