"""
Менеджер активных соединений роботов через gRPC (in-memory в pod gateway).
"""
import queue
import logging
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RobotConnectionManager:
    """Управление активными gRPC соединениями с роботами (потокобезопасный)."""

    def __init__(self):
        self._connections: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()
        logger.info("RobotConnectionManager инициализирован")

    def add_connection(self, robot_id: str, message_queue: queue.Queue) -> None:
        with self._lock:
            self._connections[robot_id] = message_queue
            count = len(self._connections)
        logger.info("Добавлено соединение для робота %s. Всего соединений: %s", robot_id, count)

    def remove_connection(self, robot_id: str) -> None:
        with self._lock:
            if robot_id in self._connections:
                del self._connections[robot_id]
                logger.info("Удалено соединение для робота %s", robot_id)

    def send_message(self, robot_id: str, message) -> bool:
        with self._lock:
            if robot_id not in self._connections:
                logger.warning("Робот %s не подключен", robot_id)
                return False
            message_queue = self._connections[robot_id]
        try:
            message_queue.put(message)
            return True
        except Exception as e:
            logger.error("Ошибка отправки сообщения роботу %s: %s", robot_id, e, exc_info=True)
            return False

    def is_connected(self, robot_id: str) -> bool:
        with self._lock:
            return robot_id in self._connections

    def get_connected_robots(self) -> list[str]:
        with self._lock:
            return list(self._connections.keys())

    def get_connection_count(self) -> int:
        with self._lock:
            return len(self._connections)


_connection_manager: Optional[RobotConnectionManager] = None


def get_connection_manager() -> RobotConnectionManager:
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = RobotConnectionManager()
    return _connection_manager
