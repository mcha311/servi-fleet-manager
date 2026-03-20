"""
Servi Fleet Manager - ROS2 Bridge Node
=======================================
ROS2 토픽 ↔ FastAPI WebSocket 브릿지

구독 토픽 (ROS2 → FastAPI):
  /robot_{id}/pose          : nav_msgs/Odometry
  /robot_{id}/status        : std_msgs/String (JSON)
  /robot_{id}/battery       : sensor_msgs/BatteryState
  /robot_{id}/scan          : sensor_msgs/LaserScan (다운샘플링)
  /robot_{id}/nav/feedback  : nav2_msgs/NavigateToPose_FeedbackMessage

발행 토픽 (FastAPI → ROS2):
  /robot_{id}/goal          : geometry_msgs/PoseStamped
  /robot_{id}/cmd_vel       : geometry_msgs/Twist
  /robot_{id}/cancel_goal   : std_msgs/Bool
"""

import os
import json
import math
import asyncio
import threading
import logging
from datetime import datetime, timezone
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState, LaserScan
from std_msgs.msg import String, Bool
from nav2_msgs.action import NavigateToPose
from builtin_interfaces.msg import Time

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from tenacity import retry, wait_exponential, stop_after_attempt, before_sleep_log

logging.basicConfig(
    level=getattr(logging, os.getenv("BRIDGE_LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("servi_bridge")


# ─────────────────────────────────────────────────────────────
# 유틸 함수
# ─────────────────────────────────────────────────────────────

def quaternion_to_yaw(q) -> float:
    """쿼터니언 → yaw (라디안) 변환"""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def yaw_to_quaternion(yaw: float) -> dict:
    """yaw → 쿼터니언 변환"""
    return {
        "x": 0.0,
        "y": 0.0,
        "z": math.sin(yaw / 2.0),
        "w": math.cos(yaw / 2.0),
    }


def ros_time_to_iso(stamp: Time) -> str:
    ts = stamp.sec + stamp.nanosec * 1e-9
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def downsample_scan(ranges: list, target_points: int = 36) -> list:
    """라이다 데이터 다운샘플링 (대역폭 절약)"""
    step = max(1, len(ranges) // target_points)
    return [r if not math.isinf(r) and not math.isnan(r) else -1.0
            for r in ranges[::step]]


# ─────────────────────────────────────────────────────────────
# ROS2 Bridge Node
# ─────────────────────────────────────────────────────────────

class ServiBridgeNode(Node):
    """
    ROS2 ↔ FastAPI 브릿지 메인 노드
    - ROS2 토픽 구독/발행
    - asyncio 이벤트 루프에서 WebSocket 연결 관리
    """

    def __init__(self):
        super().__init__("servi_bridge_node")

        # 파라미터 선언
        self.declare_parameter("fastapi_ws_url", os.getenv("FASTAPI_WS_URL", "ws://localhost:8000/ws/ros2"))
        self.declare_parameter("robot_namespace", os.getenv("ROBOT_NAMESPACE", "/robot"))
        self.declare_parameter("robot_ids", os.getenv("ROBOT_IDS", "robot_01,robot_02"))
        self.declare_parameter("publish_rate_hz", 10.0)
        self.declare_parameter("scan_downsample_points", 36)

        self.ws_url: str = self.get_parameter("fastapi_ws_url").value
        self.robot_ns: str = self.get_parameter("robot_namespace").value
        self.robot_ids: list[str] = self.get_parameter("robot_ids").value.split(",")
        self.scan_points: int = self.get_parameter("scan_downsample_points").value

        # WebSocket 연결 (asyncio)
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._ws_lock = asyncio.Lock()
        self._send_queue: asyncio.Queue = asyncio.Queue(maxsize=200)

        # ROS2 퍼블리셔 / 구독자 딕셔너리 {robot_id: publisher}
        self._goal_pubs: dict = {}
        self._cmd_vel_pubs: dict = {}
        self._cancel_pubs: dict = {}
        self._nav_clients: dict = {}

        # 각 로봇별 구독/발행 설정
        for rid in self.robot_ids:
            self._setup_robot(rid.strip())

        self.get_logger().info(
            f"🤖 ServiBridgeNode initialized | robots: {self.robot_ids} | ws: {self.ws_url}"
        )

    def _setup_robot(self, robot_id: str):
        """로봇별 ROS2 토픽 구독/발행 설정"""
        ns = f"{self.robot_ns}/{robot_id}"

        # ── 구독 (ROS2 → Bridge → FastAPI) ────────────────────
        self.create_subscription(
            Odometry,
            f"{ns}/odom",
            lambda msg, rid=robot_id: self._on_odom(rid, msg),
            10,
        )
        self.create_subscription(
            String,
            f"{ns}/status",
            lambda msg, rid=robot_id: self._on_status(rid, msg),
            10,
        )
        self.create_subscription(
            BatteryState,
            f"{ns}/battery",
            lambda msg, rid=robot_id: self._on_battery(rid, msg),
            10,
        )
        self.create_subscription(
            LaserScan,
            f"{ns}/scan",
            lambda msg, rid=robot_id: self._on_scan(rid, msg),
            10,
        )

        # ── 발행 (FastAPI → Bridge → ROS2) ────────────────────
        self._goal_pubs[robot_id] = self.create_publisher(PoseStamped, f"{ns}/goal_pose", 10)
        self._cmd_vel_pubs[robot_id] = self.create_publisher(Twist, f"{ns}/cmd_vel", 10)
        self._cancel_pubs[robot_id] = self.create_publisher(Bool, f"{ns}/cancel_goal", 10)

        # ── Nav2 Action Client ─────────────────────────────────
        self._nav_clients[robot_id] = ActionClient(
            self, NavigateToPose, f"{ns}/navigate_to_pose"
        )

        self.get_logger().info(f"  ✅ Robot setup: {robot_id} (ns: {ns})")

    # ─── ROS2 → FastAPI 콜백 ──────────────────────────────────

    def _on_odom(self, robot_id: str, msg: Odometry):
        """오도메트리 → FastAPI pose 업데이트"""
        pos = msg.pose.pose.position
        ori = msg.pose.pose.orientation
        vel = msg.twist.twist

        payload = {
            "type": "robot_pose",
            "robot_id": robot_id,
            "data": {
                "x": round(pos.x, 4),
                "y": round(pos.y, 4),
                "z": round(pos.z, 4),
                "yaw": round(math.degrees(quaternion_to_yaw(ori)), 2),
                "linear_vel": round(vel.linear.x, 4),
                "angular_vel": round(vel.angular.z, 4),
                "timestamp": ros_time_to_iso(msg.header.stamp),
            },
        }
        self._enqueue(payload)

    def _on_status(self, robot_id: str, msg: String):
        """로봇 상태 메시지 → FastAPI"""
        try:
            status_data = json.loads(msg.data)
        except json.JSONDecodeError:
            status_data = {"raw": msg.data}

        payload = {
            "type": "robot_status",
            "robot_id": robot_id,
            "data": {**status_data, "timestamp": datetime.now(timezone.utc).isoformat()},
        }
        self._enqueue(payload)

    def _on_battery(self, robot_id: str, msg: BatteryState):
        """배터리 상태 → FastAPI"""
        payload = {
            "type": "robot_battery",
            "robot_id": robot_id,
            "data": {
                "percentage": round(msg.percentage * 100, 1),
                "voltage": round(msg.voltage, 2),
                "current": round(msg.current, 3),
                "charging": msg.power_supply_status == BatteryState.POWER_SUPPLY_STATUS_CHARGING,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        self._enqueue(payload)

    def _on_scan(self, robot_id: str, msg: LaserScan):
        """라이다 스캔 (다운샘플링 후) → FastAPI"""
        payload = {
            "type": "robot_scan",
            "robot_id": robot_id,
            "data": {
                "ranges": downsample_scan(list(msg.ranges), self.scan_points),
                "angle_min": round(math.degrees(msg.angle_min), 2),
                "angle_max": round(math.degrees(msg.angle_max), 2),
                "range_max": msg.range_max,
                "timestamp": ros_time_to_iso(msg.header.stamp),
            },
        }
        self._enqueue(payload)

    # ─── FastAPI → ROS2 커맨드 처리 ───────────────────────────

    def dispatch_command(self, message: dict):
        """FastAPI에서 받은 커맨드를 ROS2로 발행"""
        cmd_type = message.get("type")
        robot_id = message.get("robot_id")
        data = message.get("data", {})

        if robot_id not in self.robot_ids:
            self.get_logger().warning(f"Unknown robot_id: {robot_id}")
            return

        if cmd_type == "navigate_to":
            self._send_nav_goal(robot_id, data)
        elif cmd_type == "cmd_vel":
            self._send_cmd_vel(robot_id, data)
        elif cmd_type == "cancel_goal":
            self._send_cancel(robot_id)
        else:
            self.get_logger().warning(f"Unknown command type: {cmd_type}")

    def _send_nav_goal(self, robot_id: str, data: dict):
        """Nav2 목표 지점 발행"""
        msg = PoseStamped()
        msg.header.frame_id = "map"
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x = float(data.get("x", 0.0))
        msg.pose.position.y = float(data.get("y", 0.0))
        msg.pose.position.z = 0.0

        yaw = float(data.get("yaw", 0.0))
        q = yaw_to_quaternion(math.radians(yaw))
        msg.pose.orientation.x = q["x"]
        msg.pose.orientation.y = q["y"]
        msg.pose.orientation.z = q["z"]
        msg.pose.orientation.w = q["w"]

        self._goal_pubs[robot_id].publish(msg)
        self.get_logger().info(
            f"📍 Nav goal sent → {robot_id}: ({data.get('x')}, {data.get('y')}, yaw={yaw}°)"
        )

    def _send_cmd_vel(self, robot_id: str, data: dict):
        """속도 명령 발행"""
        msg = Twist()
        msg.linear.x = float(data.get("linear_x", 0.0))
        msg.linear.y = float(data.get("linear_y", 0.0))
        msg.angular.z = float(data.get("angular_z", 0.0))
        self._cmd_vel_pubs[robot_id].publish(msg)

    def _send_cancel(self, robot_id: str):
        """목표 취소"""
        msg = Bool()
        msg.data = True
        self._cancel_pubs[robot_id].publish(msg)
        self.get_logger().info(f"🛑 Goal cancelled → {robot_id}")

    # ─── 내부 유틸 ────────────────────────────────────────────

    def _enqueue(self, payload: dict):
        """비동기 큐에 메시지 추가 (큐가 꽉 차면 오래된 것 제거)"""
        try:
            self._send_queue.put_nowait(payload)
        except asyncio.QueueFull:
            # 오래된 메시지 제거 후 재시도
            try:
                self._send_queue.get_nowait()
                self._send_queue.put_nowait(payload)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
# WebSocket 연결 관리 (asyncio)
# ─────────────────────────────────────────────────────────────

class WebSocketManager:
    """FastAPI WebSocket 연결 + 재연결 로직"""

    def __init__(self, node: ServiBridgeNode):
        self.node = node
        self.logger = logging.getLogger("servi_bridge.ws")

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(50),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
    )
    async def connect_and_run(self):
        """WebSocket 연결 후 송수신 루프 실행"""
        url = self.node.ws_url
        self.logger.info(f"🔌 Connecting to FastAPI: {url}")

        async with websockets.connect(
            url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            self.node._ws = ws
            self.logger.info("✅ WebSocket connected!")

            # 연결 등록 메시지
            await ws.send(json.dumps({
                "type": "bridge_connected",
                "robot_ids": self.node.robot_ids,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))

            # 송신/수신 태스크 동시 실행
            await asyncio.gather(
                self._sender_loop(ws),
                self._receiver_loop(ws),
            )

    async def _sender_loop(self, ws):
        """큐에서 메시지 꺼내서 WebSocket으로 전송"""
        while True:
            try:
                payload = await asyncio.wait_for(
                    self.node._send_queue.get(), timeout=1.0
                )
                await ws.send(json.dumps(payload))
            except asyncio.TimeoutError:
                continue
            except ConnectionClosed:
                self.logger.warning("WebSocket closed (sender)")
                raise
            except Exception as e:
                self.logger.error(f"Sender error: {e}")

    async def _receiver_loop(self, ws):
        """FastAPI에서 커맨드 수신 → ROS2 발행"""
        async for raw in ws:
            try:
                message = json.loads(raw)
                self.logger.debug(f"📨 Received: {message.get('type')} for {message.get('robot_id')}")
                self.node.dispatch_command(message)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error: {e}")
            except Exception as e:
                self.logger.error(f"Receiver error: {e}")


# ─────────────────────────────────────────────────────────────
# 메인 진입점
# ─────────────────────────────────────────────────────────────

def main():
    rclpy.init()
    node = ServiBridgeNode()

    # ROS2 executor (별도 스레드)
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    ros_thread = threading.Thread(target=executor.spin, daemon=True)
    ros_thread.start()

    # asyncio 이벤트 루프 (메인 스레드)
    ws_manager = WebSocketManager(node)

    try:
        asyncio.run(ws_manager.connect_and_run())
    except KeyboardInterrupt:
        logger.info("🛑 Bridge shutting down...")
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()