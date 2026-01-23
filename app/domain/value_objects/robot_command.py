"""
Типы команд робота (Value Object)
"""
from enum import Enum


class RobotCommand(Enum):
    """
    Типы команд для робота.
    
    Используется для специальных команд (help, silence) 
    и как общая классификация.
    """
    HELP = "help"
    SILENCE = "silence"
    UNKNOWN = "unknown"
    ERROR = "error"
