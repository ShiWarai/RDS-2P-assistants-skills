"""
Unit-тесты ответов Alice.
"""
import pytest

from app.application.dto.command_request import CommandRequestDTO
from app.domain.value_objects.platform import Platform
from app.platforms.alice.responses import (
    create_alice_response,
    create_alice_ping_response,
    build_alice_response,
)

pytestmark = pytest.mark.unit


def test_create_alice_response_with_button():
    data = {"version": "1.0"}
    payload = create_alice_response(data, "Робот поднимает лапу! 🐾", show_help_button=True)
    assert payload["response"]["text"] == "Робот поднимает лапу! 🐾"
    assert payload["response"]["end_session"] is False
    assert payload["response"]["buttons"][0]["title"] == "Помощь"
    assert payload["version"] == "1.0"


def test_create_alice_ping_response():
    payload = create_alice_ping_response({"version": "1.0"})
    assert payload["response"]["text"] == "pong"
    assert payload["response"]["end_session"] is True


def test_build_alice_response_joins_multiple_messages():
    request = CommandRequestDTO(
        user_id="u1",
        utterance="",
        is_new_session=False,
        intent="",
        data={"version": "1.0"},
        platform=Platform.ALICE,
    )
    text, payload = build_alice_response(
        request,
        ["строка 1", "строка 2"],
        False,
        has_binding_state=False,
        has_help_state=False,
        has_command_detail_state=False,
    )
    assert text == "строка 1\nстрока 2"
    assert "строка 1" in payload["response"]["text"]
