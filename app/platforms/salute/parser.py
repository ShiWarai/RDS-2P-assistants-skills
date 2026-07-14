"""
Парсинг запросов Salute (ChatApp + legacy).
"""
from typing import Dict, Any, Optional, List

from app.utils.request_parser import (
    extract_utterance_chatapp,
    extract_utterance_legacy,
    extract_number_tokens_from_tokenized,
    extract_user_id,
)

__all__ = [
    "extract_utterance_chatapp",
    "extract_utterance_legacy",
    "extract_number_tokens_from_tokenized",
    "extract_user_id",
]
