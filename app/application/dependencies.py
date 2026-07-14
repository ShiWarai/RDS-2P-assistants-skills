"""
Фабрика зависимостей для навыков (salute, alice).
"""
import logging

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


def create_process_command_use_case() -> ProcessCommandUseCase:
    """Создаёт ProcessCommandUseCase с Redis, CVC и remote robot gateway."""
    user_repository = RedisUserRepository(settings.REDIS_URL)
    binding_repository = RedisBindingRepository(settings.REDIS_URL)
    command_feedback_repository = RedisCommandFeedbackRepository(
        settings.REDIS_URL,
        last_command_ttl=settings.LAST_COMMAND_TTL_SECONDS,
    )
    command_classifier = CVCCClassifier(settings.CVC_SERVICE_URL, settings.CVC_TIMEOUT)
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
