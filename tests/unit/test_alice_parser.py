"""
Unit-тесты парсера Alice.
"""
import pytest

from app.platforms.alice.parser import (
    extract_user_id,
    extract_utterance,
    is_ping_request,
    extract_number_entities,
    apply_number_to_bind_utterance,
    extract_code_from_nlu,
)

pytestmark = pytest.mark.unit


def _alice_payload(utterance: str, user_id: str = "alice-user-1", new_session: bool = False):
    return {
        "version": "1.0",
        "session": {
            "new": new_session,
            "user": {"user_id": user_id},
        },
        "request": {
            "type": "SimpleUtterance",
            "original_utterance": utterance,
            "command": utterance,
            "nlu": {"entities": [], "tokens": utterance.split()},
        },
    }


def test_extract_user_id_from_session_user():
    data = _alice_payload("помощь")
    assert extract_user_id(data) == "alice-user-1"


def test_extract_user_id_fallback_application():
    data = {
        "session": {"application": {"application_id": "app-id-42"}},
        "request": {},
    }
    assert extract_user_id(data) == "app-id-42"


def test_is_ping_request():
    data = _alice_payload("ping")
    assert is_ping_request(data) is True
    assert is_ping_request(_alice_payload("помощь")) is False


def test_extract_utterance_simple():
    assert extract_utterance(_alice_payload("лапу")) == "лапу"


def test_extract_utterance_button_pressed():
    data = {
        "request": {
            "type": "ButtonPressed",
            "command": "помощь",
            "payload": {},
        }
    }
    assert extract_utterance(data) == "помощь"


def test_extract_number_entities():
    data = _alice_payload("привяжи робота 0")
    data["request"]["nlu"]["entities"] = [
        {"type": "YANDEX.NUMBER", "value": 0},
    ]
    assert extract_number_entities(data) == ["0"]


def test_apply_number_to_bind_utterance():
    result = apply_number_to_bind_utterance("привяжи робота num", ["0"])
    assert "0" in result


def test_extract_code_from_nlu_four_digits():
    data = _alice_payload("1 2 3 4")
    data["request"]["nlu"]["entities"] = [
        {"type": "YANDEX.NUMBER", "value": 1},
        {"type": "YANDEX.NUMBER", "value": 2},
        {"type": "YANDEX.NUMBER", "value": 3},
        {"type": "YANDEX.NUMBER", "value": 4},
    ]
    assert extract_code_from_nlu(data, "1 2 3 4") == "1234"
