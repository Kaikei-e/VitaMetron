from fastapi import APIRouter, Request

from app.database import ping

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request):
    db_ok = await ping(request.app.state.db_pool)
    if not db_ok:
        return {"status": "error", "db": "unavailable"}
    return {"status": "ok", "db": "ok"}
