"""
gRPC servicer: приём stream-подключений от роботов.
"""
import logging
import queue

from grpc_proto import robot_pb2
from grpc_proto import robot_pb2_grpc

from gateway.connection_manager import get_connection_manager

logger = logging.getLogger(__name__)


class RobotCommandServiceServicer(robot_pb2_grpc.RobotCommandServiceServicer):
    """Server Streaming RPC — отправка команд роботу."""

    def __init__(self):
        self.connection_manager = get_connection_manager()

    def StreamCommands(self, request, context):
        robot_id = str(request.robot_id).strip() if request.robot_id else None

        if not robot_id:
            logger.error("Робот подключился без robot_id")
            yield robot_pb2.StreamMessage(
                error=robot_pb2.ErrorMessage(
                    error_code="INVALID_REQUEST",
                    error_message="robot_id is required",
                )
            )
            return

        logger.info("Робот %s подключился", robot_id)
        message_queue = queue.Queue()
        self.connection_manager.add_connection(robot_id, message_queue)

        try:
            yield robot_pb2.StreamMessage(
                status=robot_pb2.StatusMessage(
                    status="connected",
                    message="Робот подключен, ожидание команд",
                )
            )
            while context.is_active():
                try:
                    message = message_queue.get(timeout=1.0)
                    yield message
                except queue.Empty:
                    continue
        except Exception as e:
            logger.error("Ошибка в stream для робота %s: %s", robot_id, e, exc_info=True)
            try:
                yield robot_pb2.StreamMessage(
                    error=robot_pb2.ErrorMessage(
                        error_code="STREAM_ERROR",
                        error_message=str(e),
                    )
                )
            except Exception:
                pass
        finally:
            self.connection_manager.remove_connection(robot_id)
            logger.info("Робот %s отключился", robot_id)
