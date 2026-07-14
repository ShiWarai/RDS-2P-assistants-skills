"""
DTO для запроса обработки команды
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

from app.domain.value_objects.platform import Platform


@dataclass
class CommandRequestDTO:
    """DTO для запроса обработки команды"""
    user_id: Optional[str]
    utterance: str
    is_new_session: bool
    intent: str
    data: Dict[str, Any]
    platform: Platform
    message: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    version: str = "1.0"

    @property
    def is_chatapp(self) -> bool:
        """Обратная совместимость для тестов."""
        return self.platform == Platform.SALUTE_CHATAPP
