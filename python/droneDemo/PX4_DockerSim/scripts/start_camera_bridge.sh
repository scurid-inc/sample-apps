#!/usr/bin/env bash
# ============================================================================
# start_camera_bridge.sh
#
# Bridges Gazebo camera/depth topics from gz_x500_depth into ROS 2 topics.
# Run this in a separate terminal after starting the simulator.
#
# Usage:
#   /workspace/scripts/start_camera_bridge.sh
#   /workspace/scripts/start_camera_bridge.sh --world aruco
#   /workspace/scripts/start_camera_bridge.sh --model x500_depth_0
# ============================================================================
set -euo pipefail

WORLD=""
MODEL=""
SENSOR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --world)
            WORLD="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --sensor)
            SENSOR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--world <world_name>] [--model <model_name>] [--sensor <sensor_name>]"
            exit 1
            ;;
    esac
done

set +u
source /opt/ros/jazzy/setup.bash
set -u

TOPICS="$(gz topic -l 2>/dev/null || true)"

AUTO_TOPIC="$(printf '%s\n' "${TOPICS}" | grep -E '^/world/.*/model/.*/link/camera_link/sensor/.*/image$' | head -n 1 || true)"

if [[ -z "${WORLD}" && -n "${AUTO_TOPIC}" ]]; then
    WORLD="$(printf '%s' "${AUTO_TOPIC}" | sed -E 's#^/world/([^/]+)/model/([^/]+)/.*#\1#')"
fi

if [[ -z "${MODEL}" && -n "${AUTO_TOPIC}" ]]; then
    MODEL="$(printf '%s' "${AUTO_TOPIC}" | sed -E 's#^/world/([^/]+)/model/([^/]+)/.*#\2#')"
fi

if [[ -z "${SENSOR}" && -n "${AUTO_TOPIC}" ]]; then
    SENSOR="$(printf '%s' "${AUTO_TOPIC}" | sed -E 's#^/world/[^/]+/model/[^/]+/link/[^/]+/sensor/([^/]+)/image$#\1#')"
fi

if [[ -z "${WORLD}" ]]; then
    WORLD="aruco"
fi

if [[ -z "${MODEL}" ]]; then
    MODEL="x500_mono_cam_down_0"
fi

if [[ -z "${SENSOR}" ]]; then
    SENSOR="camera"
fi

IMAGE_TOPIC="/world/${WORLD}/model/${MODEL}/link/camera_link/sensor/${SENSOR}/image"
CAMERA_INFO_TOPIC="/world/${WORLD}/model/${MODEL}/link/camera_link/sensor/${SENSOR}/camera_info"

if ! printf '%s\n' "${TOPICS}" | grep -qx "${IMAGE_TOPIC}"; then
    echo "Could not find image topic: ${IMAGE_TOPIC}"
    echo "Available camera-like topics:"
    printf '%s\n' "${TOPICS}" | grep -Ei 'camera|image|depth|x500' | sed -n '1,40p'
    echo "Try: $0 --world <world> --model <model_instance>"
    exit 1
fi

echo "────────────────────────────────────────────────────"
echo " Starting Gazebo -> ROS2 camera bridge"
echo " World:  ${WORLD}"
echo " Model:  ${MODEL}"
echo " Sensor: ${SENSOR}"
echo "────────────────────────────────────────────────────"

BRIDGE_ARGS=(
    "${IMAGE_TOPIC}@sensor_msgs/msg/Image@gz.msgs.Image"
    "${CAMERA_INFO_TOPIC}@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo"
)

if printf '%s\n' "${TOPICS}" | grep -qx "/depth_camera"; then
    BRIDGE_ARGS+=("/depth_camera@sensor_msgs/msg/Image@gz.msgs.Image")
fi
if printf '%s\n' "${TOPICS}" | grep -qx "/depth_camera/points"; then
    BRIDGE_ARGS+=("/depth_camera/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked")
fi

ros2 run ros_gz_bridge parameter_bridge "${BRIDGE_ARGS[@]}"
