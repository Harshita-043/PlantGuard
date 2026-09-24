"""
Scan-related API endpoints
"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter()

@router.post("/scan")
async def create_scan():
    raise _unavailable()


@router.get("/scans")
async def get_scans(skip: int = 0, limit: int = 10):
    raise _unavailable()


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str):
    raise _unavailable()


@router.get("/scans/{scan_id}/report")
async def get_scan_report(scan_id: str):
    raise _unavailable()


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Scan services are unavailable until persistence and real ML inference are integrated",
    )
