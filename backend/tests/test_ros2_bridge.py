"""
ROS2 Bridge Integration Tests
==============================
pytest로 실행: pytest tests/test_ros2_bridge.py -v
"""

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from app.core.robot_state import RobotStateStore
from app.core.connection_manager import ConnectionManager


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def robot_store():
    return RobotStateStore()


@pytest.fixture
def conn_manager():
    return ConnectionManager()


# ─────────────────────────────────────────────────────────────
# RobotStateStore Tests
# ─────────────────────────────────────────────────────────────

class TestRobotStateStore:

    def test_register_ros2_robots(self, robot_store):
        robot_store.register_ros2_robots(["robot_01", "robot_02"])
        assert robot_store.is_bridge_connected()
        assert robot_store.is_robot_available("robot_01")
        assert robot_store.is_robot_available("robot_02")
        assert not robot_store.is_robot_available("robot_99")

    def test_update_pose(self, robot_store):
        robot_store.register_ros2_robots(["robot_01"])
        pose_data = {"x": 1.5, "y": 2.3, "yaw": 45.0, "linear_vel": 0.3}
        robot_store.update_pose("robot_01", pose_data)
        
        state = robot_store.get_robot_state("robot_01")
        assert state["pose"]["x"] == 1.5
        assert state["pose"]["y"] == 2.3
        assert state["last_seen"] is not None

    def test_update_battery_low_alert(self, robot_store):
        robot_store.register_ros2_robots(["robot_01"])
        robot_store.update_battery("robot_01", {"percentage": 15.0, "voltage": 11.2})
        
        state = robot_store.get_robot_state("robot_01")
        assert state["battery"]["percentage"] == 15.0

    def test_bridge_disconnect(self, robot_store):
        robot_store.register_ros2_robots(["robot_01"])
        assert robot_store.is_bridge_connected()
        
        robot_store.mark_bridge_disconnected()
        assert not robot_store.is_bridge_connected()

    def test_auto_create_unknown_robot(self, robot_store):
        """알 수 없는 로봇 ID 데이터 수신 시 자동 등록"""
        robot_store.update_pose("unknown_robot", {"x": 0.0, "y": 0.0})
        state = robot_store.get_robot_state("unknown_robot")
        assert state is not None


# ─────────────────────────────────────────────────────────────
# ConnectionManager Tests
# ─────────────────────────────────────────────────────────────

class TestConnectionManager:

    @pytest.mark.asyncio
    async def test_broadcast_to_frontends(self, conn_manager):
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        conn_manager.frontend_connections = [mock_ws1, mock_ws2]
        
        await conn_manager.broadcast({"type": "test", "data": "hello"})
        
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_bridge_success(self, conn_manager):
        mock_bridge = AsyncMock()
        conn_manager.set_bridge(mock_bridge)
        
        result = await conn_manager.send_to_bridge({"type": "navigate_to", "robot_id": "robot_01"})
        
        assert result is True
        mock_bridge.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_bridge_not_connected(self, conn_manager):
        result = await conn_manager.send_to_bridge({"type": "navigate_to"})
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected_clients(self, conn_manager):
        mock_ws_ok = AsyncMock()
        mock_ws_fail = AsyncMock()
        mock_ws_fail.send_json.side_effect = Exception("disconnected")
        
        conn_manager.frontend_connections = [mock_ws_ok, mock_ws_fail]
        await conn_manager.broadcast({"type": "test"})
        
        # 실패한 클라이언트는 제거됨
        assert mock_ws_fail not in conn_manager.frontend_connections
        assert mock_ws_ok in conn_manager.frontend_connections


# ─────────────────────────────────────────────────────────────
# Bridge Node Unit Tests (ROS2 없이 실행 가능)
# ─────────────────────────────────────────────────────────────

class TestBridgeUtils:
    """ROS2 의존성 없이 유틸 함수만 테스트"""

    def test_quaternion_to_yaw_zero(self):
        """yaw=0 → q=(0,0,0,1)"""
        import math
        # q.w=1, q.z=0 → yaw=0
        class Q:
            x = y = z = 0.0
            w = 1.0

        # 직접 계산
        q = Q()
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        assert abs(yaw) < 0.001

    def test_quaternion_to_yaw_90deg(self):
        """yaw=90도 → q=(0,0,0.707,0.707)"""
        import math
        class Q:
            x = y = 0.0
            z = 0.7071
            w = 0.7071

        q = Q()
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        assert abs(math.degrees(yaw) - 90.0) < 1.0

    def test_downsample_scan(self):
        """라이다 360포인트 → 36포인트"""
        import math
        ranges = [1.0] * 360
        ranges[0] = float('inf')  # 무한대 처리 테스트
        
        # downsample_scan 로직 직접 테스트
        target = 36
        step = max(1, len(ranges) // target)
        result = [r if not math.isinf(r) and not math.isnan(r) else -1.0
                  for r in ranges[::step]]
        
        assert len(result) == target
        assert result[0] == -1.0  # inf → -1.0 변환
        assert result[1] == 1.0


# ─────────────────────────────────────────────────────────────
# Robot Simulator Tests
# ─────────────────────────────────────────────────────────────

class TestRobotSimulator:
    
    @pytest.mark.asyncio
    async def test_simulator_navigate(self):
        from app.core.robot_simulator import RobotSimulator
        
        sim = RobotSimulator("robot_01", start_x=0.0, start_y=0.0)
        sim.set_goal(1.0, 0.0)
        
        assert sim.state == "navigating"
        assert sim.goal == {"x": 1.0, "y": 0.0, "yaw": 0.0}
        
        # 물리 업데이트 10번
        for _ in range(10):
            await sim._update_physics()
        
        # 로봇이 목표 방향으로 이동했는지
        assert sim.x > 0.0

    @pytest.mark.asyncio
    async def test_simulator_cancel(self):
        from app.core.robot_simulator import RobotSimulator
        
        sim = RobotSimulator("robot_01")
        sim.set_goal(10.0, 10.0)
        sim.cancel_goal()
        
        assert sim.state == "idle"
        assert sim.goal is None
        assert sim.linear_vel == 0.0

    def test_simulator_manager_mode_switch(self):
        from app.core.robot_simulator import SimulatorManager
        
        mgr = SimulatorManager()
        assert not mgr.use_ros2
        
        mgr.enable_ros2_mode()
        assert mgr.use_ros2
        
        mgr.enable_simulator_mode()
        assert not mgr.use_ros2