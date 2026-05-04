# PX4 SITL Docker – Offboard Circle Demo

One-click PX4 simulation environment using VS Code Dev Containers.

## What's Inside

| Component | Details |
|---|---|
| **PX4 SITL** | Built from `main` branch inside the container |
| **Gazebo Harmonic** | 3-D physics simulation (`gz_x500` quadcopter) |
| **ROS 2 Jazzy** | Full desktop install |
| **Micro XRCE-DDS Agent** | Bridges PX4 uORB ↔ ROS 2 topics |
| **px4_msgs** | Pre-built in `/ros2_ws` |
| **Offboard circle script** | `scripts/offboard_circle.py` |

## Prerequisites

1. **Docker** installed on your Linux host
2. **VS Code** with the **Dev Containers** extension (`ms-vscode-remote.remote-containers`)
3. **QGroundControl** installed on the host (for ground station UI)
4. Allow X11 access before opening the container:
   ```bash
   xhost +local:docker
   ```

## Quick Start

### 1. Open in Container

```
Open this folder in VS Code → Ctrl+Shift+P → "Dev Containers: Reopen in Container"
```

The first build takes ~15-30 min (downloads Ubuntu 24.04, ROS 2, Gazebo, PX4 source, etc.).  
Subsequent reopens are instant.

### 2. Start the Simulation  (Terminal 1)

```bash
/workspace/scripts/start_simulation.sh
```

This will:
- Launch the **Micro XRCE-DDS Agent** on UDP port **8888**
- Build & run `make px4_sitl gz_x500` (PX4 SITL + Gazebo)

Wait until you see the PX4 shell prompt (`pxh>`).

### 3. Connect QGroundControl  (Host)

QGroundControl should auto-connect because the container uses `--network=host`.  
If it doesn't, manually add a **UDP** comm link to `127.0.0.1:14570`.

### 4. Run the Offboard Circle  (Terminal 2, inside container)

```bash
/workspace/scripts/run_offboard_circle.sh
```

Or with custom parameters:

```bash
/workspace/scripts/run_offboard_circle.sh --radius 15.0 --omega 0.3 --altitude 8.0
```

The script will:
1. Send offboard heartbeats for ~0.2 s
2. Request **OFFBOARD** mode + **ARM**
3. Command the drone to trace a circle

### 5. Alternative: Run Manually

```bash
# Terminal 1 – inside container
cd /src/PX4-Autopilot
make px4_sitl gz_x500

# Terminal 2 – inside container
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
MicroXRCEAgent udp4 -p 8888 &
python3 /workspace/scripts/offboard_circle.py
```

## Network / Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 14570 | UDP | PX4 SITL ↔ QGroundControl |
| 14580 | UDP | Companion link |
| 8888 | UDP | Micro XRCE-DDS Agent (PX4 ↔ ROS 2) |

The container runs with `--network=host`, so all ports are shared with the host.

## File Layout

```
PX4-Docker/
├── .devcontainer/
│   ├── Dockerfile          # Full build: Ubuntu 24.04 + ROS 2 + Gazebo + PX4
│   ├── devcontainer.json   # VS Code Dev Container config
│   └── entrypoint.sh       # Creates non-root user matching host UID
├── scripts/
│   ├── offboard_circle.py      # ROS 2 offboard circle controller
│   ├── run_offboard_circle.sh  # Convenience launcher with CLI args
│   └── start_simulation.sh     # One-command sim startup
└── README.md
```

## Troubleshooting

### Gazebo: "Can't open display: :0"
```bash
# On the host, before opening the container:
xhost +local:docker
```
If `DISPLAY` differs on your system, update the `DISPLAY` env in `devcontainer.json`.

### Permission errors on PX4 build artifacts
The entrypoint creates a `px4` user matching your host UID. If files are still owned by root:
```bash
sudo chown -R $(id -u):$(id -g) /src/PX4-Autopilot/build
```

### QGroundControl won't connect
With `--network=host` QGC should see the SITL instance automatically. Verify the SITL is running and check `netstat -ulnp | grep 14570`.
