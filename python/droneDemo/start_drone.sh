#!/usr/bin/env bash

set -e

SESSION="scurid_drone"
SCURID_AGENT="v25.1.2.1-linux-amd64"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is not installed."
    read -r -p "Install tmux now? [y/N]: " REPLY
    case "$REPLY" in
        [yY]|[yY][eE][sS])
            apt update && apt install -y tmux
            ;;
        *)
            echo "tmux is required. Exiting."
            exit 1
            ;;
    esac
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "tmux session '$SESSION' already exists."
    read -r -p "Kill existing session and start a new one? [y/N]: " REPLY
    case "$REPLY" in
        [yY]|[yY][eE][sS])
            tmux kill-session -t "$SESSION"
            ;;
        *)
            tmux attach-session -t "$SESSION"
            exit 0
            ;;
    esac
fi

tmux new-session -d -s "$SESSION"

tmux set-option -t "$SESSION" -g pane-border-status top
tmux set-option -t "$SESSION" -g pane-border-format "#{pane_title}"

# --- MAIN NODE ---
tmux send-keys -t "$SESSION":0.0 "cd \"$SCRIPT_DIR/ros2_ws\" && source install/setup.bash && ros2 run scurid_drone main.py" C-m
tmux select-pane -t "$SESSION":0.0 -T "MAIN - main communicating with flight controller"

# --- FLIGHT TELEMETRY NODE ---
VERIFY_PANE=$(tmux split-window -h -P -F "#{pane_id}" -t "$SESSION":0.0)
tmux send-keys -t "$VERIFY_PANE" "cd \"$SCRIPT_DIR/ros2_ws\" && source install/setup.bash && ros2 run scurid_drone output.py" C-m
tmux select-pane -t "$VERIFY_PANE" -T "OUTPUT - telemetry from flight controller"

# --- VERIFICATION NODE ---
VERIFY_PANE=$(tmux split-window -h -P -F "#{pane_id}" -t "$SESSION":0.0)
tmux send-keys -t "$VERIFY_PANE" "cd \"$SCRIPT_DIR/ros2_ws\" && source install/setup.bash && ros2 run scurid_drone verification_node.py" C-m
tmux select-pane -t "$VERIFY_PANE" -T "VERIFY - verification_node verifying drone commands"

#--- FLIGHT TELEMETRY SIGNING NODE ---
TELEM_PANE=$(tmux split-window -v -P -F "#{pane_id}" -t "$SESSION":0.0)
tmux send-keys -t "$TELEM_PANE" "cd \"$SCRIPT_DIR/ros2_ws\" && source install/setup.bash && ros2 run scurid_drone drone_telemetry_node.py" C-m
tmux select-pane -t "$TELEM_PANE" -T "TELEMETRY - drone_telemetry_node signing telemetry data"

# --- AGENT ---
AGENT_PANE=$(tmux split-window -v -P -F "#{pane_id}" -t "$SESSION":0.0)
tmux send-keys -t "$AGENT_PANE" "cd \"$SCRIPT_DIR/agent\" && chmod +x \"$SCURID_AGENT\" && ./$SCURID_AGENT --spaaddr demo.scurid.com:443" C-m
tmux select-pane -t "$AGENT_PANE" -T "AGENT - Scurid Agent"

tmux select-layout -t "$SESSION":0 tiled

tmux attach-session -t "$SESSION"