"""
Фабрика зависимостей для навыков (salute, alice).
"""
import logging
from functools import lru_cache

from app.infrastructure.persistence.redis_client import get_shared_redis_client
from app.infrastructure.persistence.redis_user_repository import RedisUserRepository
from app.infrastructure.persistence.redis_binding_repository import RedisBindingRepository
from app.infrastructure.persistence.redis_command_feedback_repository import RedisCommandFeedbackRepository
from app.infrastructure.external.cvc_classifier import CVCCClassifier
from app.infrastructure.external.remote_grpc_robot_connector import RemoteGrpcRobotConnector
from app.application.use_cases.bind_robot import BindRobotUseCase
from app.application.use_cases.unbind_robot import UnbindRobotUseCase
from app.application.use_cases.get_help import GetHelpUseCase
from app.application.use_cases.handle_binding_flow import HandleBindingFlowUseCase
from app.application.use_cases.process_command import ProcessCommandUseCase
from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache
def create_process_command_use_case() -> ProcessCommandUseCase:
    """Создаёт ProcessCommandUseCase с Redis, CVC и remote robot gateway (singleton на worker)."""
    redis_client = get_shared_redis_client(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )
    user_repository = RedisUserRepository(redis_client=redis_client)
    binding_repository = RedisBindingRepository(redis_client=redis_client)
    command_feedback_repository = RedisCommandFeedbackRepository(
        redis_client=redis_client,
        last_command_ttl=settings.LAST_COMMAND_TTL_SECONDS,
    )
    command_classifier = CVCCClassifier(
        settings.CVC_SERVICE_URL,
        timeout=settings.CVC_TIMEOUT,
        health_cache_ttl=settings.CVC_HEALTH_CACHE_TTL,
    )
    robot_connector = RemoteGrpcRobotConnector(binding_repository)

    bind_robot_uc = BindRobotUseCase(binding_repository, user_repository, robot_connector)
    unbind_robot_uc = UnbindRobotUseCase(binding_repository)
    get_help_uc = GetHelpUseCase(user_repository)
    handle_binding_flow_uc = HandleBindingFlowUseCase(
        binding_repository, user_repository, bind_robot_uc
    )

    return ProcessCommandUseCase(
        user_repository=user_repository,
        binding_repository=binding_repository,
        command_classifier=command_classifier,
        robot_connector=robot_connector,
        bind_robot_uc=bind_robot_uc,
        unbind_robot_uc=unbind_robot_uc,
        get_help_uc=get_help_uc,
        handle_binding_flow_uc=handle_binding_flow_uc,
        command_feedback_repository=command_feedback_repository,
    )


@lru_cache
def create_command_feedback_repository() -> RedisCommandFeedbackRepository:
    """Singleton репозитория feedback для admin-роутов."""
    redis_client = get_shared_redis_client(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )
    return RedisCommandFeedbackRepository(
        redis_client=redis_client,
        last_command_ttl=settings.LAST_COMMAND_TTL_SECONDS,
    )


async def shutdown_app_dependencies() -> None:
    """Закрывает долгоживущие клиенты при остановке worker."""
    try:
        use_case = create_process_command_use_case()
        classifier = use_case.command_classifier
        if hasattr(classifier, "aclose"):
            await classifier.aclose()
    except Exception as e:
        logger.warning("Ошибка при shutdown зависимостей: %s", e)
