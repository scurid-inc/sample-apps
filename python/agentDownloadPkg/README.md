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
4. For ease of operation enable the auto approval of device identity, see [here](https://scurid.cloud/auto-approve-device)

## Steps to execute the example
```
python3 main.py
```
Upon execution of the above command a selection menu appears on the terminal

```
1. Generate Identity
2. Download Package
3. Exit

Select your operation 
```
First we need to generate an [identity](https://docs.scurid.com/v23.0.2.1/identityContextEnabledFileTransfer/). Select option 1 

```
Select your operation 1
```
### Generate Identity
Enter Identity Name 

```
Identity Name my_device_identity
```
The identity is successfully generated.

```
Identity DID :  did:scurid:0x8F55005e688cA37165e36D734b1a0374f156b39f
Identity Name :  my_device_identity
Timestamp :  1724267096
 
Switch to the App and approve identity
```
Now move to the Scurid App and switch to the Identities section of the App. The newly generated identity can be found under Pending tab. Approve the identity and upload the artifact through the App. See [here](https://docs.scurid.com/v23.0.2.1/identityContextEnabledFileTransfer/) for detailed steps.

### Download Package
Switch back to the terminal 
```
1. Generate Identity
2. Download Package
3. Exit

Select your operation 2
```
Select operation 2

Enter the DID of my_device_identity

Enter the full storage path where the artifact will be downloaded.

```
Identity DID : did:scurid:0x8F55005e688cA37165e36D734b1a0374f156b39f

Storage Path : /Downloads/sample-apps/python/agentDownloadPkg/downloads
 
Package downloaded at location:  /Downloads/sample-apps/python/agentDownloadPkg/downloads
```

Artifact is downloaded.
