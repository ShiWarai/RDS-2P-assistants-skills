"""
Менеджер активных соединений роботов через gRPC
"""
import queue
import logging
import json
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Определяем корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ROBOTS_CONFIG_FILE = PROJECT_ROOT / "config" / "robots.json"


class RobotConnectionManager:
    """Управление активными gRPC соединениями с роботами"""
    
    def __init__(self):
        """Инициализация менеджера соединений"""
        self._connections: Dict[str, queue.Queue] = {}
        self._robots_config_cache: Optional[Dict[str, Dict[str, Any]]] = None
        logger.info("RobotConnectionManager инициализирован")
    
    def get_robot_name(self, robot_id: str) -> str:
        """
        Получает имя робота по ID (опционально из конфига)
        """
        # Загружаем конфиг только если он существует и еще не загружен
        if self._robots_config_cache is None:
            if ROBOTS_CONFIG_FILE.exists():
                try:
                    with open(ROBOTS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                        self._robots_config_cache = json.load(f)
                    logger.debug(f"Loaded robot names from config: {len(self._robots_config_cache)} robots")
                except Exception as e:
                    logger.debug(f"Could not load robots config: {e}")
                    self._robots_config_cache = {}
            else:
                self._robots_config_cache = {}
        
        if self._robots_config_cache and robot_id in self._robots_config_cache:
            return self._robots_config_cache[robot_id].get("name", f"Робот {robot_id}")
        
        return f"Робот {robot_id}"

    def get_available_robots_list(self) -> str:
        """
        Возвращает строку со списком доступных роботов
        """
        connected_robots = self.get_connected_robots()
        
        if not connected_robots:
            return "Нет подключенных роботов"
        
        robot_list = []
        for robot_id in connected_robots:
            name = self.get_robot_name(robot_id)
            robot_list.append(f"{robot_id} - {name}")
        
        return ", ".join(robot_list)

    def add_connection(self, robot_id: str, message_queue: queue.Queue) -> None:
        """
        Добавляет активное соединение робота
        
        Args:
            robot_id: ID робота
            message_queue: Очередь сообщений для отправки роботу
        """
        self._connections[robot_id] = message_queue
        logger.info(f"Добавлено соединение для робота {robot_id}. Всего соединений: {len(self._connections)}")
    
    def remove_connection(self, robot_id: str) -> None:
        """
        Удаляет соединение робота
        
        Args:
            robot_id: ID робота
        """
        if robot_id in self._connections:
            del self._connections[robot_id]
            logger.info(f"Удалено соединение для робота {robot_id}. Всего соединений: {len(self._connections)}")
        else:
            logger.warning(f"Попытка удалить несуществующее соединение для робота {robot_id}")
    
    def send_message(self, robot_id: str, message) -> bool:
        """
        Отправляет сообщение роботу через активное соединение
        
        Args:
            robot_id: ID робота
            message: Сообщение для отправки (StreamMessage)
            
        Returns:
            bool: True если сообщение успешно добавлено в очередь
        """
        if robot_id not in self._connections:
            logger.warning(f"Робот {robot_id} не подключен")
            return False
        
        try:
            message_queue = self._connections[robot_id]
            message_queue.put(message)
            logger.debug(f"Сообщение отправлено роботу {robot_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения роботу {robot_id}: {e}", exc_info=True)
            return False
    
    def is_connected(self, robot_id: str) -> bool:
        """
        Проверяет, подключен ли робот
        
        Args:
            robot_id: ID робота
            
        Returns:
            bool: True если робот подключен
        """
        return robot_id in self._connections
    
    def get_connected_robots(self) -> list[str]:
        """
        Возвращает список ID подключенных роботов
        
        Returns:
            list[str]: Список ID роботов
        """
        return list(self._connections.keys())
    
    def get_connection_count(self) -> int:
        """
        Возвращает количество активных соединений
        
        Returns:
            int: Количество активных соединений
        """
        return len(self._connections)


# Глобальный экземпляр менеджера соединений
_connection_manager: Optional[RobotConnectionManager] = None


def get_connection_manager() -> RobotConnectionManager:
    """
    Возвращает глобальный экземпляр менеджера соединений (singleton)
    
    Returns:
        RobotConnectionManager: Экземпляр менеджера соединений
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = RobotConnectionManager()
    return _connection_manager
