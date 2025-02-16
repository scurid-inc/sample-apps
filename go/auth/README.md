#README

A sample golang app to authenticate the device with the Scurid Server. This is designed to be run as embedded in your backend applications.

## Prerequisites

- A device identity has been created and registered with the Scurid Server. This is done by running the python/edgeAuth/main.py app.
- The device identity has been approved by the Scurid Server.
- update the constants in the main.go file with your Scurid serveraddress, email, password. The user email must have been created and approved in the Scurid App. If not done already see documentation here: https://docs.scurid.com/v23.0.2.1/users/#creating-and-inviting-a-user 

## Running the app

```
go run main.go
```

## Overview
authenticateDevice() wraps the grpc call to first authenticated your backend application with the Scurid Server.

Upon successful authentication, the token is used to subsequently call the  verifyToken() grpc call.

login() is wrapped within the authenticateDevice() function. Helping you to automate the login process.

Scurid Server APIs communicate over SSL/TLS. The CA certificate is loaded from the file ca.crt. Contact Scurid to get the CA certificate.

apiContextWithToken() helps to prepare the context with the token from the Scurid server.

sslCreds() is used to create the transport credentials for the Scurid Server. 
