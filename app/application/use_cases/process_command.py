"""
Use Case для обработки команд пользователя
"""
import logging
import time
from typing import Optional, List, Union

from app.domain.repositories.binding_repository import IBindingRepository
from app.domain.repositories.user_repository import IUserRepository
from app.domain.repositories.command_feedback_repository import ICommandFeedbackRepository
from app.domain.services.command_classifier import ICommandClassifier
from app.domain.services.robot_connector import IRobotConnector
from app.domain.value_objects.user_state import UserState
from app.domain.value_objects.platform import Platform
from app.application.dto.command_request import CommandRequestDTO
from app.application.dto.command_response import CommandResponseDTO
from app.application.use_cases.bind_robot import BindRobotUseCase
from app.application.use_cases.unbind_robot import UnbindRobotUseCase
from app.application.use_cases.get_help import GetHelpUseCase
from app.application.use_cases.handle_binding_flow import HandleBindingFlowUseCase
from app.platforms.responses import build_platform_response

logger = logging.getLogger(__name__)

# Список команд с полной информацией (из robot_service)
COMMANDS = [
    {
        'trigger': 'лапу',
        'function': 'give_paw',
        'description': 'робот поднимет лапу',
        'response_text': "Робот поднимает лапу! 🐾"
    },
    {
        'trigger': 'равняйсь',
        'function': 'stand_at_attention',
        'description': 'робот выровняется по стойке смирно',
        'response_text': "Робот равняется! 🎖️"
    },
    {
        'trigger': 'отставить',
        'function': 'dismiss',
        'description': 'робот встанет',
        'response_text': "Робот встаёт! ✨"
    },
    {
        'trigger': 'вставай',
        'function': 'dismiss',
        'description': 'робот встанет',
        'response_text': "Робот встаёт! ✨"
    },
    {
        'trigger': 'лежать',
        'function': 'lie_down',
        'description': 'робот ляжет',
        'response_text': "Робот ложится! 💤"
    },
    {
        'trigger': ['кувырок', 'вращайся'],
        'function': 'rotate',
        'description': 'робот сделает кувырок',
        'response_text': "Робот делает кувырок! 🤸"
    },
    {
        'trigger': ['бегать', 'пошли'],
        'function': 'run',
        'description': 'робот начнет бегать',
        'response_text': "Робот начинает бегать! 🏃"
    },
    {
        'trigger': 'смирно',
        'function': 'stop_running',
        'description': 'робот остановится',
        'response_text': "Робот останавливается! 🛑"
    },
    {
        'trigger': ['держи джойстик', 'возьми джойстик', 'подключись к джойстику'],
        'function': 'reconnect_joystick',
        'description': 'робот подключится к джойстику',
        'response_text': "Робот подключается к джойстику! 🎮"
    }
]


class ProcessCommandUseCase:
    """Use Case для обработки команд пользователя"""
    
    def __init__(
        self,
        user_repository: IUserRepository,
        binding_repository: IBindingRepository,
        command_classifier: ICommandClassifier,
        robot_connector: IRobotConnector,
        bind_robot_uc: BindRobotUseCase,
        unbind_robot_uc: UnbindRobotUseCase,
        get_help_uc: GetHelpUseCase,
        handle_binding_flow_uc: HandleBindingFlowUseCase,
        command_feedback_repository: ICommandFeedbackRepository,
    ):
        """
        Инициализация use case

        Args:
            user_repository: Репозиторий пользователей
            binding_repository: Репозиторий привязок
            command_classifier: Классификатор команд
            robot_connector: Коннектор для связи с роботом
            bind_robot_uc: Use case для привязки робота
            unbind_robot_uc: Use case для отвязки робота
            get_help_uc: Use case для получения справки
            handle_binding_flow_uc: Use case для обработки потока привязки
            command_feedback_repository: Репозиторий обратной связи по командам
        """
        self.user_repository = user_repository
        self.binding_repository = binding_repository
        self.command_classifier = command_classifier
        self.robot_connector = robot_connector
        self.bind_robot_uc = bind_robot_uc
        self.unbind_robot_uc = unbind_robot_uc
        self.get_help_uc = get_help_uc
        self.handle_binding_flow_uc = handle_binding_flow_uc
        self.command_feedback_repository = command_feedback_repository
    
    async def execute(self, request: CommandRequestDTO) -> CommandResponseDTO:
        """
        Обрабатывает команду пользователя
        
        Args:
            request: Запрос на обработку команды
            
        Returns:
            Ответ с текстом и метаданными
        """
        finished = False
        text_or_messages: Union[str, List[str]] = ""
        
        # Определяем состояния пользователя заранее, чтобы использовать их при формировании ответа
        has_binding_state = False
        has_help_state = False
        has_command_detail_state = False
        
        if request.user_id:
            has_binding_state = self.user_repository.has_user_state(request.user_id, UserState.WAITING_CODE)
            has_help_state = self.user_repository.has_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
            has_command_detail_state = self.user_repository.has_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
        
        if request.is_new_session or (
            request.platform.is_salute_chatapp
            and request.intent == "run_app"
            and not request.utterance
        ):
            if request.user_id and self.binding_repository.has_binding(request.user_id):
                robot_id = self.binding_repository.get_robot_id(request.user_id)
                if robot_id:
                    robot_id_str = robot_id.value
                    connected = (
                        self.robot_connector.is_robot_connected(robot_id_str)
                        if hasattr(self.robot_connector, "is_robot_connected")
                        else False
                    )
                    if connected:
                        text_or_messages = f"Привет! Ваш робот {robot_id_str} готов к управлению."
                    else:
                        text_or_messages = (
                            f"Робот {robot_id_str} привязан, но не подключен. "
                            "Проверьте подключение робота."
                        )
                else:
                    text_or_messages = "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'."
            else:
                text_or_messages = "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'."
        elif request.utterance:
            # Если в режиме привязки (waiting_code) - обрабатываем с поддержкой помощи
            if has_binding_state:
                text_or_messages, finished = await self._handle_binding_mode(
                    request, has_help_state, has_command_detail_state
                )
            else:
                # Не в режиме привязки
                text_or_messages, finished = await self._handle_normal_mode(
                    request, has_help_state, has_command_detail_state
                )
        else:
            if request.platform.is_salute or request.platform == Platform.ALICE:
                if request.user_id and self.binding_repository.has_binding(request.user_id):
                    text_or_messages = "Скажите команду для робота. Для списка команд - 'помощь'."
                else:
                    text_or_messages = "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'."
            else:
                text_or_messages = "Не понял команду."

        text, response_payload = build_platform_response(
            request,
            text_or_messages,
            finished,
            has_binding_state=has_binding_state,
            has_help_state=has_help_state,
            has_command_detail_state=has_command_detail_state,
        )

        return CommandResponseDTO(
            text=text,
            finished=finished,
            response_payload=response_payload,
        )
    
    async def _handle_binding_mode(
        self,
        request: CommandRequestDTO,
        has_help_state: bool,
        has_command_detail_state: bool
    ) -> tuple[Union[str, List[str]], bool]:
        """Обрабатывает команду в режиме привязки"""
        if not request.user_id:
            return "Не удалось определить пользователя.", False
        utterance_lower = request.utterance.lower().strip()

        if has_help_state:
            help_section_response = self._handle_help_section_choice(request, utterance_lower)
            if help_section_response is not None:
                return help_section_response
            # Не выбор раздела - обрабатываем через handle_binding_flow
            binding_text, binding_finished = await self.handle_binding_flow_uc.process(
                request.user_id, request.utterance, request.message
            )
            if binding_text is not None:
                # Возвращаем как есть (может быть список или строка)
                return binding_text, binding_finished
            return "Введите код привязки или скажите 'отмена'.", False
        
        elif has_command_detail_state:
            # Обработка выбора команды для описания
            command_name = self._extract_command_name(utterance_lower)
            description = self.get_help_uc.get_command_description(command_name)
            if description:
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
                return description, False
            else:
                # Не удалось найти команду - обрабатываем через handle_binding_flow
                binding_text, binding_finished = await self.handle_binding_flow_uc.process(
                    request.user_id, request.utterance, request.message
                )
                if binding_text is not None:
                    # Возвращаем как есть (может быть список или строка)
                    return binding_text, binding_finished
                else:
                    if request.user_id:
                        self.user_repository.remove_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
                    return "Введите код привязки или скажите 'отмена'.", False
        
        else:
            # Проверяем, не запросил ли пользователь помощь (локально или через CVC)
            from app.utils.request_parser import detect_local_service_command

            function_name = detect_local_service_command(request.utterance)
            if not function_name:
                classification_result = await self._classify_command(request.utterance)
                function_name = classification_result.get("function") if classification_result else None
            
            if function_name == "help" and "служебн" not in utterance_lower and "исполняем" not in utterance_lower:
                # Пользователь запросил помощь в режиме привязки
                if request.user_id:
                    self.user_repository.add_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
                return self.get_help_uc.get_help_menu(), False
            else:
                # Обрабатываем через handle_binding_flow
                binding_text, binding_finished = await self.handle_binding_flow_uc.process(
                    request.user_id, request.utterance, request.message
                )
                if binding_text is not None:
                    # Возвращаем как есть (может быть список или строка)
                    return binding_text, binding_finished
                else:
                    return "Введите код привязки или скажите 'отмена'.", False
    
    def _handle_help_section_choice(
        self, request: CommandRequestDTO, utterance_lower: str
    ) -> Optional[tuple[Union[str, List[str]], bool]]:
        from app.utils.request_parser import detect_help_section_choice

        section = detect_help_section_choice(utterance_lower)
        if section == "service":
            text = self.get_help_uc.get_service_commands_help(request.platform)
            if request.user_id:
                self.user_repository.remove_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
            return text, False
        if section == "executable":
            text = self.get_help_uc.get_robot_commands_help(request.user_id)
            if request.user_id:
                self.user_repository.remove_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
            return text, False
        return None

    async def _handle_normal_mode(
        self,
        request: CommandRequestDTO,
        has_help_state: bool,
        has_command_detail_state: bool
    ) -> tuple[Union[str, List[str]], bool]:
        """Обрабатывает команду в обычном режиме"""
        utterance_lower = request.utterance.lower().strip()
        
        # Проверяем команду отмены вне режима привязки
        if any(word in utterance_lower for word in ["отмена", "отменить", "отменить привязку"]):
            return "Нет активной операции для отмены.", False

        help_section_response = self._handle_help_section_choice(request, utterance_lower)
        if help_section_response is not None:
            return help_section_response
        
        if has_help_state:
            # Не выбор раздела — очищаем состояние и обрабатываем как обычную команду
            if request.user_id:
                self.user_repository.remove_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
            has_help_state = False
        
        elif has_command_detail_state:
            # Обработка выбора команды для описания
            command_name = self._extract_command_name(utterance_lower)
            description = self.get_help_uc.get_command_description(command_name)
            if description:
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
                return description, False
            else:
                # Не удалось найти команду - очищаем состояние и обрабатываем как обычную команду
                if request.user_id:
                    self.user_repository.remove_user_state(request.user_id, UserState.WAITING_COMMAND_DETAIL)
                has_command_detail_state = False
        
        # Обрабатываем команду (если не было выбора раздела помощи и не было выбора команды)
        if not has_help_state and not has_command_detail_state:
            return await self._process_normal_command(request)
        
        return "Не понял команду.", False
    
    async def _process_normal_command(self, request: CommandRequestDTO) -> tuple[str, bool]:
        """Обрабатывает обычную команду (не привязка, не помощь)"""
        from app.utils.request_parser import detect_local_service_command

        # Служебные команды распознаём локально — CVC нужен только для команд роботу
        local_function = detect_local_service_command(request.utterance)
        if local_function:
            classification_result = {"function": local_function}
        else:
            classification_result = await self._classify_command(request.utterance)
        
        if not classification_result:
            if not await self.command_classifier.is_available():
                return "Извините, сервис классификации команд временно недоступен. Пожалуйста, попробуйте позже.", False
            return "Скажите 'помощь' для списка команд.", False
        
        function_name = classification_result.get("function")
        utterance_lower = request.utterance.lower().strip()
        
        # Обрабатываем служебные команды
        if function_name == "help":
            if "служебн" not in utterance_lower and "исполняем" not in utterance_lower:
                if request.user_id:
                    self.user_repository.add_user_state(request.user_id, UserState.WAITING_HELP_SECTION)
                return self.get_help_uc.get_help_menu(), False
        
        if function_name == "silence":
            # Salute: finished=False + auto_listening=False в build_salute_response.
            # Alice: только end_session; пауза без выхода из навыка недоступна в API.
            return "Хорошо, помолчим. 🐼👋", False
        
        # Обрабатываем команды привязки/отвязки
        if function_name == "bind":
            if not request.user_id:
                return "Не удалось выполнить привязку. Нет данных пользователя.", False
            from app.utils.request_parser import extract_robot_id_from_bind_command
            robot_id_str = extract_robot_id_from_bind_command(request.utterance)
            if robot_id_str:
                success, message = await self.bind_robot_uc.start_binding(request.user_id, robot_id_str)
                return message, False
            else:
                return "Укажите номер робота.", False

        if function_name == "unbind":
            if not request.user_id:
                return "У вас нет привязанного робота.", False
            success, message = await self.unbind_robot_uc.execute(request.user_id)
            return message, False

        # Команда «исправить команду» — запись жалобы по последней выполненной команде
        if function_name == "report_command":
            if not request.user_id:
                return "Не удалось записать. Нет данных пользователя.", False
            if not self.binding_repository.has_binding(request.user_id):
                return "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'.", False
            robot_id = self.binding_repository.get_robot_id(request.user_id)
            if not robot_id:
                return "Привяжите робота.", False
            last = self.command_feedback_repository.get_last_command(request.user_id)
            if not last:
                return "Не найдена последняя команда. Выполните команду роботу и сразу скажите «исправить команду».", False
            last_utterance, last_function = last
            meta = None
            if request.data:
                meta = {}
                if request.data.get("payload", {}).get("session_id"):
                    meta["session_id"] = request.data["payload"]["session_id"]
            self.command_feedback_repository.add_feedback(
                user_id=request.user_id,
                robot_id=robot_id.value,
                user_utterance=last_utterance,
                classified_function=last_function,
                created_at=time.time(),
                meta=meta,
            )
            self.command_feedback_repository.clear_last_command(request.user_id)
            return "Спасибо, мы записали, что команда сработала неправильно. Разработчики посмотрят.", False

        # Обрабатываем команды для робота
        if request.user_id and self.binding_repository.has_binding(request.user_id):
            if function_name and function_name not in ["help", "silence", "bind", "unbind", "report_command"]:
                # Отправляем команду роботу
                success, message = self.robot_connector.send_command(request.user_id, function_name)
                if success:
                    if request.user_id:
                        self.command_feedback_repository.set_last_command(
                            request.user_id, request.utterance, function_name
                        )
                    # Используем текст ответа из COMMANDS
                    for cmd in COMMANDS:
                        if cmd['function'] == function_name:
                            return cmd['response_text'], False
                    return f"Команда '{function_name}' отправлена роботу.", False
                else:
                    return message, False
            else:
                return "Скажите 'помощь' для списка команд.", False
        else:
            return "Привяжите робота. Скажите 'привяжи робота 1' или 'привяжи панду 2'.", False
    
    async def _classify_command(self, utterance: str) -> Optional[dict]:
        """
        Классифицирует команду через классификатор
        
        Returns:
            Словарь с результатами классификации или None
        """
        utterance_lower = utterance.lower().strip()
        
        if not await self.command_classifier.is_available():
            logger.error(f"CVC сервис недоступен, невозможно классифицировать команду: '{utterance_lower}'")
            return None
        
        try:
            result = await self.command_classifier.classify(utterance_lower)
            if result and result.get("function"):
                function = result.get("function")
                confidence = result.get("confidence", 0.0)
                
                # Обрабатываем служебные команды
                if function == "help":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> 'help' (уверенность: {confidence:.3f})")
                    return {"function": "help"}
                
                if function == "silence":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> 'silence' (уверенность: {confidence:.3f})")
                    return {"function": "silence"}

                if function == "report_command":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> 'report_command' (уверенность: {confidence:.3f})")
                    return {"function": "report_command"}

                # Команды привязки возвращаем как function_name
                if function in ["bind", "unbind", "cancel"]:
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> '{function}' (уверенность: {confidence:.3f})")
                    return {"function": function}
                
                # Игнорируем "unknown" команды от CVC
                if function != "unknown":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> '{function}' (уверенность: {confidence:.3f})")
                    return {"function": function}
                else:
                    logger.warning(f"CVC классифицировал '{utterance_lower}' как 'unknown'")
                    return None
            else:
                logger.warning(f"CVC вернул пустой результат для '{utterance_lower}': {result}")
                return None
        except Exception as e:
            logger.error(f"Ошибка классификации CVC для '{utterance_lower}': {e}")
            return None
    
    def _extract_command_name(self, utterance_lower: str) -> str:
        """Извлекает название команды из utterance"""
        command_name = utterance_lower
        
        # Убираем префиксы типа "расскажи про", "про команду" и т.д.
        for prefix in ["расскажи про", "про команду", "про", "команда", "команду"]:
            if utterance_lower.startswith(prefix):
                command_name = utterance_lower[len(prefix):].strip()
                command_name = command_name.strip('"\'')
                break
        
        # Убираем кавычки если они есть
        command_name = command_name.strip('"\'')
        return command_name
