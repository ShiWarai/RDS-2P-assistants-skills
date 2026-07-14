"""
Общий пул подключений Redis на процесс (singleton).
"""
import logging
from functools import lru_cache

import redis

from app.utils.redis_url import redact_redis_url

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONNECTIONS = 20


@lru_cache
def get_shared_redis_client(redis_url: str, max_connections: int = DEFAULT_MAX_CONNECTIONS) -> redis.Redis:
    """Возвращает один Redis-клиент с пулом соединений на процесс."""
    client = redis.from_url(
        redis_url,
        decode_responses=True,
        max_connections=max_connections,
    )
    client.ping()
    logger.info(
        "Shared Redis client pool initialized (max_connections=%s, url=%s)",
        max_connections,
        redact_redis_url(redis_url),
    )
    return client
