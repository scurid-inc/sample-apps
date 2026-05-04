###############################################################################
# PX4 SITL + Gazebo Harmonic + ROS 2 Jazzy  –  Dev Container
# Base: osrf/ros:jazzy-desktop  (ROS 2 Jazzy already installed)
###############################################################################
FROM osrf/ros:jazzy-desktop

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

SHELL ["/bin/bash", "-c"]

# ── Extra system packages needed by PX4 / Gazebo / dev workflow ─────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        sudo git curl wget gnupg2 lsb-release software-properties-common \
        ca-certificates locales build-essential cmake ninja-build ccache \
        python3-pip python3-venv python3-dev python3-setuptools \
        python3-packaging python3-jinja2 python3-jsonschema python3-numpy \
        python3-toml python3-yaml python3-empy \
        python3-colcon-common-extensions ros-dev-tools \
        astyle genromfs exiftool zip unzip xxd rsync \
        gdb-multiarch gcc-arm-none-eabi libnewlib-arm-none-eabi \
        libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly \
        libxml2-dev libxslt1-dev libopencv-dev \
        xterm xauth x11-xserver-utils mesa-utils \
    && locale-gen en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8

# ── Create non-root user (devcontainers remaps UID to match host) ───────────
ARG USERNAME=px4
ARG USER_UID=1000
ARG USER_GID=1000
RUN if getent group ${USER_GID} >/dev/null 2>&1; then \
        GROUP_NAME=$(getent group ${USER_GID} | cut -d: -f1); \
    else \
        GROUP_NAME=${USERNAME}; \
        groupadd --gid ${USER_GID} ${GROUP_NAME}; \
    fi \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m -s /bin/bash ${USERNAME} 2>/dev/null \
    || usermod -l ${USERNAME} -d /home/${USERNAME} -m $(getent passwd ${USER_UID} | cut -d: -f1) 2>/dev/null \
    || true \
    && mkdir -p /home/${USERNAME} \
    && chown ${USER_UID}:${USER_GID} /home/${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

# ── Gazebo Harmonic ─────────────────────────────────────────────────────────
RUN curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
        | gpg --dearmor -o /usr/share/keyrings/gazebo-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gazebo-archive-keyring.gpg] \
        http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
        > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        gz-harmonic \
        ros-jazzy-ros-gz \
    && rm -rf /var/lib/apt/lists/*

# ── Micro XRCE-DDS Agent (bridges PX4 <-> ROS 2) ───────────────────────────
RUN git clone --depth 1 -b v2.4.3 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git /tmp/agent \
    && cd /tmp/agent && mkdir build && cd build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release \
    && make -j"$(nproc)" && make install \
    && ldconfig \
    && rm -rf /tmp/agent

# ── PX4-Autopilot source ────────────────────────────────────────────────────
RUN git clone --recursive --depth 1 -b main \
        https://github.com/PX4/PX4-Autopilot.git /src/PX4-Autopilot \
    && chown -R ${USER_UID}:${USER_GID} /src/PX4-Autopilot

# ── Pre-build px4_msgs for ROS 2 ────────────────────────────────────────────
RUN source /opt/ros/jazzy/setup.bash \
    && mkdir -p /ros2_ws/src \
    && git clone --depth 1 -b main https://github.com/PX4/px4_msgs.git /ros2_ws/src/px4_msgs \
    && cd /ros2_ws \
    && colcon build --packages-select px4_msgs \
    && chown -R ${USER_UID}:${USER_GID} /ros2_ws

# ── Python tooling for PX4 build ────────────────────────────────────────────
RUN pip3 install --break-system-packages \
        kconfiglib pyserial future pymavlink mavsdk pyros-genmsg

# ── Shell init for the px4 user ─────────────────────────────────────────────
RUN cat >> /home/${USERNAME}/.bashrc <<'BASHEOF'
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
export PX4_HOME=/src/PX4-Autopilot
export GZ_SIM_RESOURCE_PATH=${PX4_HOME}/Tools/simulation/gz/models:${PX4_HOME}/Tools/simulation/gz/worlds
export ROS_DOMAIN_ID=0
BASHEOF

# ── Environment defaults ────────────────────────────────────────────────────
ENV PX4_HOME=/src/PX4-Autopilot
ENV GZ_SIM_RESOURCE_PATH=${PX4_HOME}/Tools/simulation/gz/models:${PX4_HOME}/Tools/simulation/gz/worlds
ENV ROS_DOMAIN_ID=0

WORKDIR /src/PX4-Autopilot
