"""
Общий lifespan FastAPI для навыков.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.application.dependencies import shutdown_app_dependencies


@asynccontextmanager
async def skill_app_lifespan(app: FastAPI):
    yield
    await shutdown_app_dependencies()
