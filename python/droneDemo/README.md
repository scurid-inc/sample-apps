# Scurid Drone Demo

This project demonstrates how Scurid secures drone communication using ROS 2.

It runs on a drone setup where:
- Control commands are signed before being sent to the drone  
- Telemetry data is signed before being transmitted back  
- A simulated attacker can inject malicious commands to test the system  

---

## Overview

The system consists of two devices:

- **Drone Companion Computer (CC)** – mounted on the drone  
- **Control PC** – used to send commands and receive telemetry  

Both devices run ROS 2 nodes secured by Scurid.

---

## Prerequisites

The following must be installed on both the PC and the Companion Computer (CC):

- Docker
- Docker Compose

The followed must be installed on the CC if real hardware (flight controller) is to be used:
- Micro XRCE-DDS Agent (required for real hardware setup - Will be explained below)

---

## Setup

### 1. Clone the repository

Run on **both PC and CC**:

```bash
git clone --branch drone_demo --recurse-submodules git@github.com:scurid-inc/sample-apps.git
cd sample-apps/python/droneDemo
```

---

### 2. Start the environment

```bash
docker compose up -d --build
docker exec -it scurid_drone_project bash
```

---

### 3. Configure ROS workspace (Do this only if you need a specific px4_msg version)

Inside the container:

```bash
cd workspace/ros2_ws/src/px4_msgs
git checkout <matching-px4-version>
```

The branch must match the PX4 firmware running on the flight controller.

Then build the project inside ros2_ws/:

```bash
cd /workspace/ros2_ws
colcon build
source install/setup.bash
```

---

### 4. Add Scurid agent

Place your agent binary in:

```
agent/
```

---

### 5. Ensure time synchronization

If Autonomous Edge and the corresponding dashboard are to be used, both devices must use the same timezone. Check with:
```bash
date
```
If they're not in the same timezone, change it (use respective timezone):
```bash
ln -sf /usr/share/zoneinfo/Europe/Copenhagen /etc/localtime
echo "Europe/Copenhagen" > /etc/timezone
```

---

## Companion Computer (CC) Setup (This is only required for use on a real drone - Skip this if you're using the simulation)

Install Micro XRCE-DDS Agent on the host (outside Docker). Follow the guide here:
https://docs.px4.io/main/en/middleware/uxrce_dds  

Use "Install Standalone from Source" (The Snap version might also work, I have only build from source)

---

## Running the Demo

### 1. Start DDS Agent (on CC outside Docker) (Again, only do this if you're running on a real drone)
This will allow the CC to receive data from the flight controller.

```bash
sudo MicroXRCEAgent serial --dev /dev/ttyUSB0 -b 921600
```

You might need to use something else than 'USB0'. Check available devices if needed:

```bash
ls /dev/tty*
```

---

### 2. Start the system

Navigate to workspace/:

```
cd /workspace/
```

Start the respective launch scripts:

#### On PC

```bash
./start_pc.sh
```

This launches:
- Telemetry receiver (signed data)
- Control interface (signed commands)
- Attack simulation
- Scurid agent

---

#### On Drone (CC)

```bash
./start_drone.sh
```

This launches:
- Flight controller communication
- Telemetry publisher
- Telemetry signing
- Command verification
- Scurid agent

---
## Development Tips

### Rebuilding the workspace

After making changes, rebuild the workspace:

```bash
cd workspace/ros2_ws
colcon build
```

To build a specific package:

```bash
colcon build --packages-select scurid_drone
```

Always source after building:

```bash
source workspace/ros2_ws/install/setup.bash
```

---

### Clean build

For a clean rebuild, delete:

```bash
workspace/ros2_ws/build/
workspace/ros2_ws/install/
workspace/ros2_ws/log/
```

Then rebuild again with `colcon build`.

---

### Running individual nodes

You can run nodes directly without the start scripts:

```bash
ros2 run scurid_drone drone_telemetry_node.py
```

---

### Using tmux (start scripts)

The `start_pc.sh` and `start_drone.sh` scripts use tmux.

- Switch panes:
  - `Ctrl + b`, then arrow keys  

- Kill session:
  - `Ctrl + b`, then `:`
  - Type: `kill-session`

---

## Simulation (Optional)

If one does not have a drone to use -> The project includes a drone simulation in **PX4_DockerSim/**.

- Follow the instructions in its `README.md`
- When using the simulation, you **do not need to run the MicroXRCEAgent** from step "1. Start DDS Agent (on CC outside Docker)"

QGroundControl must be installed and running.

Download and installation instructions are available here:
https://docs.qgroundcontrol.com/master/en/qgc-user-guide/getting_started/download_and_install.html


---

## Notes

- The CC must be connected to the flight controller (e.g., Pixhawk)
- Serial device names may vary (/dev/ttyUSB0, /dev/ttyACM0, etc.)
- Time mismatch between devices will break validation
- Both sides must use compatible PX4 message versions
- Both devices must be on the same network

---

## What This Demo Shows

- Secure command execution (signed control messages)  
- Secure telemetry streaming (signed telemetry data)  
- Detection of malicious command injection  
