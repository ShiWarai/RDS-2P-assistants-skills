"""
Запуск gRPC-сервера gateway (роботы + SkillBridge).
"""
import logging
import os
from concurrent import futures

import grpc

from grpc_proto import robot_pb2_grpc
from gateway.robot_servicer import RobotCommandServiceServicer
from gateway.skill_bridge_servicer import SkillBridgeServicer

logger = logging.getLogger(__name__)

DEFAULT_PORT = 50051


def serve(port: int | None = None) -> None:
    port = port or int(os.getenv("GRPC_PORT", str(DEFAULT_PORT)))

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    robot_pb2_grpc.add_RobotCommandServiceServicer_to_server(
        RobotCommandServiceServicer(), server
    )
    robot_pb2_grpc.add_SkillBridgeServiceServicer_to_server(
        SkillBridgeServicer(), server
    )

    listen_addr = f"[::]:{port}"
    server.add_insecure_port(listen_addr)
    server.start()
    logger.info("Robot gateway запущен на порту %s", port)

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Остановка robot gateway...")
        server.stop(0)
