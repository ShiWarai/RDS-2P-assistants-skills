"""
Webhook Алисы (Яндекс Диалоги).
"""
import json
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from app.application.dependencies import create_process_command_use_case
from app.application.dto.command_request import CommandRequestDTO
from app.application.use_cases.process_command import ProcessCommandUseCase
from app.domain.value_objects.platform import Platform
from app.platforms.alice.parser import (
    extract_user_id,
    extract_utterance,
    is_ping_request,
    extract_number_entities,
    apply_number_to_bind_utterance,
)
from app.platforms.alice.responses import create_alice_ping_response

logger = logging.getLogger(__name__)

router = APIRouter()


def get_process_command_use_case() -> ProcessCommandUseCase:
    try:
        return create_process_command_use_case()
    except Exception as e:
        logger.error("Ошибка создания ProcessCommandUseCase: %s", e, exc_info=True)
        raise


def log_user_command(utterance: str, user_id: Optional[str] = None) -> None:
    context = {}
    if user_id:
        context["user_id"] = user_id[:20] + "..." if len(user_id) > 20 else user_id
    log_msg = f"Команда (Alice): '{utterance}'"
    if context:
        log_msg += f" | Контекст: {context}"
    logger.info(log_msg)


@router.post("/v1/webhook")
async def webhook(
    request: Request,
    process_command_uc: ProcessCommandUseCase = Depends(get_process_command_use_case),
) -> JSONResponse:
    try:
        data: Dict[str, Any] = await request.json()
        logger.debug("=== ПОЛНЫЙ ВХОДЯЩИЙ JSON (Alice) ===")
        logger.debug(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error("Ошибка парсинга JSON: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        if is_ping_request(data):
            return JSONResponse(
                content=create_alice_ping_response(data),
                media_type="application/json",
            )

        session = data.get("session", {})
        req = data.get("request", {})
        user_id = extract_user_id(data)
        is_new_session = session.get("new", False)
        utterance = extract_utterance(data)

        numbers = extract_number_entities(data)
        utterance = apply_number_to_bind_utterance(utterance, numbers)

        if utterance:
            log_user_command(utterance, user_id)

        command_request = CommandRequestDTO(
            user_id=user_id,
            utterance=utterance,
            is_new_session=is_new_session,
            intent="",
            data=data,
            platform=Platform.ALICE,
            message=req,
            session=session,
            version=data.get("version", "1.0"),
        )

        command_response = await process_command_uc.execute(command_request)
        logger.info("Ответ: '%s'", command_response.text)

        return JSONResponse(
            content=command_response.response_payload,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
    except Exception as e:
        logger.error("Ошибка обработки запроса: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
