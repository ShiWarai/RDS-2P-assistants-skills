"""
Сборка ответов для платформы Salute (ChatApp + legacy).
"""
from typing import Dict, Any, List, Optional

from app.application.dto.command_request import CommandRequestDTO
from app.domain.value_objects.platform import Platform


def create_chatapp_response(
    data: Dict[str, Any],
    text: str,
    finished: bool = False,
    auto_listening: Optional[bool] = None,
    show_suggestions: bool = True,
) -> Dict[str, Any]:
    payload = {
        "items": [{
            "bubble": {
                "text": text,
                "expand_policy": "preserve_panel_state",
            }
        }],
        "pronounceText": text,
        "pronounceTextType": "application/text",
        "finished": finished,
    }

    if auto_listening is None:
        auto_listening = not finished

    if not finished:
        payload["auto_listening"] = auto_listening
        if show_suggestions:
            payload["suggestions"] = {
                "buttons": [{
                    "title": "Помощь",
                    "action": {"text": "помощь", "type": "text"},
                }]
            }

    return {
        "messageId": data.get("messageId"),
        "sessionId": data.get("sessionId"),
        "uuid": data.get("uuid", {}),
        "messageName": "ANSWER_TO_USER",
        "payload": payload,
    }


def create_chatapp_response_multiple(
    data: Dict[str, Any],
    texts: List[str],
    finished: bool = False,
) -> Dict[str, Any]:
    items = []
    all_text = ""
    for text in texts:
        items.append({
            "bubble": {"text": text, "expand_policy": "preserve_panel_state"},
        })
        if all_text:
            all_text += " "
        all_text += text

    payload = {
        "items": items,
        "pronounceText": all_text,
        "pronounceTextType": "application/text",
        "finished": finished,
    }
    if not finished:
        payload["auto_listening"] = True

    return {
        "messageId": data.get("messageId"),
        "sessionId": data.get("sessionId"),
        "uuid": data.get("uuid", {}),
        "messageName": "ANSWER_TO_USER",
        "payload": payload,
    }


def create_legacy_response(
    text: str,
    session: Dict[str, Any],
    version: str,
    end_session: bool = False,
) -> Dict[str, Any]:
    return {
        "response": {"text": text, "end_session": end_session},
        "version": version,
        "session": session,
    }


def build_salute_response(
    request: CommandRequestDTO,
    text_or_messages,
    finished: bool,
    *,
    has_binding_state: bool,
    has_help_state: bool,
    has_command_detail_state: bool,
) -> tuple[str, Dict[str, Any]]:
    if isinstance(text_or_messages, list):
        if request.platform == Platform.SALUTE_CHATAPP:
            payload = create_chatapp_response_multiple(request.data, text_or_messages, finished)
            return "\n".join(text_or_messages), payload
        text = " ".join(text_or_messages)
        return text, create_legacy_response(text, request.session or {}, request.version, finished)

    text = text_or_messages
    if request.platform == Platform.SALUTE_CHATAPP:
        auto_listening = None
        show_suggestions = False
        if "помолчим" in text.lower() and not finished:
            auto_listening = False
        elif not (has_help_state or has_command_detail_state or has_binding_state):
            if any(emoji in text for emoji in ["🐾", "🎖️", "✨", "💤", "🤸", "🏃", "🛑", "🎮"]) and not finished:
                show_suggestions = True
        payload = create_chatapp_response(
            request.data, text, finished, auto_listening, show_suggestions
        )
        return text, payload

    return text, create_legacy_response(text, request.session or {}, request.version, finished)
