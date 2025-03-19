# Python App: Upload Files
This folder contains a sample app for uploading contents to the Scurid server

## Dependency installation
```
pip3 install -r requirements.txt
```
## Prerequisite
1. The Scurid Server shall be up and running. See [here](https://docs.scurid.com/v23.0.2.1/quickstart/quickstart-on-premise/#download-scurid-server) for details.
2. The Scurid App is onboarded and is connected to the Scurid Server. See [here](https://docs.scurid.com/v23.0.2.1/quickstart/quickstart-on-premise/#download-scurid-edge-agent) for details.
3. The Scurid Edge Agent is up and Approved by the Scurid App. See [here](https://docs.scurid.com/v23.0.2.1/quickstart/quickstart-on-premise/#step-2-launching-scurid-server-and-app) for details.
4. Set parameters in the secret/config.ini file.

## Note
In case of compiling the files inside protos/* locally move the compiled files to compiled_protos/*
## Steps to execute the example
```
python3 main.py
```
## Output
```
== Login ==
 
user:  mrx@fexbox.org
login successful
 
== setting persistence and autodir ==
 
persistence is set to True
autoDir is set to True
 
== file upload starts ==
 
 uploading file: file2.txt, at location: datastore/file2.txt
 file:  file2.txt, is successfully uploaded
 
 uploading file: file1.txt, at location: datastore/file1.txt
 file:  file1.txt, is successfully uploaded
 
 uploading file: sample.txt, at location: datastore/sample.txt
 file:  sample.txt, is successfully uploaded
 
== upload complete ==
```