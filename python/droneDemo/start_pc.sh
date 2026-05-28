#!/usr/bin/env bash

set -e

SESSION="scurid_pc"
SCURID_AGENT="v25.1.2.1-linux-amd64"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Check if tmux is installed ---
if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is not installed."
    read -r -p "Install tmux now? [y/N]: " REPLY

    case "$REPLY" in
        [yY]|[yY][eE][sS])
            echo "Installing tmux..."
            apt update && apt install -y tmux
            ;;
        *)
            echo "tmux is required to run this script. Exiting."
            exit 1
            ;;
    esac
fi

# --- Prevent duplicate session name ---
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "tmux session '$SESSION' already exists."
    read -r -p "Kill existing session and start a new one? [y/N]: " REPLY

    case "$REPLY" in
        [yY]|[yY][eE][sS])
            tmux kill-session -t "$SESSION"
            ;;
        *)
            echo "Attaching to existing session."
            tmux attach-session -t "$SESSION"
            exit 0
            ;;
    esac
fi

tmux new-session -d -s "$SESSION"

# Enable pane titles
tmux set-option -t "$SESSION" -g pane-border-status top
tmux set-option -t "$SESSION" -g pane-border-format "#{pane_title}"

# --- LAUNCH NODE ---
LAUNCH_PANE="$SESSION":0.0
tmux select-pane -t "$LAUNCH_PANE" -T "Secure drone telemetry stream"
tmux send-keys -t "$LAUNCH_PANE" "cd \"$SCRIPT_DIR/ros2_ws\" && source install/setup.bash && ros2 run scurid_pc pc_telemetry_node.py" C-m

# --- CONTROL NODE ---
CONTROL_PANE=$(tmux split-window -h -P -F "#{pane_id}" -t "$SESSION":0.0)
tmux send-keys -t "$CONTROL_PANE" "cd \"$SCRIPT_DIR/ros2_ws\" && source install/setup.bash && ros2 run scurid_pc control_node.py" C-m
tmux select-pane -t "$CONTROL_PANE" -T "Drone control panel"

# --- ATTACK NODE ---
ATTACK_PANE=$(tmux split-window -v -P -F "#{pane_id}" -t "$CONTROL_PANE")
tmux send-keys -t "$ATTACK_PANE" "cd \"$SCRIPT_DIR/ros2_ws\" && source install/setup.bash && ros2 run scurid_pc attack_node.py" C-m
tmux select-pane -t "$ATTACK_PANE" -T "Attack panel"

# --- AGENT ---
AGENT_PANE=$(tmux split-window -v -P -F "#{pane_id}" -t "$SESSION":0.0)
tmux send-keys -t "$AGENT_PANE" "cd \"$SCRIPT_DIR/agent\" && chmod +x \"$SCURID_AGENT\" && ./$SCURID_AGENT --spaaddr demo.scurid.com:443" C-m
tmux select-pane -t "$AGENT_PANE" -T "AGENT - Scurid Agent"

# Layout
tmux select-layout -t "$SESSION":0 tiled

tmux attach-session -t "$SESSION"