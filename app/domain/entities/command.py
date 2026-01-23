"""
Доменная сущность Command
"""
from typing import Optional, Dict, Any
from app.domain.value_objects.robot_command import RobotCommand


class Command:
    """Команда пользователя"""
    
    def __init__(
        self,
        utterance: str,
        function_name: Optional[str] = None,
        command_type: RobotCommand = RobotCommand.UNKNOWN,
        motor_command: Optional[Dict[str, Any]] = None
    ):
        """
        Создает команду
        
        Args:
            utterance: Текст команды от пользователя
            function_name: Имя функции для выполнения (если распознана)
            command_type: Тип команды (Enum RobotCommand)
            motor_command: Команда для моторов робота
        """
        if not utterance:
            raise ValueError("utterance не может быть пустым")
        self._utterance = utterance
        self._function_name = function_name
        self._command_type = command_type
        self._motor_command = motor_command or {}
    
    @property
    def utterance(self) -> str:
        """Возвращает текст команды"""
        return self._utterance
    
    @property
    def function_name(self) -> Optional[str]:
        """Возвращает имя функции"""
        return self._function_name
    
    @property
    def command_type(self) -> RobotCommand:
        """Возвращает тип команды"""
        return self._command_type
    
    @property
    def motor_command(self) -> Dict[str, Any]:
        """Возвращает команду для моторов"""
        return self._motor_command.copy() if self._motor_command else {}
    
    def is_recognized(self) -> bool:
        """Проверяет, распознана ли команда"""
        return self._function_name is not None
    
    def __repr__(self) -> str:
        return f"Command(utterance='{self._utterance}', function='{self._function_name}', type='{self._command_type}')"
