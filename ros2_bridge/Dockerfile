# ============================================================
# Servi Fleet Manager - ROS2 Bridge Node
# Base: ROS2 Humble on Ubuntu 22.04 (ARM64 compatible)
# ============================================================
FROM ros:humble-ros-base-jammy

# ── 시스템 의존성 ──────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-colcon-common-extensions \
    ros-humble-rclpy \
    ros-humble-geometry-msgs \
    ros-humble-nav-msgs \
    ros-humble-sensor-msgs \
    ros-humble-std-msgs \
    ros-humble-action-msgs \
    ros-humble-nav2-msgs \
    ros-humble-tf2-ros \
    && rm -rf /var/lib/apt/lists/*

# ── Python 의존성 ──────────────────────────────────────────
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# ── ROS2 워크스페이스 설정 ─────────────────────────────────
WORKDIR /ros2_ws
COPY servi_bridge/ src/servi_bridge/

RUN . /opt/ros/humble/setup.sh && \
    colcon build --symlink-install --packages-select servi_bridge

# ── 엔트리포인트 ───────────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV FASTAPI_WS_URL=ws://backend:8000/ws/ros2
ENV ROBOT_NAMESPACE=/robot
ENV BRIDGE_LOG_LEVEL=INFO

ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "run", "servi_bridge", "bridge_node"]