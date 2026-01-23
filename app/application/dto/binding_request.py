"""
DTO для запроса привязки робота
"""
from dataclasses import dataclass
from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode


@dataclass
class BindingRequestDTO:
    """DTO для запроса привязки робота"""
    user_id: str
    robot_id: RobotId


@dataclass
class BindingCodeRequestDTO:
    """DTO для запроса верификации кода привязки"""
    user_id: str
    code: BindingCode
