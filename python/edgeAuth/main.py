# Demo Application showing Download functionality by edge agent

import edgeagent_pb2
import edgeagent_pb2_grpc
import grpc

addr = 'localhost:4040'  # update the server and port accordingly, addr corresponds to an agent
channel = grpc.insecure_channel(addr)  # starting a local only channel
stub = edgeagent_pb2_grpc.ScuridEdgeAgentAPIStub(channel)  # grpc client

def createAndRegisterDeviceIdentity():
    # Check if DID file already exists
    try:
        with open('device_did.txt', 'r') as f:
            existing_did = f.read().strip()
        if existing_did:
            print(f"Device already registered with DID: {existing_did}")
            return
    except FileNotFoundError:
        pass  # Continue with registration if file doesn't exist
    
    try:
        ireq = edgeagent_pb2.CreateDeviceIdentityReq()
        create_response = stub.CreateDeviceIdentity(ireq)
    except grpc.RpcError as e:
        print(f'failed setting: {e.details}')
        return
    else:
        print(create_response)
    
    try:
        deviceName = "deviceAuthTest"
        ireq = edgeagent_pb2.RegisterDeviceIdentityReq(did=create_response.did, deviceName=deviceName)
        register_response = stub.RegisterDeviceIdentity(ireq)
    except grpc.RpcError as e:
        print(f'failed setting: {e.details}')
        return
    else:
        print(register_response)
        # Save DID to file after successful registration
        with open('device_did.txt', 'w') as f:
            f.write(create_response.did)
        print(f"DID saved to device_did.txt")

def getToken():
    try:
        # Read DID from file
        with open('device_did.txt', 'r') as f:
            did = f.read().strip()
        if not did:
            print("No DID found in file. Please register device first.")
            return
            
        ireq = edgeagent_pb2.GetTokenReq(username=did)  # Pass the DID to the request
        req = stub.GetToken(ireq)
    except FileNotFoundError:
        print("device_did.txt not found. Please register device first.")
        return
    except grpc.RpcError as e:
        print(f'failed setting: {e.details}')
    else:
        print(req)

if __name__ == "__main__":
    try:
        # First try to read the DID file
        with open('device_did.txt', 'r') as f:
            if f.read().strip():
                # If DID exists, just get the token
                getToken()
    except FileNotFoundError:
        # If no DID file exists, create and register first, then get token
        print("No device registration found. Creating new device...")
        createAndRegisterDeviceIdentity()
        print("\nGetting token for new device...")
        getToken()

