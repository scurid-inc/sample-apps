import grpc
import compiled_protos.platformapi_pb2
import compiled_protos.platformapi_pb2_grpc  
import compiled_protos.auth_pb2
import compiled_protos.auth_pb2_grpc
import compiled_protos.platformapiv2_pb2
import compiled_protos.platformapiv2_pb2_grpc
import os
import configparser

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config file
config.read('secret/config.ini')

# Access the values in the config file
email = config['login']['email']
password = config['login']['password']
dirpath = config['store']['dirpath']
pathonagent = config['store']['pathonagent']
server = config['infra']['server_and_port']
cert_file = config['infra']['certs']
agentDID = config['infra']['agentDID']
persist_on = config.getboolean('settings', 'persist')
autoDir_on = config.getboolean('settings', 'autodir')

# Read certificate
with open(cert_file, 'rb') as f:
    ca_cert = f.read()

# Create SSL credentials for the secure connection
credentials = grpc.ssl_channel_credentials(ca_cert)

# Create the channel
channel = grpc.secure_channel(server, credentials)

# Create the stub for Upload Files
stub = compiled_protos.platformapi_pb2_grpc.ScuridPlatformAgentAPIStub(channel)

# Create the stub for auth token (Login)
auth_stub = compiled_protos.auth_pb2_grpc.AuthStub(channel)

# Create the stub for setting the autodir and persistence
pfv2_stub = compiled_protos.platformapiv2_pb2_grpc.PlatformStub(channel)


# get the list of files and their
# path of a given dir
def list_files_in_directory(directory_path):
    file_info = []

    for root, dirs, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_info.append((file_path, file))
    
    return file_info

#Login
def Login():
    print("user: ", email)
    try:
        ireq = compiled_protos.auth_pb2.LoginReq(
            user=compiled_protos.auth_pb2.UserStruct(
             username=email
        ),
            password=password
        )
        res = auth_stub.Login(ireq)
    except grpc.RpcError as e:
        print(f'failed logging in: {e.details}')
    else:
        print("login successful")
        return res.token

#configure persistance and autoDir
def SetAgentConfig(persistance,autoDir,creds):
    print(" ")
    print("== setting persistence and autodir ==")
    print(" ")
    try:
        ireq = compiled_protos.platformapiv2_pb2.ConfigureAgentReq(
            agentID=agentDID,
            deviceFileDownloadConfig = compiled_protos.platformInternal_pb2.DeviceFileDownloadConfig(
                autoCreateDir=autoDir,
                enableStage=persistance
            )
        )
        res = pfv2_stub.ConfigureAgent(ireq,metadata=creds)
    except grpc.RpcError as e:
        print(f'failed setting persistence and autodir : {e.details}')
    else:
        print("persistence is set to True")
        print("autoDir is set to True")


# Get context token
def apit_context_with_token():
    # Get the token from the server (use your actual method here)
    token_from_server = Login()

    # Create metadata containing the authorization token
    metadata_with_token = (('authorization', f'{token_from_server}'),)

    # Return the credentials so it can be used to make gRPC calls
    return metadata_with_token

# Define the function to stream the requests
def generate_upload_requests(file_info,file_path):
    # Send file info as the first part of the request (e.g., metadata)
    yield compiled_protos.platformapi_pb2.UploadFilesReq(
        info=file_info,
        agentPath=pathonagent,
        userUploadPath=dirpath
    )
    
    # Open the file and send it as chunks
    with open(file_path, 'rb') as file:
        chunk_size = 1024  # Adjust chunk size as needed
        while chunk := file.read(chunk_size):
            # Send the chunk as part of the stream
            yield compiled_protos.platformapi_pb2.UploadFilesReq(
                chunkData=chunk,
                agentPath=pathonagent,
                userUploadPath=dirpath
            )

# Make the RPC call, passing the metadata with the context token
try:
    print("== Login ==")
    print(" ")
    creds = apit_context_with_token()

    SetAgentConfig(persist_on,autoDir_on,creds)
    #Iterate over each file in the dir and upload
    files=list_files_in_directory(dirpath)
    print(" ")
    print("== file upload starts ==")
    for file_path, file_name in files:
        print(" ")
        print(f" uploading file: {file_name}, at location: {file_path}")
        # Create the FileInfo object for metadata
        file_info = compiled_protos.platformapi_pb2.FileInfo(
            deviceIdentity=agentDID,  # Use the correct device identity
            fileId=file_name,
            fileType=os.path.splitext(file_name)[1]  # Extract the file extension (e.g., '.txt')
        )
        response = stub.UploadFiles(generate_upload_requests(file_info,file_path),metadata=creds)
        if response.result == True:
            print(f" file:  {file_name}, is successfully uploaded")
        else:
            print(" response: ", response)
    print(" ")
    print("== upload complete ==")
except grpc.RpcError as e:
    print(f"RPC failed with status code {e.code()}: {e.details()}")
    print("Error traceback:", e.debug_error_string())
