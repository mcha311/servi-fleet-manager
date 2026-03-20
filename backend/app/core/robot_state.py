"""
Robot State Store
=================
ROS2에서 수신한 로봇 상태를 메모리에 캐싱
Redis로 백업 (선택적)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RobotStateStore:
    """
    로봇 상태 인메모리 스토어 + Redis 캐시
    
    구조:
    {
        "robot_01": {
            "pose": {...},
            "status": {...},
            "battery": {...},
            "scan": {...},
            "last_seen": "ISO datetime",
        }
    }
    """

    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self._store: dict = {}
        self._redis = redis_client
        self._bridge_connected = False
        self._bridge_connected_at: Optional[str] = None
        self._registered_robots: list[str] = []
        self._lock = asyncio.Lock()

    # ─── 브릿지 연결 관리 ─────────────────────────────────────

    def register_ros2_robots(self, robot_ids: list[str]):
        self._registered_robots = robot_ids
        self._bridge_connected = True
        self._bridge_connected_at = datetime.now(timezone.utc).isoformat()
        for rid in robot_ids:
            if rid not in self._store:
                self._store[rid] = {
                    "robot_id": rid,
                    "source": "ros2",
                    "pose": None,
                    "status": {"state": "unknown"},
                    "battery": None,
                    "scan": None,
                    "last_seen": None,
                }

    def mark_bridge_disconnected(self):
        self._bridge_connected = False
        logger.warning("ROS2 Bridge disconnected - state is stale")

    def is_bridge_connected(self) -> bool:
        return self._bridge_connected

    def get_registered_robots(self) -> list[str]:
        return self._registered_robots

    def is_robot_available(self, robot_id: str) -> bool:
        return robot_id in self._store

    # ─── 상태 업데이트 ────────────────────────────────────────

    def update_pose(self, robot_id: str, data: dict):
        self._ensure_robot(robot_id)
        self._store[robot_id]["pose"] = data
        self._store[robot_id]["last_seen"] = datetime.now(timezone.utc).isoformat()

    def update_status(self, robot_id: str, data: dict):
        self._ensure_robot(robot_id)
        self._store[robot_id]["status"] = {
            **self._store[robot_id].get("status", {}),
            **data,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def update_battery(self, robot_id: str, data: dict):
        self._ensure_robot(robot_id)
        self._store[robot_id]["battery"] = data

    def update_scan(self, robot_id: str, data: dict):
        self._ensure_robot(robot_id)
        # 스캔은 최신 것만 유지 (메모리 절약)
        self._store[robot_id]["scan"] = data

    # ─── 상태 조회 ────────────────────────────────────────────

    def get_robot_state(self, robot_id: str) -> Optional[dict]:
        return self._store.get(robot_id)

    def get_all_robots(self) -> list[dict]:
        return list(self._store.values())

    # ─── 내부 유틸 ────────────────────────────────────────────

    def _ensure_robot(self, robot_id: str):
        if robot_id not in self._store:
            self._store[robot_id] = {
                "robot_id": robot_id,
                "source": "ros2",
                "pose": None,
                "status": {"state": "unknown"},
                "battery": None,
                "scan": None,
                "last_seen": None,
            }