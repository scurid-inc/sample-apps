#!/bin/bash
# entrypoint.sh – Create a non-root user matching the host UID so that files
# written inside the container are owned by the host user.

USER_ID=${LOCAL_USER_ID:-1000}
GROUP_ID=${LOCAL_GROUP_ID:-1000}

if [ "$USER_ID" != "0" ]; then
    groupadd -g "$GROUP_ID" -o px4 2>/dev/null
    useradd --shell /bin/bash -u "$USER_ID" -g "$GROUP_ID" -o -c "" -m px4 2>/dev/null
    echo "px4 ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/px4

    # Give the user ownership of key directories
    chown -R px4:px4 /ros2_ws 2>/dev/null || true
    chown -R px4:px4 /home/px4 2>/dev/null || true

    export HOME=/home/px4

    # Source ROS 2 and px4_msgs in the user's bashrc
    cat >> /home/px4/.bashrc <<'EOF'
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
export PX4_HOME=/src/PX4-Autopilot
export GZ_SIM_RESOURCE_PATH=${PX4_HOME}/Tools/simulation/gz/models:${PX4_HOME}/Tools/simulation/gz/worlds
export ROS_DOMAIN_ID=0
EOF
    chown px4:px4 /home/px4/.bashrc

    exec gosu "$USER_ID" "$@"
else
    source /opt/ros/jazzy/setup.bash
    source /ros2_ws/install/setup.bash
    exec "$@"
fi
