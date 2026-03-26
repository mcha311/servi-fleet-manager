#!/bin/bash
# ============================================================
# Servi ROS2 Bridge - Docker 엔트리포인트
# ============================================================
set -e

# ROS2 Jazzy 환경 소싱
source /opt/ros/jazzy/setup.bash

# 워크스페이스 소싱
if [ -f /ros2_ws/install/setup.bash ]; then
    source /ros2_ws/install/setup.bash
fi

echo "🤖 ROS2 Bridge 시작"
echo "   FASTAPI_WS_URL: ${FASTAPI_WS_URL}"
echo "   ROS_DOMAIN_ID: ${ROS_DOMAIN_ID}"
echo "   RMW: ${RMW_IMPLEMENTATION}"

exec "$@"