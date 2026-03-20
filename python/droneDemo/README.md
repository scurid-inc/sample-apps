# Scurid Drone Demo

This project runs Scurid on a drone using ROS 2. It launches ROS 2 nodes for drone control and telemetry, where both control commands and telemetry data are secured and signed using the Scurid infrastructure.

A dedicated ROS 2 node can simulate an attacker by injecting spoofed or tampered control commands into the system.

## System Setup

The demo requires two devices:
- A companion computer (CC) mounted on the drone
- A separate PC (or similar device) for controlling the drone

Both systems should run Ubuntu 22. 

**Note:** If you are not running Ubuntu 22 natively, you can use a Docker container with Ubuntu 22 and ROS 2 Humble:

When starting the container:
- Mount your workspace (this repository) into the container
- Grant access to the required serial device (e.g. `/dev/ttyUSB0`)

Example:
```bash
docker run -it --rm \
  --name <your_ROS2_container_name> \
  --network host \
  --device=<host_serial_device>:<container_serial_device> \
  -v <host_workspace_path>:/workspace \
  -w /workspace \
  <ros2_humble_image> \
  bash
```

## Requirements

- Scurid agent binary placed in the `agent/` folder on both devices
- ROS 2 (Humble)
- Colcon build tools
- Both devices connected to the same network
- gRPC
- Protobuf

## Installation

Clone the repository onto both the drone CC and a PC.

Build the workspace (Do this both on the drone and on the PC):
```bash
cd ros2_ws
colcon build
source install/setup.bash
```

On the CC, install **uXRCE-DDS** by following the official PX4 instructions:

- https://docs.px4.io/main/en/middleware/uxrce_dds

Use the section **"Install Standalone from Source"**.

## Usage
Make sure the CC is connected to the flight controller.

In a terminal on the CC: Start the Micro XRCE-DDS Agent over a serial connection:

```bash
sudo MicroXRCEAgent serial --dev /dev/ttyUSB0 -b 921600
```

**Note:** The serial device may differ (e.g. `/dev/ttyACM0`, `/dev/ttyUSB1`). Check available devices with `ls /dev/tty*` and use the correct one.

This demo is split into two; PC and CC/drone. Both are startet on their respective devices with a shell script.

On PC:
```bash
./start_pc.sh
```
This starts:
- Drone control nodes exposing a simple UI for sending signed control commands
- Telemetry subscriber receiving signed telemetry data from the drone
- Attack simulation used to inject malicious commands to the control stream
- Scurid agent

On drone companion computer:
```bash
./start_drone.sh
```
This starts:
- Communication with the Pixhawk4 flight controller
- Drone telemetry publisher reading raw data from the flight controller and publishing it on a topic
- Scurid-secured telemetry communication used to sign the raw flight controller telemetry data
- Scurid-secured control commands receiver used to verify drone control commands
- Scurid agent