"""
Webhook Salute (SmartApp / ChatApp API).
"""
import json
import logging
import re
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from app.application.dependencies import create_process_command_use_case
from app.application.dto.command_request import CommandRequestDTO
from app.application.use_cases.process_command import ProcessCommandUseCase
from app.domain.value_objects.platform import Platform
from app.platforms.salute.parser import (
    extract_utterance_chatapp,
    extract_utterance_legacy,
    extract_number_tokens_from_tokenized,
    extract_user_id,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_process_command_use_case() -> ProcessCommandUseCase:
    try:
        return create_process_command_use_case()
    except Exception as e:
        logger.error("Ошибка создания ProcessCommandUseCase: %s", e, exc_info=True)
        raise


def log_user_command(user_visible_text: str, utterance: str, user_id: Optional[str] = None) -> None:
    context = {}
    if user_id:
        context["user_id"] = user_id[:20] + "..." if len(user_id) > 20 else user_id
    if user_visible_text:
        log_msg = f"Команда (видимая пользователю): '{user_visible_text}'"
        if context:
            log_msg += f" | Контекст: {context}"
        logger.info(log_msg)
    if utterance != user_visible_text:
        logger.debug("Команда (для обработки): '%s'", utterance)


@router.post("/v1/webhook")
async def webhook(
    request: Request,
    process_command_uc: ProcessCommandUseCase = Depends(get_process_command_use_case),
) -> JSONResponse:
    try:
        data: Dict[str, Any] = await request.json()
        logger.debug("=== ПОЛНЫЙ ВХОДЯЩИЙ JSON (Salute) ===")
        logger.debug(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        logger.error("Ошибка парсинга JSON: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        message_name = data.get("messageName", "")
        user_id = extract_user_id(data.get("uuid", {}))

        if message_name == "MESSAGE_TO_SKILL":
            payload = data.get("payload", {})
            message = payload.get("message", {})
            is_new_session = payload.get("new_session", False)
            intent = payload.get("intent", "")

            user_visible_text = message.get("human_normalized_text") or message.get("original_text", "")
            utterance = extract_utterance_chatapp(message)
            log_user_command(user_visible_text, utterance, user_id)

            if "num_token" in utterance.lower():
                tokenized = message.get("tokenized_elements_list", [])
                number_tokens = extract_number_tokens_from_tokenized(tokenized)
                if number_tokens:
                    value = number_tokens[0]
                    utterance = utterance.replace("num_token", str(value)).replace("NUM_TOKEN", str(value))

            if any(word in utterance.lower() for word in ["привяжи", "привязать", "подключи", "настрой"]):
                if not re.search(
                    r"(привяжи|привязать|подключи|настрой)\s+(робот|робота|панду)\s+\d+",
                    utterance.lower(),
                ):
                    tokenized = message.get("tokenized_elements_list", [])
                    number_tokens = extract_number_tokens_from_tokenized(tokenized)
                    if number_tokens:
                        value = number_tokens[0]
                        utterance = re.sub(
                            r"(привяжи\s+робот|привязать\s+робот|привяжи\s+робота|привязать\s+робота|привяжи\s+панду|привязать\s+панду)\s+\w+",
                            rf"\1 {value}",
                            utterance.lower(),
                        )

            command_request = CommandRequestDTO(
                user_id=user_id,
                utterance=utterance,
                is_new_session=is_new_session,
                intent=intent,
                data=data,
                platform=Platform.SALUTE_CHATAPP,
                message=message,
            )
        else:
            session = data.get("session", {})
            req = data.get("request", {})
            version = data.get("version", "1.0")
            is_new_session = session.get("new", False)
            utterance = extract_utterance_legacy(data, req)
            if utterance:
                log_user_command(utterance, utterance, user_id)

            command_request = CommandRequestDTO(
                user_id=user_id,
                utterance=utterance,
                is_new_session=is_new_session,
                intent="",
                data=data,
                platform=Platform.SALUTE_LEGACY,
                message=None,
                session=session,
                version=version,
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
