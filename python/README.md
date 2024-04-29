# Python Sample App
This folder contains a sample app for the following features to be done on edge devices that run with an OS.

1. Creating unique identities on the edge
2. Registering the identity with the Scurid Edge Agent
3. Signing data with the generated identity
4. Verify data that has been signed

## Create Identity
Generates a unique identity by calling an API to the Scurid Edge Agent. 

## Register Identity
Registers the generated identity to the Scurid Edge Agent.

## Sign Data
Takes the generated identity and the data the user wants to send as input parameters and generates a signature based on these.
**NOTE** The user will have to manually update the identity input parameter to be the one that is generated on their machine. This identity is printed out when creating the identity.

## Verify data
Takes the signature, generated identity, and user data as input parameters and verifies that the identity and data are valid with respect to the generated signature.
**NOTE** The user will have to manually update the identity and signature input parameters to be the ones that are generated on their machine. These values are printed out in the previous functions.

Testing the validity of the data can be done simply by altering the user data or the generated identity to be different than what was generated. 