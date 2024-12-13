# Demo Application showing Download functionality by edge agent

import edgeagent_pb2
import edgeagent_pb2_grpc
import grpc
import calendar
import time,json
import sys

addr = 'localhost:4040'  # update the server and port accordingly, addr corresponds to an agent
channel = grpc.insecure_channel(addr)  # starting a local only channel
stub = edgeagent_pb2_grpc.ScuridEdgeAgentAPIStub(channel)  # grpc client

def sendData():
    try:
        if len(sys.argv) < 2:
            print(f'incomplete arguments, pass agentid')
            exit()

        msg = input("Enter your message: \t")
        
        ireq = edgeagent_pb2.SendDeviceDataWithCustomFieldsReq(agentDID=sys.argv[1],data=['{"msg":"'+str(msg)+'"}'])
        req = stub.SendDeviceDataWithCustomFields(ireq)
    except grpc.RpcError as e:
        print(f'failed setting: {e.details}')
    else:
        return req

if __name__ == '__main__':
    while(1):
        print(" ")
        print("1. Send Data")
        print("2. Exit")
        print(" ")
        choice = input('Select your operation ')
        print(" ")
        
        if choice == "1":
            print(sendData())
        if choice == "2":
            exit()

