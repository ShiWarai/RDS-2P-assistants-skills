"""
Платформа голосового ассистента.
"""
from enum import Enum


class Platform(str, Enum):
    SALUTE_CHATAPP = "salute_chatapp"
    SALUTE_LEGACY = "salute_legacy"
    ALICE = "alice"

    @property
    def is_salute(self) -> bool:
        return self in (Platform.SALUTE_CHATAPP, Platform.SALUTE_LEGACY)

    @property
    def is_salute_chatapp(self) -> bool:
        return self == Platform.SALUTE_CHATAPP

    @property
    def is_alice(self) -> bool:
        return self == Platform.ALICE
