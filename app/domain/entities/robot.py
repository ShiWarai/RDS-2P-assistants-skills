"""
Доменная сущность Robot
"""
from app.domain.value_objects.robot_id import RobotId


class Robot:
    """Робот в системе"""
    
    def __init__(self, robot_id: RobotId, name: str = None):
        """
        Создает робота
        
        Args:
            robot_id: ID робота
            name: Имя робота (опционально)
        """
        self._robot_id = robot_id
        self._name = name or f"Робот {robot_id.value}"
    
    @property
    def robot_id(self) -> RobotId:
        """Возвращает ID робота"""
        return self._robot_id
    
    @property
    def name(self) -> str:
        """Возвращает имя робота"""
        return self._name
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Robot):
            return False
        return self._robot_id == other._robot_id
    
    def __hash__(self) -> int:
        return hash(self._robot_id)
    
    def __repr__(self) -> str:
        return f"Robot(robot_id={self._robot_id}, name='{self._name}')"
