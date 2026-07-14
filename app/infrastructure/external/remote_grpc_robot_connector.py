"""
Реализация IRobotConnector через SkillBridgeService (robot-gateway).
"""
import logging
from typing import Tuple, Optional

import grpc

try:
    from grpc_proto import robot_pb2
    from grpc_proto import robot_pb2_grpc
except ImportError:
    robot_pb2 = None
    robot_pb2_grpc = None

from app.domain.services.robot_connector import IRobotConnector
from app.domain.value_objects.robot_id import RobotId
from app.domain.value_objects.binding_code import BindingCode
from app.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class RemoteGrpcRobotConnector(IRobotConnector):
    """Клиент к внутрикластерному robot-gateway."""

    def __init__(self, binding_repository):
        self.binding_repository = binding_repository
        self._channel = None
        self._stub = None
        logger.info("RemoteGrpcRobotConnector инициализирован (gateway=%s)", settings.ROBOT_GATEWAY_URL)

    def _get_stub(self):
        if robot_pb2_grpc is None:
            return None
        if self._stub is None:
            self._channel = grpc.insecure_channel(settings.ROBOT_GATEWAY_URL)
            self._stub = robot_pb2_grpc.SkillBridgeServiceStub(self._channel)
        return self._stub

    def send_command(self, user_id: str, function_name: str) -> Tuple[bool, str]:
        stub = self._get_stub()
        if stub is None:
            return False, "gRPC протобуфы не загружены"

        robot_id = self.binding_repository.get_robot_id(user_id)
        if not robot_id:
            return False, "Нет привязки для этого пользователя"

        try:
            response = stub.SendCommand(
                robot_pb2.SendCommandRequest(
                    robot_id=robot_id.value,
                    command_text=function_name,
                )
            )
            return response.success, response.message
        except grpc.RpcError as e:
            logger.error("SendCommand RPC error: %s", e)
            return False, "Сервис роботов временно недоступен."

    def initiate_binding(
        self,
        user_id: str,
        robot_id: RobotId,
    ) -> Tuple[bool, str, Optional[BindingCode], Optional[float]]:
        stub = self._get_stub()
        if stub is None:
            return False, "gRPC протобуфы не загружены", None, None

        try:
            response = stub.InitiateBinding(
                robot_pb2.InitiateBindingRequest(robot_id=robot_id.value)
            )
            if not response.success:
                return False, response.message, None, None
            code = BindingCode(response.code) if response.code else None
            expires_at = float(response.expires_at) if response.expires_at else None
            logger.info(
                "[КОД ПРИВЯЗКИ] Пользователь %s -> робот %s. Код: %s",
                user_id,
                robot_id.value,
                response.code,
            )
            return True, response.message, code, expires_at
        except grpc.RpcError as e:
            logger.error("InitiateBinding RPC error: %s", e)
            return False, "Сервис роботов временно недоступен.", None, None

    def complete_binding_with_code(
        self,
        user_id: str,
        robot_id: RobotId,
    ) -> Tuple[bool, str]:
        stub = self._get_stub()
        if stub is None:
            return False, "gRPC протобуфы не загружены"

        try:
            response = stub.NotifyBindingComplete(
                robot_pb2.NotifyBindingCompleteRequest(
                    robot_id=robot_id.value,
                    user_id=user_id,
                )
            )
            return response.success, response.message
        except grpc.RpcError as e:
            logger.error("NotifyBindingComplete RPC error: %s", e)
            return False, "Сервис роботов временно недоступен."

    def is_robot_connected(self, robot_id: str) -> bool:
        stub = self._get_stub()
        if stub is None:
            return False
        try:
            response = stub.IsRobotConnected(
                robot_pb2.IsRobotConnectedRequest(robot_id=robot_id)
            )
            return response.connected
        except grpc.RpcError as e:
            logger.error("IsRobotConnected RPC error: %s", e)
            return False
