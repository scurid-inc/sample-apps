# Scurid Edge Agent Installation Script

This script automates the installation and setup of the **Scurid Edge Agent**, ensuring it is downloaded, installed, configured, and managed as a **systemd service**.

---

## Features
- **Downloads the latest binary** from a specified URL 
- **Configures the agent** using provided command-line parameters or environment variables.
- **Ensures correct permissions** for the `scurid` user.
- **Sets up a systemd service** for automatic startup and management.

---

## Usage

### Run the script

```shell
install.sh
```

## Specify a custom download URL
```shell
install.sh --url "https://example.com/custom-agent"
```

## Configuration
1. If an .env file is found in $HOME, /home/atmark/, or /home/user1/, the script will use EDGE_ID as the agent name.
2. If --name is provided via CLI, it overrides the .env value.


| Parameter | Description | Default Value                                                                                     |
|-----------|-------------|---------------------------------------------------------------------------------------------------|
| `--url`   | Custom download URL for the agent binary. | `https://storage.googleapis.com/scurid-artifacts/edgeagent/v24.1.0.0/scuridedgeagent-linux-amd64` |
| `--spaaddr` | Custom platform address. | `<yourserver.scurid.com>:443`                                                                     |
| `--port` | gRPC port the agent should use. | `:4040`                                                                                           |
| `--address` | gRPC address the agent should bind to. | `localhost`                                                                                       |
| `--store` | Storage path for agent data. | `/var/lib/scurid/keys`                                                                            |
| `--pkg` | Package directory for agent dependencies. | `./pkg/`                                                                                          |
| `--syncrate` | Synchronization rate in seconds. | `30s`                                                                                             |
| `--name` | Name of the agent instance. Overrides environment values. | `scurid-edge-agent-1` or value from `.env` (`EDGE_ID`)                                            |


## Download for different linux flavours and architecture Edge Agent v25.1.2.0

NOTE: These are provided for quick easy access. For the latest version, please refer to the [Scurid Edge Agent Releases](https://www.scurid.com/downloads)

| Platform      | URL |
|---------------|-----|
| freebsd-amd64 | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-freebsd-amd64 |
| freebsd-arm5   | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-freebsd-arm5|
| freebsd-arm7    | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-freebsd-arm7|
| linux-amd64     | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-linux-amd64|
| linux-arm5   | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-linux-arm5|
| linux-arm6    | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-linux-arm6|
| linux-arm64    | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-linux-arm64|
| linux-arm7   | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-linux-arm7|
| linux-mips64   | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-linux-mips64|
| linux-mips64le  | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-linux-mips64le|
| linux-ppc64| https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-linux-ppc64|
| linux-ppc64le   | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-linux-ppc64le|
| netbsd-amd64 | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-netbsd-amd64|
| netbsd-arm6  | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-netbsd-arm6|
| netbsd-arm7| https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-netbsd-arm7|
| openbsd-amd64   | https://storage.googleapis.com/scurid-artifacts/edgeagent/v25.1.2.0/v25.1.2.0-openbsd-amd64|




## Systemd Service

The script automatically creates a systemd service:
* Service Name: scuridedgeagent 
* Service File: /etc/systemd/system/scuridedgeagent.service

```shell
sudo systemctl status scuridedgeagent
```

## Restart the service
```shell
sudo systemctl restart scuridedgeagent
```

## Logs of the systemd service
```shell
sudo journalctl -u scuridedgeagent --no-pager --lines=50
```

