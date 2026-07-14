"""
Реализация ICommandClassifier через CVC API (async httpx).
"""
import logging
import time
from typing import Optional, Dict, Any

import httpx

from app.domain.services.command_classifier import ICommandClassifier

logger = logging.getLogger(__name__)


class CVCCClassifier(ICommandClassifier):
    """Реализация классификатора команд через CVC API"""

    def __init__(
        self,
        base_url: str,
        timeout: float = 2.0,
        health_cache_ttl: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.health_cache_ttl = health_cache_ttl
        self._available: Optional[bool] = None
        self._available_checked_at: float = 0.0
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        logger.info(
            "CVCCClassifier инициализирован с base_url=%s, timeout=%s, health_cache_ttl=%s",
            self.base_url,
            timeout,
            health_cache_ttl,
        )

    async def aclose(self) -> None:
        await self._http_client.aclose()

    def _health_cache_valid(self) -> bool:
        if self._available is None:
            return False
        return (time.monotonic() - self._available_checked_at) < self.health_cache_ttl

    def _set_availability(self, available: bool) -> None:
        if self._available is not None and self._available != available:
            if available:
                logger.info("CVC сервис снова доступен")
            else:
                logger.warning("CVC сервис недоступен")
        elif self._available is None:
            if available:
                logger.info("CVC сервис доступен, будет использоваться для классификации команд")
            else:
                logger.warning("CVC сервис недоступен - система будет сообщать об ошибках подключения")
        self._available = available
        self._available_checked_at = time.monotonic()

    async def _refresh_availability(self) -> bool:
        try:
            response = await self._http_client.get(f"{self.base_url}/v1/health")
            self._set_availability(response.status_code == 200)
        except Exception:
            self._set_availability(False)
        return bool(self._available)

    async def classify(self, utterance: str) -> Optional[Dict[str, Any]]:
        """Классифицирует команду пользователя"""
        try:
            response = await self._http_client.post(
                f"{self.base_url}/v1/predict",
                json={"text": utterance, "return_confidence": True},
            )
            response.raise_for_status()
            result = response.json()

            command = result.get("command")
            if command:
                self._set_availability(True)
                return {
                    "function": command,
                    "confidence": result.get("confidence"),
                }
            return None
        except Exception as e:
            self._set_availability(False)
            logger.error("Ошибка классификации CVC для '%s': %s", utterance, e)
            return None

    async def is_available(self) -> bool:
        """Проверяет доступность сервиса классификации (с TTL-кэшем)."""
        if self._health_cache_valid():
            return bool(self._available)
        return await self._refresh_availability()
