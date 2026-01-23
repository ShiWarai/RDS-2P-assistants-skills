"""
API маршруты для SmartApp
"""
import json
import logging
import re
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import httpx

from app.services.robot_service import RobotService
from app.services.binding_service import BindingService
from app.services.grpc_service import initiate_binding, complete_binding_with_code, send_command_to_robot
from app.models.commands import RobotCommand
from app.utils.request_parser import (
    extract_utterance_chatapp,
    extract_utterance_legacy,
    extract_robot_id_from_bind_command,
    extract_code_from_utterance,
    extract_number_tokens_from_tokenized,
    is_bind_command,
    is_unbind_command
)
from app.utils.response_builder import create_chatapp_response, create_chatapp_response_multiple, create_legacy_response

logger = logging.getLogger(__name__)

router = APIRouter()

# Константы
GREETING_MESSAGE = "Привет! Я робот-панда 🐼! Скажите команду для управления."


async def request_binding_code(user_id: str, robot_id: str, binding_service: BindingService) -> tuple[bool, str, Optional[str], Optional[float]]:
    """
    Запрашивает код верификации у робота через gRPC
    
    Returns:
        tuple: (успех, сообщение, код, expires_at)
    """
    # Используем gRPC для инициации привязки
    success, message = initiate_binding(user_id, robot_id, binding_service)
    
    if success:
        # Получаем код из состояния привязки через BindingService
        code, expires_at = binding_service.get_binding_code(user_id)
        if code and expires_at:
            return True, message, code, expires_at
    
    return False, message, None, None


async def _handle_cancel_command(
    binding_service: BindingService,
    user_id: str,
    binding_state: Optional[str]
) -> tuple[str, bool]:
    """Обрабатывает команду отмены привязки"""
    if binding_state == "waiting_code":
        binding_service.cancel_binding(user_id)
        return "Привязка отменена.", False
    else:
        return "Нет активной операции для отмены.", False


async def _handle_code_input(
    binding_service: BindingService,
    user_id: str,
    utterance: str,
    message: Optional[Dict[str, Any]] = None
) -> tuple[Optional[str | List[str]], bool]:
    """Обрабатывает ввод кода верификации"""
    logger.debug(f"Извлечение кода из utterance: '{utterance}'")
    code = extract_code_from_utterance(utterance)
    
    # Если код не извлечён или выглядит подозрительно (все цифры одинаковые),
    # пробуем извлечь из tokenized_elements_list
    if (not code or (code and len(set(code)) == 1)) and message:
        logger.debug(f"Код не извлечён или подозрителен ({code}), пробуем tokenized_elements_list")
        tokenized = message.get("tokenized_elements_list", [])
        logger.debug(f"Tokenized elements для кода: {json.dumps(tokenized, ensure_ascii=False, indent=2)}")
        
        # Извлекаем все числовые токены используя общую функцию
        number_tokens = extract_number_tokens_from_tokenized(tokenized)
        
        # Если нашли ровно 4 числа, используем их как код
        if len(number_tokens) == 4:
            code = ''.join(number_tokens)
            logger.debug(f"Код извлечён из токенов: {code}")
    
    logger.debug(f"Извлеченный код: {code}")
    if code:
        # Используем gRPC функцию для завершения привязки
        success, message_text = complete_binding_with_code(user_id, code, binding_service)
        if success:
            robot_id = binding_service.get_robot_id(user_id)
            # Возвращаем список из двух сообщений
            return [
                f"Робот {robot_id} привязан! 🐼",
                GREETING_MESSAGE
            ], False
        else:
            return message_text, False
    else:
        return "Введите код или 'отмена'.", False


async def _handle_bind_start(
    binding_service: BindingService,
    user_id: str,
    utterance: str
) -> tuple[str, bool]:
    """Обрабатывает начало процесса привязки"""
    # Проверяем, не привязан ли уже робот
    if binding_service.has_binding(user_id):
        robot_id = binding_service.get_robot_id(user_id)
        return f"Робот {robot_id} уже привязан. Скажите 'отвяжи робота'.", False
    
    # Извлекаем ID робота
    logger.debug(f"=== ИЗВЛЕЧЕНИЕ ID РОБОТА ===")
    logger.debug(f"utterance для extract_robot_id_from_bind_command: '{utterance}'")
    robot_id = extract_robot_id_from_bind_command(utterance)
    logger.debug(f"Извлеченный robot_id: {robot_id}")
    if not robot_id:
        return "Укажите номер робота.", False
    
    # Запрашиваем код у робота через gRPC
    success, message_text, code, expires_at = await request_binding_code(user_id, robot_id, binding_service)
    if success and code and expires_at:
        logger.debug(f"Состояние привязки сохранено: user_id={user_id}, robot_id={robot_id}, code={code}")
        return f"Введите код для робота {robot_id}.", False
    else:
        return message_text, False


def _handle_unbind(
    binding_service: BindingService,
    user_id: str
) -> tuple[str, bool]:
    """Обрабатывает команду отвязки робота"""
    if binding_service.has_binding(user_id):
        robot_id = binding_service.get_robot_id(user_id)
        binding_service.unbind_robot(user_id)
        return f"Робот {robot_id} отвязан.", False
    else:
        return "У вас нет привязанного робота.", False


async def handle_binding_flow(
    binding_service: BindingService,
    user_id: str,
    utterance: str,
    message: Optional[Dict[str, Any]] = None
) -> tuple[Optional[str | List[str]], bool]:
    """
    Обрабатывает процесс привязки робота
    
    Returns:
        tuple: (текст ответа или список текстов для множественных сообщений, finished) 
               или (None, False) если команда не связана с привязкой
    """
    utterance_lower = utterance.lower().strip()
    
    # Проверяем команду отмены (обрабатываем в любом состоянии)
    has_binding_state = binding_service.has_user_state(user_id, "waiting_code")
    if any(word in utterance_lower for word in ["отмена", "отменить", "отменить привязку"]):
        return await _handle_cancel_command(binding_service, user_id, "waiting_code" if has_binding_state else None)
    
    # Кэшируем состояние привязки (уже получено выше)
    logger.debug(f"Состояние привязки для user_id={user_id}: {has_binding_state}, utterance='{utterance}'")
    
    # Если ожидается код - проверяем ввод кода
    if has_binding_state:
        return await _handle_code_input(binding_service, user_id, utterance, message)
    
    # Если нет активной привязки, проверяем команду начала привязки
    if is_bind_command(utterance):
        return await _handle_bind_start(binding_service, user_id, utterance)
    
    # Команда отвязки
    if is_unbind_command(utterance):
        return _handle_unbind(binding_service, user_id)
    
    # Команда не связана с привязкой
    return None, False


def get_robot_service() -> RobotService:
    """Dependency для получения RobotService"""
    from app.main import robot_service
    return robot_service


def get_binding_service() -> BindingService:
    """Dependency для получения BindingService"""
    from app.main import binding_service
    return binding_service


async def _process_command(
    binding_service: BindingService,
    robot_service: RobotService,
    user_id: Optional[str],
    utterance: str,
    message: Optional[Dict[str, Any]],
    is_new_session: bool,
    intent: str,
    data: Dict[str, Any],
    is_chatapp: bool = True,
    session: Optional[Dict[str, Any]] = None,
    version: str = "1.0"
) -> tuple[str, bool, Dict[str, Any]]:
    """
    Общая функция обработки команд для ChatApp и Legacy API
    
    Returns:
        tuple: (текст ответа, finished/end_session, response_payload)
    """
    finished = False
    
    if is_new_session or (is_chatapp and intent == "run_app" and not utterance):
        # Новая сессия - проверяем привязку
        if user_id and binding_service.has_binding(user_id):
            robot_id = binding_service.get_robot_id(user_id)
            if is_chatapp:
                text = f"Привет! Ваш робот {robot_id} готов к управлению."
            else:
                text = f"Привет! Ваш робот {robot_id} готов к управлению."
        else:
            text = "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'."
    elif utterance:
        has_binding_state = binding_service.has_user_state(user_id, "waiting_code") if user_id else False
        
        # Если в режиме привязки (waiting_code) - обрабатываем с поддержкой помощи
        if has_binding_state:
            utterance_lower = utterance.lower().strip()
            has_help_state = binding_service.has_user_state(user_id, "waiting_help_section") if user_id else False
            has_command_detail_state = binding_service.has_user_state(user_id, "waiting_command_detail") if user_id else False
            
            # Если пользователь в режиме выбора раздела помощи (может быть одновременно в режиме привязки)
            if has_help_state:
                if "служеб" in utterance_lower:
                    text = robot_service._get_service_commands_help()
                    binding_service.remove_user_state(user_id, "waiting_help_section")
                    finished = False
                elif "исполняем" in utterance_lower:
                    text = robot_service._get_robot_commands_help()
                    binding_service.remove_user_state(user_id, "waiting_help_section")
                    # Устанавливаем состояние ожидания выбора команды для подробного описания
                    if user_id:
                        binding_service.add_user_state(user_id, "waiting_command_detail")
                    finished = False
                else:
                    # Не выбор раздела - обрабатываем через handle_binding_flow
                    binding_text, binding_finished = await handle_binding_flow(binding_service, user_id, utterance, message)
                    if binding_text is not None:
                        if isinstance(binding_text, list):
                            if is_chatapp:
                                response_payload = create_chatapp_response_multiple(data, binding_text, binding_finished)
                                logger.info(f"Ответ: '{binding_text[0]}'")
                                return binding_text[0], binding_finished, response_payload
                            text = " ".join(binding_text)
                        else:
                            text = binding_text
                        finished = binding_finished
                    else:
                        text = "Введите код привязки или скажите 'отмена'."
                        finished = False
            elif has_command_detail_state:
                # Пользователь в режиме ожидания выбора команды для подробного описания
                # Ищем название команды в запросе (формат: "расскажи про бегать" или просто "бегать")
                utterance_lower = utterance.lower().strip()
                
                # Убираем префиксы типа "расскажи про", "про команду" и т.д.
                command_name = utterance_lower
                for prefix in ["расскажи про", "про команду", "про", "команда", "команду"]:
                    if utterance_lower.startswith(prefix):
                        command_name = utterance_lower[len(prefix):].strip()
                        # Убираем кавычки если есть
                        command_name = command_name.strip('"\'')
                        break
                
                # Убираем кавычки если они есть
                command_name = command_name.strip('"\'')
                
                description = robot_service._get_command_description(command_name)
                if description:
                    text = description
                    binding_service.remove_user_state(user_id, "waiting_command_detail")
                    finished = False
                else:
                    # Не удалось найти команду - обрабатываем через handle_binding_flow
                    binding_text, binding_finished = await handle_binding_flow(binding_service, user_id, utterance, message)
                    if binding_text is not None:
                        if isinstance(binding_text, list):
                            if is_chatapp:
                                response_payload = create_chatapp_response_multiple(data, binding_text, binding_finished)
                                logger.info(f"Ответ: '{binding_text[0]}'")
                                return binding_text[0], binding_finished, response_payload
                            text = " ".join(binding_text)
                        else:
                            text = binding_text
                        finished = binding_finished
                    else:
                        binding_service.remove_user_state(user_id, "waiting_command_detail")
                        text = "Введите код привязки или скажите 'отмена'."
                        finished = False
            else:
                # Сначала проверяем, не запросил ли пользователь помощь (через CVC)
                result = robot_service.process_command(utterance)
                if result.command == RobotCommand.HELP and "служебн" not in utterance_lower and "исполняем" not in utterance_lower:
                    # Пользователь запросил помощь в режиме привязки - добавляем состояние помощи
                    if user_id:
                        binding_service.add_user_state(user_id, "waiting_help_section")
                    text = result.text
                    finished = result.finished
                else:
                    # Обрабатываем через handle_binding_flow (без CVC)
                    binding_text, binding_finished = await handle_binding_flow(binding_service, user_id, utterance, message)
                    if binding_text is not None:
                        if isinstance(binding_text, list):
                            if is_chatapp:
                                response_payload = create_chatapp_response_multiple(data, binding_text, binding_finished)
                                logger.info(f"Ответ: '{binding_text[0]}'")
                                return binding_text[0], binding_finished, response_payload
                            text = " ".join(binding_text)
                        else:
                            text = binding_text
                        finished = binding_finished
                    else:
                        text = "Введите код привязки или скажите 'отмена'."
                        finished = False
        else:
            # Не в режиме привязки - проверяем через CVC, является ли это командой привязки/отвязки
            utterance_lower = utterance.lower().strip()
            
            # Проверяем команду отмены вне режима привязки (не имеет смысла, но обрабатываем)
            if any(word in utterance_lower for word in ["отмена", "отменить", "отменить привязку"]):
                text = "Нет активной операции для отмены."
                finished = False
            else:
                # Проверяем состояние режима помощи
                has_help_state = binding_service.has_user_state(user_id, "waiting_help_section") if user_id else False
                has_command_detail_state = binding_service.has_user_state(user_id, "waiting_command_detail") if user_id else False
                
                if has_help_state:
                    # Пользователь в режиме выбора раздела помощи
                    if "служеб" in utterance_lower:
                        text = robot_service._get_service_commands_help()
                        binding_service.remove_user_state(user_id, "waiting_help_section")
                        finished = False
                    elif "исполняем" in utterance_lower:
                        text = robot_service._get_robot_commands_help()
                        binding_service.remove_user_state(user_id, "waiting_help_section")
                        # Устанавливаем состояние ожидания выбора команды для подробного описания
                        if user_id:
                            binding_service.add_user_state(user_id, "waiting_command_detail")
                        finished = False
                    else:
                        # Не выбор раздела - очищаем состояние и обрабатываем как обычную команду
                        binding_service.remove_user_state(user_id, "waiting_help_section")
                        # Продолжаем обработку команды ниже
                        has_help_state = False  # Сбрасываем, чтобы обработать команду
                elif has_command_detail_state:
                    # Пользователь в режиме ожидания выбора команды для подробного описания
                    # Ищем название команды в запросе (формат: "расскажи про бегать" или просто "бегать")
                    utterance_lower = utterance.lower().strip()
                    
                    # Убираем префиксы типа "расскажи про", "про команду" и т.д.
                    command_name = utterance_lower
                    for prefix in ["расскажи про", "про команду", "про", "команда", "команду"]:
                        if utterance_lower.startswith(prefix):
                            command_name = utterance_lower[len(prefix):].strip()
                            # Убираем кавычки если есть
                            command_name = command_name.strip('"\'')
                            break
                    
                    # Убираем кавычки если они есть
                    command_name = command_name.strip('"\'')
                    
                    description = robot_service._get_command_description(command_name)
                    if description:
                        text = description
                        binding_service.remove_user_state(user_id, "waiting_command_detail")
                        finished = False
                    else:
                        # Не удалось найти команду - очищаем состояние и обрабатываем как обычную команду
                        binding_service.remove_user_state(user_id, "waiting_command_detail")
                        has_command_detail_state = False
                
                # Обрабатываем команду (если не было выбора раздела помощи и не было выбора команды)
                if not has_help_state and not has_command_detail_state:
                    logger.info(f"Проверка привязки: user_id={user_id}, has_binding={binding_service.has_binding(user_id) if user_id else False}")
                    result = robot_service.process_command(utterance)
                    
                    # Получаем function_name из результата (может быть от CVC)
                    function_name = result.motor_command.get("function") if result.motor_command else None
                    
                    # Если это команда помощи, устанавливаем состояние
                    if result.command == RobotCommand.HELP and "служебн" not in utterance_lower and "исполняем" not in utterance_lower:
                        if user_id:
                            binding_service.add_user_state(user_id, "waiting_help_section")
                        # Устанавливаем text из result для команды помощи
                        text = result.text
                        finished = result.finished
                    # Проверяем, является ли команда командой привязки/отвязки от CVC
                    elif function_name == "bind":
                        # Команда привязки от CVC - извлекаем номер робота и начинаем процесс привязки
                        binding_text, binding_finished = await _handle_bind_start(binding_service, user_id, utterance)
                        if isinstance(binding_text, list):
                            if is_chatapp:
                                response_payload = create_chatapp_response_multiple(data, binding_text, binding_finished)
                                logger.info(f"Ответ: '{binding_text[0]}'")
                                return binding_text[0], binding_finished, response_payload
                            text = " ".join(binding_text)
                        else:
                            text = binding_text
                        finished = binding_finished
                    elif function_name == "unbind":
                        # Команда отвязки от CVC
                        binding_text, binding_finished = _handle_unbind(binding_service, user_id)
                        text = binding_text
                        finished = binding_finished
                    elif user_id and binding_service.has_binding(user_id):
                        # Обычная команда для робота (требует привязки)
                        # Если команда распознана и требует выполнения, отправляем через gRPC
                        if result.success and result.motor_command and result.motor_command.get("function"):
                            # Извлекаем имя функции для отправки роботу
                            function_name = result.motor_command.get("function")
                            logger.info(f"Отправка команды роботу: function={function_name}, user_id={user_id}")
                            success, message = send_command_to_robot(user_id, function_name, binding_service)
                            if success:
                                # Команда успешно отправлена - используем текст об успехе
                                text = result.text
                            else:
                                # Команда не отправлена - показываем ТОЛЬКО сообщение об ошибке (без текста об успехе)
                                # ВАЖНО: полностью заменяем text на message, не объединяем!
                                text = message
                        else:
                            # Команды HELP, SILENCE или нераспознанные команды - используем текст из result
                            text = result.text
                            if not result.success:
                                logger.warning(f"Команда не распознана или нет функции: success={result.success}, motor_command={result.motor_command}")
                        
                        finished = result.finished
                    else:
                        # Команда требует привязки, но привязки нет
                        text = "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'."
                        finished = False
    else:
        if is_chatapp:
            if user_id and binding_service.has_binding(user_id):
                text = "Скажите команду для робота. Для списка команд - 'помощь'."
            else:
                text = "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'."
        else:
            text = "Не понял команду."
    
    # Создаём response payload в зависимости от формата API
    if is_chatapp:
        response_payload = create_chatapp_response(data, text, finished)
    else:
        response_payload = create_legacy_response(text, session or {}, version, finished)
    
    return text, finished, response_payload


def log_user_command(user_visible_text: str, utterance: str, user_id: Optional[str] = None) -> None:
    """
    Единообразное логирование команд пользователя с контекстом
    
    Args:
        user_visible_text: Текст, который видит пользователь на экране
        utterance: Текст, используемый для обработки
        user_id: ID пользователя (опционально)
    """
    context = {}
    if user_id:
        context["user_id"] = user_id[:20] + "..." if len(user_id) > 20 else user_id
    
    if user_visible_text:
        log_msg = f"Команда (видимая пользователю): '{user_visible_text}'"
        if context:
            log_msg += f" | Контекст: {context}"
        logger.info(log_msg)
    
    if utterance != user_visible_text:
        logger.debug(f"Команда (для обработки): '{utterance}'")


@router.post("/v1/webhook")
async def webhook(
    request: Request,
    robot_service: RobotService = Depends(get_robot_service),
    binding_service: BindingService = Depends(get_binding_service)
) -> JSONResponse:
    """Основной endpoint для обработки запросов от SmartApp API"""
    try:
        data: Dict[str, Any] = await request.json()
        logger.debug(f"=== ПОЛНЫЙ ВХОДЯЩИЙ JSON ===")
        logger.debug(json.dumps(data, ensure_ascii=False, indent=2))
        
    except Exception as e:
        logger.error(f"Ошибка парсинга JSON: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        message_name = data.get("messageName", "")
        logger.debug(f"Message name: {message_name}")
        
        # Извлекаем user_id
        user_id = binding_service.get_user_id(data.get("uuid", {}))
        logger.debug(f"User ID: {user_id}")
        
        # Определяем формат запроса: новый ChatApp API или старый SmartApp API
        if message_name == "MESSAGE_TO_SKILL":
            # Новый формат ChatApp API
            payload = data.get("payload", {})
            message = payload.get("message", {})
            is_new_session = payload.get("new_session", False)
            intent = payload.get("intent", "")
            
            logger.debug(f"=== MESSAGE DATA ===")
            logger.debug(json.dumps(message, ensure_ascii=False, indent=2))
            logger.debug(f"is_new_session: {is_new_session}, intent: {intent}")
            
            # Логируем команду пользователя единообразно
            user_visible_text = message.get("human_normalized_text") or message.get("original_text", "")
            utterance = extract_utterance_chatapp(message)
            log_user_command(user_visible_text, utterance, user_id)
            
            # Детальная информация только в DEBUG режиме
            logger.debug(f"Варианты текста: original='{message.get('original_text', '')}', "
                        f"human_normalized='{message.get('human_normalized_text', '')}', "
                        f"normalized='{message.get('normalized_text', '')}', "
                        f"utterance для обработки='{utterance}'")
            
            # Если в utterance есть num_token, заменяем на число из токенов
            # Это нужно сделать ПЕРВЫМ, до других обработок
            if "num_token" in utterance.lower():
                logger.debug(f"Обнаружен num_token в utterance")
                tokenized = message.get("tokenized_elements_list", [])
                logger.debug(f"=== TOKENIZED ELEMENTS (для num_token) ===")
                logger.debug(f"Tokenized JSON: {json.dumps(tokenized, ensure_ascii=False, indent=2)}")
                
                # Извлекаем числовые токены используя общую функцию
                number_tokens = extract_number_tokens_from_tokenized(tokenized)
                
                if number_tokens:
                    # Берём первое найденное число для замены num_token
                    value = number_tokens[0]
                    utterance = utterance.replace("num_token", str(value)).replace("NUM_TOKEN", str(value))
                    logger.debug(f"Заменен num_token на {value}")
                else:
                    logger.debug(f"Числовой токен не найден для num_token")
            
            # Извлекаем число из tokenized_elements_list для команд привязки
            # Это нужно, даже если normalized_text неправильно преобразовал число
            if any(word in utterance.lower() for word in ["привяжи", "привязать", "подключи", "настрой"]):
                # Проверяем, есть ли уже число в utterance
                if not re.search(r"(привяжи|привязать|подключи|настрой)\s+(робот|робота|панду)\s+\d+", utterance.lower()):
                    logger.debug(f"Числа нет в utterance, ищем в токенах")
                    tokenized = message.get("tokenized_elements_list", [])
                    logger.debug(f"=== TOKENIZED ELEMENTS (для извлечения числа) ===")
                    logger.debug(f"Tokenized JSON: {json.dumps(tokenized, ensure_ascii=False, indent=2)}")
                    
                    # Извлекаем числовые токены используя общую функцию
                    number_tokens = extract_number_tokens_from_tokenized(tokenized)
                    
                    if number_tokens:
                        # Берём первое найденное число
                        value = number_tokens[0]
                        logger.debug(f"Извлеченное число из токена: {value}")
                        # Заменяем последнее слово после "робот/робота" на число
                        old_utterance = utterance
                        utterance = re.sub(
                            r"(привяжи\s+робот|привязать\s+робот|привяжи\s+робота|привязать\s+робота|привяжи\s+панду|привязать\s+панду)\s+\w+",
                            rf"\1 {value}",
                            utterance.lower()
                        )
                        logger.debug(f"Utterance до замены: '{old_utterance}'")
                        logger.debug(f"Utterance после замены: '{utterance}'")
                    else:
                        logger.debug(f"Числовой токен не найден")
                else:
                    logger.debug(f"Число уже есть в utterance, замена не требуется")
            
            logger.debug(f"Финальный utterance для обработки: '{utterance}'")
            
            # Обрабатываем команду (общая логика для ChatApp API)
            text, finished, response_payload = await _process_command(
                binding_service, robot_service, user_id, utterance, message,
                is_new_session, intent, data, is_chatapp=True
            )
            
            # Логируем ответ бота
            logger.info(f"Ответ: '{text}'")
            
        else:
            # Старый формат SmartApp API (для обратной совместимости)
            session = data.get("session", {})
            req = data.get("request", {})
            version = data.get("version", "1.0")
            is_new_session = session.get("new", False)
            utterance = extract_utterance_legacy(data, req)
            
            # Логируем команду пользователя (для legacy API нет отдельного user_visible_text)
            if utterance:
                log_user_command(utterance, utterance, user_id)
            
            # Обрабатываем команду (общая логика для Legacy API)
            text, end_session, response_payload = await _process_command(
                binding_service, robot_service, user_id, utterance, None,
                is_new_session, "", data, is_chatapp=False, session=session, version=version
            )
            
            # Логируем ответ бота
            logger.info(f"Ответ: '{text}'")

        return JSONResponse(
            content=response_payload,
            media_type="application/json",
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "SmartApp API is running"}


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@router.post("/robot/command")
async def robot_command(
    request: Request,
    robot_service: RobotService = Depends(get_robot_service)
) -> Dict[str, Any]:
    """
    Endpoint для тестирования команд робота.
    Принимает JSON с полем 'utterance' (текст команды).
    """
    try:
        data = await request.json()
        utterance = data.get("utterance", "")
        
        if not utterance:
            raise HTTPException(status_code=400, detail="Field 'utterance' is required")
        
        result = await robot_service.execute_command(utterance)
        
        return {
            "success": result.success,
            "command": result.command.value,
            "text": result.text,
            "motor_command": result.motor_command,
            "error_message": result.error_message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка в endpoint команды робота: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

