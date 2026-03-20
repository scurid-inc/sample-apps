#!/usr/bin/env python3

import json

import grpc
import rclpy                                # type: ignore
from std_msgs.msg import ByteMultiArray     # type: ignore

import pb2.edgeagent_pb2 as ep              # type: ignore
import pb2.edgeagent_pb2_grpc as epg        # type: ignore
from scurid_utils.did_node import DIDNode   # type: ignore

class PCTelemetryNode(DIDNode):
    """
    Telemetry receiver running on PC.
    It receives and verifies signed telemetry messages from the drone.
    """
    def __init__(self):
        # Initialize the base DIDNode, which also initializes the ROS node
        super().__init__('pc_telem_node')

        # Connect to agent
        self.channel = grpc.insecure_channel('localhost:4040') # Agent address:port
        self.stub = epg.ScuridEdgeAgentAPIStub(self.channel)

        # Subscriber
        self.subscriber = self.create_subscription(
            ByteMultiArray,
            '/telemetry_out',
            self.listener_callback,
            10
        )

        self.get_logger().info("PC telemetry node started")

    def verify(self, protected_data):
        """
        Uses Scurid API to verify messages.
        """
        # Convert to dict
        data = json.loads(protected_data.decode("utf-8"))

        # Separate signature and payload
        signature = data["signature"]
        payload = data["payload"]

        # Recreate the exact bytes that were signed
        payload_bytes = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":")
        ).encode("utf-8")

        # Verify the payload
        try:
            req = self.stub.VerifySignature(
                ep.VerifySignatureReq(
                    signature=signature,
                    payload=payload_bytes,
                    did=self.did
                )
            )
            return payload, req.isValid
        except grpc.RpcError as e:
            self.get_logger().error(f"VerifySignature failed: {e.details()}")
        
        return payload, False


    def send_to_server(self, data):
        """
        Send data to Cockroach Database.        
        """
        # Convery data to JSON formatted string
        str_data = json.dumps(data) # todo Figure out the telemetry data structure and add a corresponding data schema

        # Send data
        try:
            ireq = ep.SendDeviceDataWithCustomFieldsReq(agentDID=self.did,data=[str_data]) 
            self.stub.SendDeviceDataWithCustomFields(ireq)
        except grpc.RpcError as e:
            print(f'Failed sending: {e.details}')

    def listener_callback(self, msg):
        """
        Runs when a protected telemetry message is received.
        It rebuilds the bytes and verifies the message.
        """
        # Rebuild original bytes
        protected_data = b"".join(msg.data)

        # Verify
        verified_data, req = self.verify(protected_data)

        # Check if it was accepted. Reject if not
        if not req:
            self.get_logger().error("Rejected command")
            return

        # Send data to server/CDB
        self.send_to_server(verified_data)

        self.get_logger().info(f"Verified data: {verified_data}")

def main(args=None):
    # Initialize the ROS 2 Python client library
    rclpy.init(args=args)

    # Create the ROS Node
    node = PCTelemetryNode()

    # Spin/start the Node, and handle shutdown
    try:
        rclpy.spin(node)
    finally:
        rclpy.shutdown()
        node.destroy_node()

if __name__ == '__main__':
    main()