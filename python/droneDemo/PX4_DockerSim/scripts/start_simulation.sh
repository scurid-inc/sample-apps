#!/usr/bin/env bash
# ============================================================================
# start_simulation.sh
#
# Starts the full PX4 SITL + Gazebo Harmonic stack AND the Micro XRCE-DDS
# agent so that ROS 2 topics are available immediately.
#
# Usage (inside the container):
#     /workspace/scripts/start_simulation.sh
#     /workspace/scripts/start_simulation.sh --world aruco.sdf
#
# What it does:
#   1. Launches Micro XRCE-DDS Agent in the background (bridges PX4 ↔ ROS 2)
#   2. Runs  make px4_sitl gz_x500  in the foreground
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

WORLD="/workspace/worlds/aruco.sdf"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --world)
            WORLD="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--world <world_name>]"
            exit 1
            ;;
    esac
done

if [[ "${WORLD}" != /* ]]; then
    WORLD="/workspace/worlds/${WORLD}"
fi

# Source ROS 2 + px4_msgs
set +u
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
set -u

PX4_DIR="/src/PX4-Autopilot"
PX4_WORLDS_DIR="${PX4_DIR}/Tools/simulation/gz/worlds"

WORLD_PATH="${WORLD}"
if [[ ! -f "${WORLD_PATH}" ]]; then
    echo "World file not found: ${WORLD_PATH}"
    exit 1
fi

WORLD_BASENAME="$(basename "${WORLD_PATH}")"
WORLD_NAME="${WORLD_BASENAME%.sdf}"
if [[ "${WORLD_BASENAME}" == "${WORLD_NAME}" ]]; then
    WORLD_BASENAME="${WORLD_BASENAME}.sdf"
    WORLD_PATH_WITH_EXT="${WORLD_PATH}.sdf"
    if [[ -f "${WORLD_PATH_WITH_EXT}" ]]; then
        WORLD_PATH="${WORLD_PATH_WITH_EXT}"
    else
        echo "World file must exist as .sdf: ${WORLD_PATH_WITH_EXT}"
        exit 1
    fi
fi

mkdir -p "${PX4_WORLDS_DIR}"
ln -sfn "${WORLD_PATH}" "${PX4_WORLDS_DIR}/${WORLD_BASENAME}"

echo "────────────────────────────────────────────────────"
echo " Starting Micro XRCE-DDS Agent  (UDP 8888)"
echo "────────────────────────────────────────────────────"

# Clean up stale PX4/Gazebo processes from previous interrupted runs.
if pgrep -f "/src/PX4-Autopilot/build/px4_sitl_default/bin/px4" >/dev/null 2>&1; then
    echo " Found existing PX4 SITL process, stopping it..."
    pkill -f "/src/PX4-Autopilot/build/px4_sitl_default/bin/px4" || true
    sleep 1
fi

if pgrep -f "gz sim" >/dev/null 2>&1; then
    echo " Found existing Gazebo process, stopping it..."
    pkill -f "gz sim" || true
    sleep 1
fi

# Clean up any stale XRCE agent instance using the same UDP port.
if pgrep -f "MicroXRCEAgent udp4 -p 8888" >/dev/null 2>&1; then
    echo " Found existing MicroXRCEAgent on UDP 8888, restarting it..."
    pkill -f "MicroXRCEAgent udp4 -p 8888" || true
    sleep 1
fi

# The agent listens on UDP so PX4 SITL can talk to ROS 2.
# -p 8888 sets the DDS-XRCE transport port (matches PX4 SITL default of UXRCE_DDS_PORT).
MicroXRCEAgent udp4 -p 8888 &
AGENT_PID=$!
echo "  Agent PID: ${AGENT_PID}"

# Trap to clean up the agent when this script exits
cleanup() {
    echo ""
    echo "Shutting down XRCE-DDS Agent (PID ${AGENT_PID})…"
    kill "${AGENT_PID}" 2>/dev/null || true
    kill "${CAMERA_SUB_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Workaround: gz-sensors8 segfaults when a camera sensor has zero subscribers.
# Keep a persistent gz subscriber alive so HasConnections() never returns null.
_keep_camera_alive() {
    while true; do
        local topic
        topic="$(gz topic -l 2>/dev/null | grep -m1 '/sensor/camera/image$' || true)"
        if [[ -n "${topic}" ]]; then
            gz topic -e -t "${topic}" >/dev/null 2>&1 || true
        fi
        sleep 1
    done
}
_keep_camera_alive &
CAMERA_SUB_PID=$!

echo ""
echo "────────────────────────────────────────────────────"
echo " Building & launching PX4 SITL  +  Gazebo (gz_x500)"
echo " World file: ${WORLD_PATH}"
echo " PX4 world name: ${WORLD_NAME}"
echo "────────────────────────────────────────────────────"
cd "${PX4_DIR}"

# Set PX4 to use the matching XRCE-DDS port for its client
unset PX4_GZ_STANDALONE
export PX4_SIM_MODEL=gz_x500
export PX4_GZ_WORLD="${WORLD_NAME}"

#make px4_sitl gz_x500
#make px4_sitl gz_x500_vision
#make px4_sitl gz_x500_depth
make px4_sitl gz_x500_mono_cam_down