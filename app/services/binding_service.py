"""
Сервис управления привязками пользователей к роботам
Использует Redis для хранения данных
"""
import os
import logging
import time
from typing import Optional, Dict, Any, Set
import redis

logger = logging.getLogger(__name__)

CODE_EXPIRY_SECONDS = 300  # 5 минут

# Префиксы для ключей Redis
BINDINGS_PREFIX = "bindings:"
STATES_PREFIX = "binding_states:"  # Старый префикс, будет удален после миграции
HELP_STATES_PREFIX = "help_states:"  # Старый префикс, будет удален после миграции
USER_STATES_PREFIX = "user_states:"  # Новый единый префикс для состояний
BINDING_DATA_PREFIX = "binding_data:"  # Префикс для данных привязки


class BindingService:
    """Управление привязками пользователей к роботам через Redis"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Инициализация сервиса привязок
        
        Args:
            redis_url: URL подключения к Redis (по умолчанию из переменной окружения)
        """
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Проверяем подключение
            self.redis_client.ping()
            logger.info(f"BindingService инициализирован (Redis: {redis_url})")
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            raise
    
    def get_user_states(self, user_id: str) -> Set[str]:
        """
        Получает все активные состояния пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Множество активных состояний (например, {"waiting_code", "waiting_help_section"})
        """
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            if not self.redis_client.exists(key):
                return set()
            states = self.redis_client.smembers(key)
            return set(states) if states else set()
        except Exception as e:
            logger.error(f"Ошибка получения состояний для user_id={user_id}: {e}")
            return set()
    
    def has_user_state(self, user_id: str, state: str) -> bool:
        """
        Проверяет наличие конкретного состояния у пользователя
        
        Args:
            user_id: ID пользователя
            state: Название состояния (например, "waiting_code", "waiting_help_section")
        
        Returns:
            True если состояние активно, False иначе
        """
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            if not self.redis_client.exists(key):
                return False
            return self.redis_client.sismember(key, state)
        except Exception as e:
            logger.error(f"Ошибка проверки состояния {state} для user_id={user_id}: {e}")
            return False
    
    def add_user_state(self, user_id: str, state: str, ttl: int = CODE_EXPIRY_SECONDS) -> bool:
        """
        Добавляет состояние пользователю
        
        Args:
            user_id: ID пользователя
            state: Название состояния (например, "waiting_code", "waiting_help_section")
            ttl: Время жизни в секундах (по умолчанию 5 минут)
        
        Returns:
            True если успешно
        """
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            self.redis_client.sadd(key, state)
            # Устанавливаем TTL (если ключ уже существовал, TTL обновится)
            self.redis_client.expire(key, ttl)
            logger.debug(f"Added state '{state}' for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления состояния {state} для user_id={user_id}: {e}")
            return False
    
    def remove_user_state(self, user_id: str, state: str) -> bool:
        """
        Удаляет состояние у пользователя
        
        Args:
            user_id: ID пользователя
            state: Название состояния для удаления
        
        Returns:
            True если успешно
        """
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            removed = self.redis_client.srem(key, state)
            if removed > 0:
                logger.debug(f"Removed state '{state}' for user {user_id}")
                # Если Set пуст, удаляем ключ
                if self.redis_client.scard(key) == 0:
                    self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления состояния {state} для user_id={user_id}: {e}")
            return False
    
    def clear_user_states(self, user_id: str) -> bool:
        """
        Очищает все состояния пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            True если успешно
        """
        try:
            key = f"{USER_STATES_PREFIX}{user_id}"
            deleted = self.redis_client.delete(key)
            if deleted > 0:
                logger.debug(f"Cleared all states for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки состояний для user_id={user_id}: {e}")
            return False
    
    def get_user_id(self, uuid_data: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает идентификатор пользователя из uuid
        
        Args:
            uuid_data: Объект uuid из запроса SmartApp API
            
        Returns:
            Идентификатор пользователя (sub или userId)
        """
        # Используем sub как основной идентификатор (более стабильный)
        user_id = uuid_data.get("sub") or uuid_data.get("userId")
        return user_id
    
    def has_binding(self, user_id: str) -> bool:
        """Проверяет, есть ли постоянная привязка для пользователя"""
        try:
            key = f"{BINDINGS_PREFIX}{user_id}"
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Ошибка проверки привязки для user_id={user_id}: {e}")
            return False
    
    def get_robot_id(self, user_id: str) -> Optional[str]:
        """Получает ID привязанного робота для пользователя"""
        try:
            key = f"{BINDINGS_PREFIX}{user_id}"
            robot_id = self.redis_client.get(key)
            return robot_id if robot_id else None
        except Exception as e:
            logger.error(f"Ошибка получения robot_id для user_id={user_id}: {e}")
            return None
    
    def get_binding_state(self, user_id: str) -> Optional[str]:
        """
        Получает текущее состояние процесса привязки (для обратной совместимости)
        
        ВАЖНО: Используйте has_user_state(user_id, "waiting_code") вместо этого метода
        """
        # Проверяем новую систему состояний
        if self.has_user_state(user_id, "waiting_code"):
            # Проверяем, не истек ли код
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            if self.redis_client.exists(binding_data_key):
                expires_at_str = self.redis_client.hget(binding_data_key, "expires_at")
                if expires_at_str:
                    expires_at = float(expires_at_str)
                    if time.time() > expires_at:
                        logger.info(f"Binding code expired for user {user_id}")
                        self.cancel_binding(user_id)
                        return None
                    return "waiting_code"
        
        # Проверяем старую систему для обратной совместимости
        try:
            old_key = f"{STATES_PREFIX}{user_id}"
            if not self.redis_client.exists(old_key):
                return None
            
            expires_at_str = self.redis_client.hget(old_key, "expires_at")
            if not expires_at_str:
                return None
            
            expires_at = float(expires_at_str)
            if time.time() > expires_at:
                self.cancel_binding(user_id)
                return None
            
            return "waiting_code"
        except Exception as e:
            logger.error(f"Ошибка получения состояния привязки для user_id={user_id}: {e}")
            return None
    
    def start_binding(self, user_id: str, robot_id: str, code: str, expires_at: float) -> bool:
        """Начинает процесс привязки - сохраняет состояние ожидания кода"""
        if not user_id or not robot_id or not code:
            logger.error("User ID, robot ID and code are required for binding")
            return False
        
        # Приводим код к строке и убираем пробелы
        code_str = str(code).strip()
        logger.debug(f"Сохранение кода привязки: '{code_str}' (type: {type(code_str).__name__})")
        
        try:
            # Удаляем старое состояние привязки, если есть (старая система)
            old_state_key = f"{STATES_PREFIX}{user_id}"
            self.redis_client.delete(old_state_key)
            
            # Удаляем старые данные привязки, если есть
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            self.redis_client.delete(binding_data_key)
            
            # Сохраняем данные привязки в Hash
            self.redis_client.hset(binding_data_key, mapping={
                "robot_id": robot_id,
                "code": code_str,
                "expires_at": str(expires_at),
                "attempts": "0"
            })
            
            # Добавляем состояние "waiting_code" в единую систему состояний
            ttl = max(1, int(expires_at - time.time()))
            self.add_user_state(user_id, "waiting_code", ttl)
            
            # Устанавливаем TTL для данных привязки (синхронизирован с состояниями)
            self.redis_client.expire(binding_data_key, ttl)
            
            logger.info(f"Started binding process for user {user_id} to robot {robot_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка начала привязки для user_id={user_id}, robot_id={robot_id}: {e}")
            return False
    
    def get_binding_code(self, user_id: str) -> tuple[Optional[str], Optional[float]]:
        """
        Получает код и expires_at из состояния привязки
        
        Returns:
            tuple: (code, expires_at) или (None, None) если состояние не найдено или истекло
        """
        try:
            # Проверяем новую систему
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            if self.redis_client.exists(binding_data_key):
                state_data = self.redis_client.hgetall(binding_data_key)
                if state_data:
                    expires_at_str = state_data.get("expires_at")
                    if expires_at_str:
                        expires_at = float(expires_at_str)
                        if time.time() > expires_at:
                            self.cancel_binding(user_id)
                            return None, None
                        code = state_data.get("code")
                        return code, expires_at
            
            # Проверяем старую систему для обратной совместимости
            old_key = f"{STATES_PREFIX}{user_id}"
            if self.redis_client.exists(old_key):
                state_data = self.redis_client.hgetall(old_key)
                if state_data:
                    expires_at_str = state_data.get("expires_at")
                    if expires_at_str:
                        expires_at = float(expires_at_str)
                        if time.time() > expires_at:
                            self.cancel_binding(user_id)
                            return None, None
                        code = state_data.get("code")
                        return code, expires_at
            
            return None, None
        except Exception as e:
            logger.error(f"Ошибка получения кода привязки для user_id={user_id}: {e}")
            return None, None
    
    def verify_binding_code(self, user_id: str, code: str) -> tuple[bool, str]:
        """Проверяет код верификации"""
        try:
            # Используем новую систему
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            if not self.redis_client.exists(binding_data_key):
                # Проверяем старую систему для обратной совместимости
                old_key = f"{STATES_PREFIX}{user_id}"
                if not self.redis_client.exists(old_key):
                    return False, "Процесс привязки не начат"
                key = old_key
            else:
                key = binding_data_key
            
            # Получаем данные из Hash
            state_data = self.redis_client.hgetall(key)
            if not state_data:
                return False, "Процесс привязки не начат"
            
            # Проверяем истечение времени
            expires_at_str = state_data.get("expires_at")
            if not expires_at_str:
                return False, "Процесс привязки не начат"
            
            expires_at = float(expires_at_str)
            if time.time() > expires_at:
                self.cancel_binding(user_id)
                return False, "Код истек. Начните привязку заново."
            
            # Проверяем код
            code_str = str(code).strip()
            stored_code_str = str(state_data.get("code", "")).strip()
            logger.debug(f"Проверка кода: введённый='{code_str}' (type: {type(code_str).__name__}), сохранённый='{stored_code_str}' (type: {type(stored_code_str).__name__})")
            
            if code_str != stored_code_str:
                # Увеличиваем счетчик попыток
                attempts = int(state_data.get("attempts", "0")) + 1
                self.redis_client.hset(key, "attempts", str(attempts))
                
                if attempts >= 3:
                    self.cancel_binding(user_id)
                    return False, "Превышено количество попыток. Начните привязку заново."
                else:
                    remaining = 3 - attempts
                    return False, f"Неверный код. Осталось попыток: {remaining}"
            
            # Код верный
            return True, "Код подтвержден"
        except Exception as e:
            logger.error(f"Ошибка проверки кода для user_id={user_id}: {e}")
            return False, "Ошибка проверки кода"
    
    def complete_binding(self, user_id: str) -> bool:
        """Завершает привязку - сохраняет постоянную привязку"""
        try:
            binding_key = f"{BINDINGS_PREFIX}{user_id}"
            
            # Пробуем получить данные из новой системы
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            state_data = None
            if self.redis_client.exists(binding_data_key):
                state_data = self.redis_client.hgetall(binding_data_key)
            
            # Если не нашли в новой системе, проверяем старую
            if not state_data:
                old_state_key = f"{STATES_PREFIX}{user_id}"
                if self.redis_client.exists(old_state_key):
                    state_data = self.redis_client.hgetall(old_state_key)
            
            if not state_data:
                logger.error(f"No binding state found for user {user_id}")
                return False
            
            robot_id = state_data.get("robot_id")
            if not robot_id:
                logger.error(f"No robot_id in binding state for user {user_id}")
                return False
            
            # Сохраняем постоянную привязку (просто строка robot_id)
            self.redis_client.set(binding_key, robot_id)
            
            # Удаляем временное состояние из новой системы
            self.remove_user_state(user_id, "waiting_code")
            self.redis_client.delete(binding_data_key)
            
            # Удаляем из старой системы
            old_state_key = f"{STATES_PREFIX}{user_id}"
            self.redis_client.delete(old_state_key)
            
            logger.info(f"Completed binding: user {user_id} -> robot {robot_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка завершения привязки для user_id={user_id}: {e}")
            return False
    
    def cancel_binding(self, user_id: str) -> bool:
        """Отменяет процесс привязки"""
        try:
            # Удаляем состояние из новой системы
            self.remove_user_state(user_id, "waiting_code")
            
            # Удаляем данные привязки
            binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
            self.redis_client.delete(binding_data_key)
            
            # Удаляем из старой системы (для обратной совместимости)
            old_key = f"{STATES_PREFIX}{user_id}"
            deleted = self.redis_client.delete(old_key)
            
            if deleted > 0 or self.redis_client.exists(binding_data_key) == 0:
                logger.info(f"Cancelled binding for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка отмены привязки для user_id={user_id}: {e}")
            return False
    
    def unbind_robot(self, user_id: str) -> bool:
        """Отвязывает робота от пользователя"""
        try:
            key = f"{BINDINGS_PREFIX}{user_id}"
            deleted = self.redis_client.delete(key)
            if deleted > 0:
                logger.info(f"Unbound robot from user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка отвязки робота для user_id={user_id}: {e}")
            return False
    
    def get_binding_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о состоянии привязки для пользователя"""
        try:
            # Проверяем постоянную привязку
            binding_key = f"{BINDINGS_PREFIX}{user_id}"
            robot_id = self.redis_client.get(binding_key)
            
            if robot_id:
                return {
                    "has_binding": True,
                    "robot_id": robot_id,
                    "state": "completed"
                }
            
            # Проверяем временное состояние (новая система)
            if self.has_user_state(user_id, "waiting_code"):
                binding_data_key = f"{BINDING_DATA_PREFIX}{user_id}"
                if self.redis_client.exists(binding_data_key):
                    state_data = self.redis_client.hgetall(binding_data_key)
                    if state_data:
                        # Проверяем, не истек ли код
                        expires_at_str = state_data.get("expires_at")
                        if expires_at_str:
                            expires_at = float(expires_at_str)
                            if time.time() > expires_at:
                                self.cancel_binding(user_id)
                                return {
                                    "has_binding": False,
                                    "state": None
                                }
                            return {
                                "has_binding": False,
                                "robot_id": state_data.get("robot_id"),
                                "state": "waiting_code",
                                "attempts": int(state_data.get("attempts", "0"))
                            }
            
            # Проверяем старую систему для обратной совместимости
            old_state_key = f"{STATES_PREFIX}{user_id}"
            if self.redis_client.exists(old_state_key):
                state_data = self.redis_client.hgetall(old_state_key)
                if state_data:
                    # Проверяем, не истек ли код
                    expires_at_str = state_data.get("expires_at")
                    if expires_at_str:
                        expires_at = float(expires_at_str)
                        if time.time() > expires_at:
                            self.cancel_binding(user_id)
                            return {
                                "has_binding": False,
                                "state": None
                            }
                        return {
                            "has_binding": False,
                            "robot_id": state_data.get("robot_id"),
                            "state": "waiting_code",
                            "attempts": int(state_data.get("attempts", "0"))
                        }
            
            return {
                "has_binding": False,
                "state": None
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о привязке для user_id={user_id}: {e}")
            return {
                "has_binding": False,
                "state": None
            }
    