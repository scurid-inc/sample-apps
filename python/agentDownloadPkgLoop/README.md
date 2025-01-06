# Python App: Identity Enabled Download
This folder contains a sample app for the following feature to be done on edge devices that run with an OS.

1. Enables an Edge device to download an artifact based on identity associated with the Agent. 

## Dependency installation
```
pip3 install -r requirements.txt
```
## Prerequisite
1. The Scurid Server shall be up and running. See [here](https://docs.scurid.com/v23.0.2.1/quickstart/quickstart-on-premise/#download-scurid-server) for details.
2. The Scurid App is onboarded and is connected to the Scurid Server. See [here](https://docs.scurid.com/v23.0.2.1/quickstart/quickstart-on-premise/#download-scurid-edge-agent) for details.
3. The Scurid Edge Agent is up and Approved by the Scurid App. See [here](https://docs.scurid.com/v23.0.2.1/quickstart/quickstart-on-premise/#step-2-launching-scurid-server-and-app) for details.

## Steps to execute the example
```
python3 main.py
```