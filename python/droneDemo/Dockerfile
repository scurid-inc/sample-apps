FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    ros-humble-ament-cmake \
    tmux \
    git \
    build-essential \
    cmake \
    protobuf-compiler \
    libprotobuf-dev \
    libgrpc++-dev \
    protobuf-compiler-grpc \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --upgrade \
    pip==26.1 \
    setuptools==82.0.1 \
    packaging==26.2 \
    wheel==0.47.0

RUN pip3 install --no-cache-dir \
    grpcio==1.80.0 \
    grpcio-tools==1.80.0 \
    protobuf==6.33.6

RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

WORKDIR /workspace