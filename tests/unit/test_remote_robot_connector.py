"""
Unit-тесты RemoteGrpcRobotConnector (mock gRPC).
"""
from unittest.mock import MagicMock, patch

import pytest

from app.domain.value_objects.robot_id import RobotId
from app.infrastructure.external.remote_grpc_robot_connector import RemoteGrpcRobotConnector

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.fixture
def binding_repo():
    repo = MagicMock()
    repo.get_robot_id.return_value = RobotId("0")
    return repo


@patch("app.infrastructure.external.remote_grpc_robot_connector.robot_pb2_grpc")
@patch("app.infrastructure.external.remote_grpc_robot_connector.robot_pb2")
@patch("app.infrastructure.external.remote_grpc_robot_connector.grpc.insecure_channel")
def test_send_command_success(mock_channel, mock_pb2, mock_grpc_module, binding_repo):
    stub = MagicMock()
    stub.SendCommand.return_value = _FakeResponse(success=True, message="Команда отправлена")
    mock_grpc_module.SkillBridgeServiceStub.return_value = stub

    connector = RemoteGrpcRobotConnector(binding_repo)
    success, message = connector.send_command("user1", "give_paw")

    assert success is True
    assert "отправлена" in message.lower()
    stub.SendCommand.assert_called_once()


@patch("app.infrastructure.external.remote_grpc_robot_connector.robot_pb2_grpc")
@patch("app.infrastructure.external.remote_grpc_robot_connector.robot_pb2")
@patch("app.infrastructure.external.remote_grpc_robot_connector.grpc.insecure_channel")
def test_initiate_binding_success(mock_channel, mock_pb2, mock_grpc_module, binding_repo):
    stub = MagicMock()
    stub.InitiateBinding.return_value = _FakeResponse(
        success=True,
        message="ok",
        code="1234",
        expires_at=9999999999,
    )
    mock_grpc_module.SkillBridgeServiceStub.return_value = stub

    connector = RemoteGrpcRobotConnector(binding_repo)
    success, message, code, expires = connector.initiate_binding("user1", RobotId("0"))

    assert success is True
    assert code is not None
    assert code.value == "1234"
    assert expires is not None


@patch("app.infrastructure.external.remote_grpc_robot_connector.robot_pb2_grpc")
@patch("app.infrastructure.external.remote_grpc_robot_connector.robot_pb2")
@patch("app.infrastructure.external.remote_grpc_robot_connector.grpc.insecure_channel")
def test_is_robot_connected(mock_channel, mock_pb2, mock_grpc_module, binding_repo):
    stub = MagicMock()
    stub.IsRobotConnected.return_value = _FakeResponse(connected=True)
    mock_grpc_module.SkillBridgeServiceStub.return_value = stub

    connector = RemoteGrpcRobotConnector(binding_repo)
    assert connector.is_robot_connected("0") is True
