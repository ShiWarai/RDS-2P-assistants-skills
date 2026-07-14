"""
Парсинг запросов Яндекс Диалогов (Алиса).
https://yandex.ru/dev/dialogs/alice/doc/ru/request
"""
import re
from typing import Dict, Any, Optional, List


def extract_user_id(data: Dict[str, Any]) -> Optional[str]:
    session = data.get("session", {})
    user = session.get("user", {})
    raw = user.get("user_id")
    if raw is None:
        application = session.get("application", {})
        raw = application.get("application_id") or session.get("user_id")
    if raw is None:
        return None
    return str(raw).strip() or None


def is_ping_request(data: Dict[str, Any]) -> bool:
    req = data.get("request", {})
    return req.get("original_utterance", "").strip().lower() == "ping"


def extract_utterance(data: Dict[str, Any]) -> str:
    req = data.get("request", {})
    req_type = req.get("type", "")

    if req_type == "ButtonPressed":
        payload = req.get("payload")
        if isinstance(payload, dict) and payload.get("text"):
            return str(payload["text"]).lower().strip()
        if isinstance(payload, str) and payload:
            return payload.lower().strip()
        return (req.get("command") or "").lower().strip()

    original = req.get("original_utterance", "")
    if original:
        return original.lower().strip()
    return (req.get("command") or "").lower().strip()


def extract_number_entities(data: Dict[str, Any]) -> List[str]:
    """Извлекает YANDEX.NUMBER из request.nlu.entities."""
    req = data.get("request", {})
    nlu = req.get("nlu", {})
    entities = nlu.get("entities", [])
    numbers = []
    for entity in entities:
        if entity.get("type") == "YANDEX.NUMBER":
            value = entity.get("value")
            if value is not None:
                numbers.append(str(int(value) if isinstance(value, float) else value))
    return numbers


def apply_number_to_bind_utterance(utterance: str, numbers: List[str]) -> str:
    """Подставляет число из NLU в команду привязки, если его нет в тексте."""
    if not numbers:
        return utterance
    if re.search(
        r"(привяжи|привязать|подключи|настрой)\s+(робот|робота|панду)\s+\d+",
        utterance.lower(),
    ):
        return utterance
    value = numbers[0]
    return re.sub(
        r"(привяжи\s+робот|привязать\s+робот|привяжи\s+робота|привязать\s+робота|привяжи\s+панду|привязать\s+панду)\s+\w+",
        rf"\1 {value}",
        utterance.lower(),
    )


def extract_code_from_nlu(data: Dict[str, Any], utterance: str) -> Optional[str]:
    """4 цифры из NLU entities или utterance."""
    from app.utils.request_parser import extract_code_from_utterance

    code = extract_code_from_utterance(utterance)
    if code:
        return code

    numbers = extract_number_entities(data)
    if len(numbers) == 4:
        return "".join(numbers)
    return None
