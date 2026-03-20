#!/bin/bash
# ============================================================
# UTM Ubuntu 22.04 ARM64 - ROS2 Humble 설치 및 설정 스크립트
# Servi Fleet Manager - ROS2 Bridge 개발 환경
# ============================================================
set -e

echo "🤖 Servi Fleet Manager - ROS2 개발 환경 설정 시작"
echo "=================================================="

# ── 1. ROS2 Humble 설치 ────────────────────────────────────
echo ""
echo "📦 Step 1: ROS2 Humble 설치"

# Locale 설정
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# ROS2 apt 소스 추가
sudo apt install -y software-properties-common curl
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y \
    ros-humble-desktop \
    ros-humble-nav2-bringup \
    ros-humble-nav2-msgs \
    ros-humble-cyclonedds \
    ros-humble-rmw-cyclonedds-cpp \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-pip

# rosdep 초기화
sudo rosdep init || true
rosdep update

echo "✅ ROS2 Humble 설치 완료"

# ── 2. 환경 변수 설정 ─────────────────────────────────────
echo ""
echo "⚙️  Step 2: 환경 변수 설정"

SHELL_RC="$HOME/.bashrc"

grep -qxF "source /opt/ros/humble/setup.bash" "$SHELL_RC" || \
    echo "source /opt/ros/humble/setup.bash" >> "$SHELL_RC"

grep -qxF "export ROS_DOMAIN_ID=42" "$SHELL_RC" || \
    echo "export ROS_DOMAIN_ID=42" >> "$SHELL_RC"

grep -qxF "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" "$SHELL_RC" || \
    echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> "$SHELL_RC"

# FastAPI 백엔드 URL (Mac 호스트)
# UTM에서 Mac 호스트 IP는 일반적으로 192.168.64.1
FASTAPI_URL="ws://192.168.64.1:8000/ws/ros2"
grep -qxF "export FASTAPI_WS_URL=${FASTAPI_URL}" "$SHELL_RC" || \
    echo "export FASTAPI_WS_URL=${FASTAPI_URL}" >> "$SHELL_RC"

source "$SHELL_RC"
echo "✅ 환경 변수 설정 완료 (ROS_DOMAIN_ID=42)"

# ── 3. ROS2 Navigator 클론 ─────────────────────────────────
echo ""
echo "📥 Step 3: ROS2 Navigator 설정"

WORKSPACE="$HOME/servi_ws"
mkdir -p "$WORKSPACE/src"

# 기존 Navigator 클론 (이미 있으면 스킵)
if [ ! -d "$WORKSPACE/src/ros2-robot-navigator" ]; then
    git clone https://github.com/mcha311/ros2-robot-navigator \
        "$WORKSPACE/src/ros2-robot-navigator"
fi

# servi_bridge 소스 복사 (개발 시)
# docker-compose 없이 직접 실행할 때 사용
# cp -r /path/to/servi-fleet-manager/ros2_bridge/servi_bridge \
#     "$WORKSPACE/src/servi_bridge"

# 빌드
cd "$WORKSPACE"
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

echo "✅ ROS2 워크스페이스 빌드 완료: $WORKSPACE"

# ── 4. 테스트 토픽 발행 확인 ──────────────────────────────
echo ""
echo "🧪 Step 4: 연결 테스트"
echo ""
echo "아래 명령어로 ROS2 토픽 테스트:"
echo ""
echo "  # 포즈 토픽 발행 (테스트용)"
echo "  ros2 topic pub /robot/robot_01/odom nav_msgs/msg/Odometry \\"
echo "    '{pose: {pose: {position: {x: 1.0, y: 2.0}}}}'"
echo ""
echo "  # FastAPI WS 연결 확인"
echo "  ros2 run servi_bridge bridge_node"
echo ""
echo "  # 토픽 목록 확인"
echo "  ros2 topic list | grep robot"

# ── 5. systemd 서비스 등록 (선택) ────────────────────────
echo ""
echo "⚡ Step 5: systemd 서비스 등록 (부팅 시 자동 시작)"

SERVICE_FILE="/etc/systemd/system/servi-ros2-bridge.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Servi ROS2 Bridge Node
After=network.target

[Service]
Type=simple
User=$USER
Environment="ROS_DOMAIN_ID=42"
Environment="RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
Environment="FASTAPI_WS_URL=${FASTAPI_URL}"
ExecStartPre=/bin/bash -c 'source /opt/ros/humble/setup.bash && source ${WORKSPACE}/install/setup.bash'
ExecStart=/bin/bash -c 'source /opt/ros/humble/setup.bash && source ${WORKSPACE}/install/setup.bash && ros2 run servi_bridge bridge_node'
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
# sudo systemctl enable servi-ros2-bridge  # 자동 시작 원하면 활성화
echo "✅ systemd 서비스 등록 완료"
echo "   시작: sudo systemctl start servi-ros2-bridge"
echo "   로그: journalctl -u servi-ros2-bridge -f"

echo ""
echo "=================================================="
echo "🎉 ROS2 개발 환경 설정 완료!"
echo ""
echo "다음 단계:"
echo "  1. source ~/.bashrc"
echo "  2. Mac에서 docker-compose 실행 중인지 확인"
echo "  3. ros2 run servi_bridge bridge_node"
echo "=================================================="