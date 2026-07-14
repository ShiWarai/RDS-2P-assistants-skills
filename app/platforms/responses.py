"""
Фабрика ответов по платформе.
"""
from typing import Dict, Any, List, Union

from app.application.dto.command_request import CommandRequestDTO
from app.domain.value_objects.platform import Platform
from app.platforms.salute.responses import build_salute_response
from app.platforms.alice.responses import build_alice_response


def build_platform_response(
    request: CommandRequestDTO,
    text_or_messages: Union[str, List[str]],
    finished: bool,
    *,
    has_binding_state: bool,
    has_help_state: bool,
    has_command_detail_state: bool,
) -> tuple[str, Dict[str, Any]]:
    if request.platform.is_salute:
        return build_salute_response(
            request,
            text_or_messages,
            finished,
            has_binding_state=has_binding_state,
            has_help_state=has_help_state,
            has_command_detail_state=has_command_detail_state,
        )
    if request.platform == Platform.ALICE:
        return build_alice_response(
            request,
            text_or_messages,
            finished,
            has_binding_state=has_binding_state,
            has_help_state=has_help_state,
            has_command_detail_state=has_command_detail_state,
        )
    raise ValueError(f"Unsupported platform: {request.platform}")
