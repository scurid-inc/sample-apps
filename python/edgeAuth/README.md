# Python App: Scurid Authentication

## Dependency installation

```
pip3 install -r requirements.txt
```

## Run the app

```
python3 main.py
```

## EdgeAuth

This sample app is used to authenticate the device with the Scurid Server. 

createAndRegisterDeviceIdentity() - creates a device identity and registers it with the Scurid Server. To avoid creating a new device identity on every run, the device identity is saved in a file called device_did.txt.

getToken() - reads the device identity from the file device_did.txt and uses it to get a token from the Scurid Server.
