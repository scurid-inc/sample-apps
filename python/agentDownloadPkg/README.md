# Python Sample App
This folder contains a sample app for the following features to be done on edge devices that run with an OS.

1. Enables Edge Device to download an artifact based on identity associated with the agent. 

## Dependency installation
```
pip3 install -r requirements.txt
```
## Prerequisite
1. The Scurid Server shall be up and running. 
2. The Scurid App is connected to the Scurid Server.
3. The Scurid Edge Agent is up and Approved by the Scurid App.

## Steps to execute the example
```
python3 main.py
```
Upon execution of the above command a selection menu appears on the terminal

```
1. Generate Identity
2. Download Package
 
Select your operation 
```
First we need to generate an identity. Select option 1 

```
Select your operation 1
```
Enter Identity Name 

```
Identity Name my_device_identity
```
The identity is successfully generated.

```
Identity DID :  did:scurid:0x8F55005e688cA37165e36D734b1a0374f156b39f
Identity Name :  my_device_identity
 
Switch to the App and approve identity
```
Now move to the Scurid App and switch to the Identities section of the App. The newly generated identity can be found under Pending tab. Approve the identity and upload the artifact through the App.

Switch back to the terminal 
```
1. Generate Identity
2. Download Package
 
Select your operation 2
```
Select operation 2

Enter the DID of my_device_identity

Enter the full storage path where the artifact will be downloaded.

```
Identity DID : did:scurid:0x8F55005e688cA37165e36D734b1a0374f156b39f
Storage Path : /Users/roshan/Downloads/sample-apps/python/agentDownloadPkg/downloads
 
Package downloaded at location:  /Users/roshan/Downloads/sample-apps/python/agentDownloadPkg/downloads
```

Artifact is downloaded.
