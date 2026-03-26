# ============================================================
# Servi Fleet Manager - ROS2 Bridge Node
# Base: ROS2 Jazzy on Ubuntu 24.04 (ARM64 compatible)
# ============================================================
FROM ros:jazzy-ros-base-noble

# ── 시스템 의존성 ──────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-colcon-common-extensions \
    ros-jazzy-rclpy \
    ros-jazzy-geometry-msgs \
    ros-jazzy-nav-msgs \
    ros-jazzy-sensor-msgs \
    ros-jazzy-std-msgs \
    ros-jazzy-action-msgs \
    ros-jazzy-nav2-msgs \
    ros-jazzy-tf2-ros \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-cyclonedds \
    && rm -rf /var/lib/apt/lists/*

# ── Python 의존성 ──────────────────────────────────────────
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt --break-system-packages

# ── ROS2 워크스페이스 설정 ─────────────────────────────────
WORKDIR /ros2_ws
COPY servi_bridge/ src/servi_bridge/
RUN . /opt/ros/jazzy/setup.sh && \
    colcon build --symlink-install --packages-select servi_bridge

# ── 엔트리포인트 ───────────────────────────────────────────
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV FASTAPI_WS_URL=ws://backend:8000/ws/ros2
ENV ROBOT_NAMESPACE=/robot
ENV BRIDGE_LOG_LEVEL=INFO

ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "run", "servi_bridge", "bridge_node"]