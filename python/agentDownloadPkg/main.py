# Demo Application showing Download functionality by edge agent

import edgeagent_pb2
import edgeagent_pb2_grpc
import grpc

addr = 'localhost:4040'  # update the server and port accordingly
channel = grpc.insecure_channel(addr)  # starting a local only channel
stub = edgeagent_pb2_grpc.ScuridEdgeAgentAPIStub(channel)  # grpc client

def downloadpkg():
    try:
        param1 = 'did:scurid:0x7b781C2fba42fE0CD5Ef979Fa579Cd6A4c0Ffbc3' #approved identity
        param2 = '/Users/roshan/Downloads/sample-apps/python/agentDownloadPkg/downloads' #full path where the file needs to be stored
        ireq = edgeagent_pb2.DownloadFilesReq(identity=param1,path=param2)
        req = stub.DownloadFiles(ireq)
    except grpc.RpcError as e:
        print(f'failed setting: {e.details}')
    else:
        print(req)

if __name__ == '__main__':
    downloadpkg()
