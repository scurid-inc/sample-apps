#!/bin/bash

# Default values
SCURID_AGENT_URL="https://storage.googleapis.com/scurid-artifacts/edgeagent/v24.1.0.0/scuridedgeagent-linux-amd64"
SPA_ADDR="demo.scurid.com:443"  # Default platform address

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --url) SCURID_AGENT_URL="$2"; shift ;;  # Allow custom download URL
        --spaaddr) SPA_ADDR="$2"; shift ;;  # Allow custom SPA address
        --port) GRPC_PORT="$2"; shift ;;
        --address) GRPC_ADDR="$2"; shift ;;
        --store) STORE_PATH="$2"; shift ;;
        --pkg) PKG_DIR="$2"; shift ;;
        --syncrate) SYNC_RATE="$2"; shift ;;
        --name) AGENT_NAME="$2"; shift ;;  # Command-line argument overrides all
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Print the chosen values
echo "Using Scurid Edge Agent URL: $SCURID_AGENT_URL"
echo "Using SPA_ADDR: $SPA_ADDR"

# Download the binary
echo "Downloading Scurid Edge Agent..."
wget -O scuridedgeagent "$SCURID_AGENT_URL"

# Make it executable
echo "Making scuridedgeagent executable..."
chmod +x scuridedgeagent

# Move it to /usr/local/bin/ and set ownership to scurid
echo "Moving scuridedgeagent to /usr/local/bin/..."
sudo mv scuridedgeagent /usr/local/bin/scuridedgeagent
sudo chown scurid:scurid /usr/local/bin/scuridedgeagent
sudo chmod 755 /usr/local/bin/scuridedgeagent

echo "Scurid Edge Agent downloaded, installed, and assigned to scurid user."

# Define variables
APP_NAME="scuridedgeagent"
SERVICE_NAME="scuridedgeagent"
CONFIG_DIR="/etc/scurid/store"
KEYS_DIR="/var/lib/scurid/keys"
EXECUTABLE="/usr/local/bin/$APP_NAME"
LOG_DIR="/var/log/scurid"
LOG_SUBDIR="$LOG_DIR/log"  # Zerolog expects this

# Default values for flags
GRPC_PORT=":4040"
GRPC_ADDR="localhost"
STORE_PATH=$KEYS_DIR
PKG_DIR="./pkg/"
SYNC_RATE="30s"
AGENT_NAME="scurid-edge-agent-1"  # Default if no .env file

# Check if .env file exists in home directory
if [[ -f "$HOME/.env" ]]; then
    source "$HOME/.env"
elif [[ -f "/home/atmark/.env" ]]; then
    source "/home/atmark/.env"
elif [[ -f "/home/user1/.env" ]]; then
    source "/home/user1/.env"
fi

# If EDGE_ID is set in .env, use it as AGENT_NAME
if [[ -n "$EDGE_ID" ]]; then
    AGENT_NAME="$EDGE_ID"
fi

echo "Using AGENT_NAME: $AGENT_NAME"

# Ensure required directories exist (use sudo for system-wide paths)
sudo useradd -r -m -s /bin/false scurid
sudo mkdir -p "$LOG_SUBDIR"
sudo chown -R scurid:scurid "$LOG_DIR"
sudo chmod -R 755 "$LOG_DIR"
sudo mkdir -p /etc/scurid/store
sudo chown -R scurid:scurid /etc/scurid/store
sudo chmod -R 755 /etc/scurid/store

sudo mkdir -p /var/lib/scurid/keys
sudo chown -R scurid:scurid /var/lib/scurid
sudo chmod -R 755 /var/lib/scurid

# Ensure the application exists
if [[ ! -f "$EXECUTABLE" ]]; then
    echo "Error: $EXECUTABLE not found!"
    exit 1
fi

# Create the systemd service file
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

cat <<EOF | sudo tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=Scurid Edge Agent
After=network.target

[Service]
User=scurid
ExecStart=$EXECUTABLE --port=$GRPC_PORT --address=$GRPC_ADDR --spaaddr=$SPA_ADDR --store=$STORE_PATH --pkg=$PKG_DIR --syncrate=$SYNC_RATE --name=$AGENT_NAME
WorkingDirectory=$CONFIG_DIR
Restart=always
RestartSec=5s
StandardOutput=append:$LOG_DIR/output.log
StandardError=append:$LOG_DIR/error.log

[Install]
WantedBy=multi-user.target
EOF

# Set correct permissions
sudo chmod 644 "$SERVICE_FILE"

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Systemd service for $SERVICE_NAME has been created and started."