# sample-apps
Used for showcasing how to integrate and build new applications using Scurid for IoT Edge and beyond.

This repository is organized into several small apps that demonstrate how to use Scurid for IoT Edge and beyond. Each app is self-contained and includes all the code needed to run it.

Apps written in different languages are organized into separate directories.

## Pre-Requisites
If using any of the sample apps ensure that you have a running Scurid setup. If not please follow the steps [here](https://www.scurid.com/get-started) to get started.
Also see our [documentation](https://docs.scurid.com) for more details.

## Sample Apps

These sample apps are provided to help you quickly get started and test out different functionalities of Scurid for IoT Edge and beyond. 
**Important**: These apps are provided as-is and are not meant to be used in production.

### Golang

Building any golang apps requires [Go](https://golang.org/doc/install) to be installed on your machine.
Also, the Scurid Edge agent should be onboarded running on your device, if not please follow the steps [here](https://docs.scurid.com/v23.0.2.1/autonomousDeviceOnboarding/)

#### PiZero
Provides a simple app that runs on Raspberry Pi Zero, it is possible to run it on other platforms as well. 

The app makes call to ISS Open API to collect current ISS telemetry data, formats it, and then it hands it over to the Scurid Edge Agent, running on the same device, for further processing.

Scurid Edge Agent is responsible for securely connecting to the Scurid server, exchanging data.

To launch the app follow the steps below:

1. Build the app for your platform e.g. for Raspberry Pi Zero:
```
GOOS=linux GOARCH=arm GOARM=6 go build -o pizero-app
```
2. Transfer the app to your device e.g. using [WinSCP](https://winscp.net/eng/download.php) or [FileZilla](https://filezilla-project.org/)
3. Launch the app:
```
./pizero-app -url localhost:4040 -agentconfig /store/config.yaml
```
**NOTE**: The url for the edgeagent and path for the agentConfig flag above is the default path where Scurid Edge Agent stores its configuration file on your device. If you have edge agent running on a different path, please update accordingly.