#!/usr/bin/env python3

import json

import grpc
import rclpy                                # type: ignore
from std_msgs.msg import ByteMultiArray     # type: ignore
from geometry_msgs.msg import PoseStamped   # type: ignore

import pb2.edgeagent_pb2 as ep              # type: ignore
import pb2.edgeagent_pb2_grpc as epg        # type: ignore
from scurid_utils.did_node import DIDNode   # type: ignore

class VerificationNode(DIDNode):
    """
    Verification Node running on the drone.
    """
    def __init__(self):
        # Initialize the base DIDNode, which also initializes the ROS node
        super().__init__('verification_node')

        self.channel = grpc.insecure_channel('localhost:4040') # Agent address:port
        self.stub = epg.ScuridEdgeAgentAPIStub(self.channel)

        # Subscriber
        self.subscription = self.create_subscription(
            ByteMultiArray,          # Message type
            '/secure_cmd',           # Incoming ROS topic
            self.listener_callback,  # Callback on new message
            10                       # Queue size
        )

        # Publisher
        self.pose_publisher = self.create_publisher(
            PoseStamped,
            "/scurid_drone/relative_pose_cmd",
            10
        )

        self.get_logger().info("Verification Node started")

    def verify(self, protected_data):
        """
        Verify signed data using Scurid API.
        """
        # protected_data is bytes → decode before json.loads to a dict
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

        # Verify the payload using the signature
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
            self.get_logger().error(f"VerifySignature RPC failed: {e.details()}")
        
        return payload, False

    def publish_pose_command(self, cmd: dict):
        """
        Convert verified command dict into PoseStamped for main.py.
        Expected keys: dx, dy, dz, dyaw
        """
        pose_msg = PoseStamped()
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        pose_msg.header.frame_id = "base_link"

        pose_msg.pose.position.x = float(cmd.get("dx", 0.0))
        pose_msg.pose.position.y = float(cmd.get("dy", 0.0))
        pose_msg.pose.position.z = float(cmd.get("dz", 0.0))

        pose_msg.pose.orientation.x = 0.0
        pose_msg.pose.orientation.y = 0.0
        pose_msg.pose.orientation.z = float(cmd.get("dyaw", 0.0))
        pose_msg.pose.orientation.w = 1.0

        self.pose_publisher.publish(pose_msg)
        self.get_logger().info(f"Published verified pose command: {cmd}")


    def listener_callback(self, msg):
        """
        Runs when a protected command is received.
        Rebuilds bytes, verifies/decrypts, parses JSON, and republishes accepted commands.
        """

        # Rebuild original bytes
        protected_data = b"".join(msg.data)

        # Verify
        verified_data, req = self.verify(protected_data)

        # Check if it was accepted. Reject if not
        if not req:
            self.get_logger().error("Rejected command")
            return

        self.publish_pose_command(verified_data)

def main(args=None):
    # Initialize the ROS 2 Python client library
    rclpy.init(args=args)

    # Create the node
    node = VerificationNode()

    # Spin/start the node, and handle shutdown
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()








