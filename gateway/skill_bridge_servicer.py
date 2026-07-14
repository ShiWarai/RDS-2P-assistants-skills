"""
gRPC servicer: API для навыков (salute, alice) внутри кластера.
"""
import logging
import random
import time
import uuid

from grpc_proto import robot_pb2
from grpc_proto import robot_pb2_grpc

from gateway.connection_manager import get_connection_manager

logger = logging.getLogger(__name__)

BINDING_CODE_TTL_SECONDS = 300


class SkillBridgeServicer(robot_pb2_grpc.SkillBridgeServiceServicer):
    """Мост между навыками и подключёнными роботами."""

    def __init__(self):
        self.connection_manager = get_connection_manager()

    def SendCommand(self, request, context):
        robot_id = str(request.robot_id).strip()
        if not robot_id:
            return robot_pb2.SendCommandResponse(success=False, message="robot_id is required")

        if not self.connection_manager.is_connected(robot_id):
            return robot_pb2.SendCommandResponse(success=False, message="Робот не подключен.")

        command_message = robot_pb2.StreamMessage(
            command=robot_pb2.Command(
                command_text=request.command_text,
                timestamp=int(time.time()),
                command_id=str(uuid.uuid4()),
            )
        )
        if self.connection_manager.send_message(robot_id, command_message):
            logger.info("Команда отправлена роботу %s: %s", robot_id, request.command_text)
            return robot_pb2.SendCommandResponse(success=True, message="Команда отправлена")
        return robot_pb2.SendCommandResponse(success=False, message="Не удалось отправить команду.")

    def InitiateBinding(self, request, context):
        robot_id = str(request.robot_id).strip()
        if not robot_id:
            return robot_pb2.InitiateBindingResponse(success=False, message="robot_id is required")

        if not self.connection_manager.is_connected(robot_id):
            return robot_pb2.InitiateBindingResponse(
                success=False,
                message=f"Робот {robot_id} не подключен.",
            )

        code_value = str(random.randint(1000, 9999))
        expires_at = int(time.time() + BINDING_CODE_TTL_SECONDS)

        binding_code_message = robot_pb2.StreamMessage(
            binding_code=robot_pb2.BindingCodeMessage(code=code_value, expires_at=expires_at)
        )
        if not self.connection_manager.send_message(robot_id, binding_code_message):
            return robot_pb2.InitiateBindingResponse(
                success=False,
                message=f"Не удалось отправить код роботу {robot_id}.",
            )

        status_message = robot_pb2.StreamMessage(
            status=robot_pb2.StatusMessage(
                status="binding_required",
                message="Введите код привязки в приложении навыка",
            )
        )
        self.connection_manager.send_message(robot_id, status_message)
        logger.info("[КОД ПРИВЯЗКИ] Робот %s. Код: %s", robot_id, code_value)

        return robot_pb2.InitiateBindingResponse(
            success=True,
            message=f"Введите код для робота {robot_id}. Код отображается в логах робота.",
            code=code_value,
            expires_at=expires_at,
        )

    def NotifyBindingComplete(self, request, context):
        robot_id = str(request.robot_id).strip()
        user_id = str(request.user_id).strip()

        if not self.connection_manager.is_connected(robot_id):
            return robot_pb2.NotifyBindingCompleteResponse(
                success=True,
                message="Привязка завершена (робот не в сети для получения уведомления)",
            )

        status_message = robot_pb2.StreamMessage(
            status=robot_pb2.StatusMessage(
                status="binding_completed",
                message=f"Пользователь {user_id} успешно привязан",
            )
        )
        if self.connection_manager.send_message(robot_id, status_message):
            return robot_pb2.NotifyBindingCompleteResponse(
                success=True,
                message="Уведомление отправлено роботу",
            )
        return robot_pb2.NotifyBindingCompleteResponse(
            success=False,
            message="Не удалось отправить уведомление роботу",
        )

    def IsRobotConnected(self, request, context):
        robot_id = str(request.robot_id).strip()
        return robot_pb2.IsRobotConnectedResponse(
            connected=self.connection_manager.is_connected(robot_id)
        )

    def ListConnectedRobots(self, request, context):
        return robot_pb2.ListConnectedRobotsResponse(
            robot_ids=self.connection_manager.get_connected_robots()
        )
