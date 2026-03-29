"""
API v1 роутер
"""
from fastapi import APIRouter
from app.api.v1 import auth, summary, timeline, metrics, leave, admin, devices, ingest

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(summary.router, prefix="/summary", tags=["summary"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["timeline"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(leave.router, prefix="/leave", tags=["leave"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])

