"""
Сервис управления роботом-пандой.
Обрабатывает голосовые команды и отправляет их на моторы робота.
"""
import logging
from typing import Dict, Any, Optional

from app.models.commands import RobotCommand, CommandResult
from app.config import CVC_SERVICE_URL
from app.services.cvc_client import CVCClient

logger = logging.getLogger(__name__)

# Список команд с полной информацией
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


class RobotService:
    """Сервис для управления роботом-пандой"""
    
    def __init__(self, robot_api_url: Optional[str] = None, cvc_service_url: Optional[str] = None):
        """
        Инициализация сервиса робота
        
        Args:
            robot_api_url: URL API робота для отправки команд (опционально, не используется с gRPC)
            cvc_service_url: URL CVC сервиса для классификации команд (по умолчанию из конфига)
        """
        self.robot_api_url = robot_api_url
        cvc_url = cvc_service_url or CVC_SERVICE_URL
        self.cvc_client = CVCClient(base_url=cvc_url)
        self._cvc_available = None  # Кэш для проверки доступности
        logger.info(f"RobotService инициализирован. Robot API URL: {robot_api_url or 'Не настроен (используется gRPC)'}, CVC URL: {cvc_url}")
    
    def _is_cvc_available(self) -> bool:
        """
        Проверяет доступность CVC сервиса (с кэшированием).
        
        Returns:
            True если CVC доступен, False иначе
        """
        if self._cvc_available is None:
            self._cvc_available = self.cvc_client.is_available()
            if self._cvc_available:
                logger.info("CVC сервис доступен, будет использоваться для классификации команд")
            else:
                logger.warning("CVC сервис недоступен - система будет сообщать об ошибках подключения")
        return self._cvc_available
    
    def parse_command(self, utterance: str) -> tuple[Optional[str], RobotCommand]:
        """
        Распознает команду из текста пользователя через CVC сервис.
        Сначала обращается к CVC классификатору, затем обрабатывает служебные команды.
        Если CVC недоступен, возвращает ошибку.
        
        Args:
            utterance: Текст команды пользователя
            
        Returns:
            tuple: (function_name или None, RobotCommand)
                   function_name - имя функции для отправки роботу (например, "dismiss")
                   RobotCommand - тип команды для внутренней обработки
        """
        utterance_lower = utterance.lower().strip()
        
        # Проверяем доступность CVC сервиса
        if not self._is_cvc_available():
            logger.error(f"CVC сервис недоступен, невозможно классифицировать команду: '{utterance_lower}'")
            return None, RobotCommand.ERROR
        
        # Используем CVC сервис для классификации (передаем полный текст, CVC сам обработает префиксы)
        try:
            result = self.cvc_client.predict(utterance_lower, return_confidence=True)
            if result and result.get("command"):
                command = result.get("command")
                confidence = result.get("confidence", 0.0)
                
                # Обрабатываем служебные команды, которые возвращает CVC
                if command == "help":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> 'help' (уверенность: {confidence:.3f})")
                    return None, RobotCommand.HELP
                
                if command == "silence":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> 'silence' (уверенность: {confidence:.3f})")
                    return None, RobotCommand.SILENCE
                
                # Команды привязки (bind, unbind, cancel) возвращаем как function_name для обработки в routes.py
                if command in ["bind", "unbind", "cancel"]:
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> '{command}' (уверенность: {confidence:.3f})")
                    return command, RobotCommand.UNKNOWN
                
                # Игнорируем "unknown" команды от CVC
                if command != "unknown":
                    logger.info(f"CVC классифицировал '{utterance_lower}' -> '{command}' (уверенность: {confidence:.3f})")
                    return command, RobotCommand.UNKNOWN
                else:
                    logger.warning(f"CVC классифицировал '{utterance_lower}' как 'unknown'")
                    return None, RobotCommand.UNKNOWN
            else:
                logger.warning(f"CVC вернул пустой результат для '{utterance_lower}': {result}")
                return None, RobotCommand.ERROR
        except Exception as e:
            logger.error(f"Ошибка классификации CVC для '{utterance_lower}': {e}")
            return None, RobotCommand.ERROR
    
    def process_command(self, utterance: str) -> CommandResult:
        """
        Обрабатывает команду пользователя
        
        Args:
            utterance: Текст команды пользователя
            
        Returns:
            CommandResult: Результат обработки команды
        """
        function_name, command_type = self.parse_command(utterance)
        
        # Определяем текст ответа пользователю
        utterance_lower = utterance.lower().strip()
        
        if command_type == RobotCommand.HELP:
            # Проверяем, выбран ли конкретный раздел в том же запросе (например, "помощь служебные")
            if "служебн" in utterance_lower:
                text = self._get_service_commands_help()
            elif "исполняем" in utterance_lower:
                text = self._get_robot_commands_help()
            else:
                # Показываем выбор разделов
                text = "Выберите раздел: 'служебные' или 'исполняемые'."
        elif not function_name and command_type == RobotCommand.UNKNOWN:
            text = "Скажите 'помощь' для списка команд."
        elif command_type == RobotCommand.SILENCE:
            text = "Хорошо, помолчим. 🐼👋"
        elif command_type == RobotCommand.ERROR:
            text = "Извините, сервис классификации команд временно недоступен. Пожалуйста, попробуйте позже."
        elif function_name:
            # Команда распознана - определяем ответ пользователю по function
            for cmd in COMMANDS:
                if cmd['function'] == function_name:
                    text = cmd['response_text']
                    break
            else:
                text = f"Команда '{function_name}' отправлена роботу."
        
        # Генерируем команду для отправки роботу (function на английском)
        command_text = function_name if function_name else None
        
        return CommandResult(
            command=command_type,
            text=text,
            motor_command={"function": command_text} if command_text else None,
            success=function_name is not None or command_type in (RobotCommand.HELP, RobotCommand.SILENCE),
            finished=(command_type == RobotCommand.SILENCE),
            error_message=text if command_type == RobotCommand.ERROR else None
        )
    
    def _get_service_commands_help(self) -> str:
        """Возвращает список служебных команд"""
        help_lines = ["Служебные команды:"]
        help_lines.extend([
            "'Привяжи робота 1' или 'Привяжи панду 2' - привязать робота;",
            "'Отвяжи робота' - отвязать робота;",
            "'Молчи' - временно остановить общение."
        ])
        return "\n".join(help_lines)
    
    def _get_robot_commands_help(self) -> str:
        """Возвращает список команд управления роботом (только названия)"""
        help_lines = ["Команды управления роботом:"]
        for cmd in COMMANDS:
            triggers = cmd['trigger'] if isinstance(cmd['trigger'], list) else [cmd['trigger']]
            # Показываем только первый вариант
            help_lines.append(f"• '{triggers[0]}'")
        
        help_lines.append("\nДля подробного описания скажите 'расскажи про \"название команды\"'.")
        return "\n".join(help_lines)
    
    def _get_command_description(self, command_name: str) -> Optional[str]:
        """
        Возвращает подробное описание команды по названию
        
        Args:
            command_name: Название команды (триггер)
        
        Returns:
            Описание команды или None если команда не найдена
        """
        command_name_lower = command_name.lower().strip()
        
        # Ищем команду по триггеру
        for cmd in COMMANDS:
            triggers = cmd['trigger'] if isinstance(cmd['trigger'], list) else [cmd['trigger']]
            # Проверяем все варианты триггеров
            for trigger in triggers:
                if trigger.lower() == command_name_lower:
                    description = cmd.get('description', '')
                    if description:
                        return f"Команда '{trigger}':\n{description.capitalize()}."
                    else:
                        return f"Команда '{trigger}'"
        
        return None