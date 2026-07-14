"""
Настройки приложения
"""
import os
from typing import Optional


class Settings:
    """Настройки приложения"""
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # CVC Service
    CVC_SERVICE_URL: str = os.getenv("CVC_SERVICE_URL", "http://localhost:20001")
    CVC_TIMEOUT: float = float(os.getenv("CVC_TIMEOUT", "2.0"))
    CVC_HEALTH_CACHE_TTL: float = float(os.getenv("CVC_HEALTH_CACHE_TTL", "30.0"))
    
    # Redis pool
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
    
    # Uvicorn
    UVICORN_WORKERS: int = int(os.getenv("UVICORN_WORKERS", "2"))
    
    # Robot gateway (in-cluster gRPC)
    ROBOT_GATEWAY_URL: str = os.getenv("ROBOT_GATEWAY_URL", "robot-gateway:50051")
    
    # Binding
    CODE_EXPIRY_SECONDS: int = 300  # 5 минут
    MAX_BINDING_ATTEMPTS: int = 3

    # Command feedback («исправить команду»)
    LAST_COMMAND_TTL_SECONDS: int = int(os.getenv("LAST_COMMAND_TTL_SECONDS", "300"))


# Глобальный экземпляр настроек
settings = Settings()
