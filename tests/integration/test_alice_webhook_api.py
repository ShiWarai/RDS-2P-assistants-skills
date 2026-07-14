"""
Интеграционные тесты для POST /v1/webhook (Alice).
"""
import pytest

pytestmark = pytest.mark.integration


def _alice_payload(utterance: str, user_id: str = "test-user-1", new_session: bool = False):
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


def _alice_text(data: dict) -> str:
    return data.get("response", {}).get("text", "")


def test_alice_webhook_bind_robot_returns_instruction(alice_client):
    payload = _alice_payload("привяжи робота 0")
    resp = alice_client.post("/v1/webhook", json=payload)
    assert resp.status_code == 200
    text = _alice_text(resp.json())
    assert "код" in text.lower() or "привяз" in text.lower()


def test_alice_webhook_help_returns_menu(alice_client):
    payload = _alice_payload("помощь")
    resp = alice_client.post("/v1/webhook", json=payload)
    assert resp.status_code == 200
    text = _alice_text(resp.json())
    assert "служебн" in text.lower() or "раздел" in text.lower()


def test_alice_webhook_help_then_service_commands(alice_client):
    user = "alice-help-flow"
    alice_client.post("/v1/webhook", json=_alice_payload("помощь", user_id=user))
    resp = alice_client.post("/v1/webhook", json=_alice_payload("служебные", user_id=user))
    assert resp.status_code == 200
    text = _alice_text(resp.json())
    assert "привяжи" in text.lower() or "служебн" in text.lower()


def test_alice_webhook_service_section_without_help_state(alice_client):
    resp = alice_client.post("/v1/webhook", json=_alice_payload("служебная"))
    assert resp.status_code == 200
    text = _alice_text(resp.json())
    assert "привяжи" in text.lower() or "молчи" in text.lower()


def test_alice_webhook_command_without_binding(alice_client):
    payload = _alice_payload("лапу")
    resp = alice_client.post("/v1/webhook", json=payload)
    assert resp.status_code == 200
    text = _alice_text(resp.json())
    assert "привяж" in text.lower() or "робот" in text.lower()


def test_alice_webhook_command_with_binding(alice_client):
    user = "user-bound-alice"
    alice_client.post("/v1/webhook", json=_alice_payload("привяжи робота 0", user_id=user))
    alice_client.post("/v1/webhook", json=_alice_payload("1234", user_id=user))

    resp = alice_client.post("/v1/webhook", json=_alice_payload("лапу", user_id=user))
    assert resp.status_code == 200
    text = _alice_text(resp.json())
    assert "лапу" in text.lower() or "🐾" in text


def test_alice_webhook_ping(alice_client):
    payload = _alice_payload("ping")
    resp = alice_client.post("/v1/webhook", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"]["text"] == "pong"
    assert data["response"]["end_session"] is True
