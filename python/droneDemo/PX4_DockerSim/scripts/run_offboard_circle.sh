#!/usr/bin/env bash
# ============================================================================
# run_offboard_circle.sh
#
# Convenience wrapper to launch the offboard mode controller.
# Run this in a SECOND terminal inside the container while the simulation
# is running.
#
# Usage:
#     /workspace/scripts/run_offboard_circle.sh
#     /workspace/scripts/run_offboard_circle.sh --altitude 8.0
# ============================================================================
set -euo pipefail

# Source ROS 2 + px4_msgs
set +u
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
set -u

# Parse optional arguments into ROS 2 parameter format
ALTITUDE=5.0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --altitude) ALTITUDE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "────────────────────────────────────────────────────"
echo " Offboard Mode Controller"
echo "   default altitude = ${ALTITUDE} m"
echo "────────────────────────────────────────────────────"

python3 /workspace/scripts/offboard_mode.py --ros-args \
    -p default_altitude:="${ALTITUDE}"
