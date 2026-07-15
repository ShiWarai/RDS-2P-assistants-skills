"""
Сборка ответов для навыка Алисы.
https://yandex.ru/dev/dialogs/alice/doc/ru/response

У API Алисы нет auto_listening: «молчи» не выключает микрофон как в Salute.
end_session=true — полный выход из навыка, не пауза.
"""
from typing import Dict, Any, List, Union

from app.application.dto.command_request import CommandRequestDTO


def create_alice_response(
    data: Dict[str, Any],
    text: str,
    end_session: bool = False,
    show_help_button: bool = False,
) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "text": text,
        "end_session": end_session,
    }
    if show_help_button and not end_session:
        response["buttons"] = [{"title": "Помощь", "hide": True}]
    return {
        "response": response,
        "version": data.get("version", "1.0"),
    }


def create_alice_ping_response(data: Dict[str, Any]) -> Dict[str, Any]:
    return create_alice_response(data, "pong", end_session=True)


def build_alice_response(
    request: CommandRequestDTO,
    text_or_messages: Union[str, List[str]],
    finished: bool,
    *,
    has_binding_state: bool,
    has_help_state: bool,
    has_command_detail_state: bool,
) -> tuple[str, Dict[str, Any]]:
    del has_binding_state, has_help_state, has_command_detail_state

    if isinstance(text_or_messages, list):
        text = "\n".join(text_or_messages)
    else:
        text = text_or_messages

    show_help = False
    if not finished and text:
        if any(emoji in text for emoji in ["🐾", "🎖️", "✨", "💤", "🤸", "🏃", "🛑", "🎮"]):
            show_help = True

    payload = create_alice_response(
        request.data,
        text,
        end_session=finished,
        show_help_button=show_help,
    )
    return text, payload
