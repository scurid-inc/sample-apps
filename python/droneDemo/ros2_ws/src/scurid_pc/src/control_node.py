#!/usr/bin/env python3

import json
import threading

import grpc
import rclpy                                        # type: ignore
from std_msgs.msg import ByteMultiArray, String     # type: ignore

import pb2.edgeagent_pb2 as ep                      # type: ignore
import pb2.edgeagent_pb2_grpc as epg                # type: ignore
from scurid_utils.did_node import DIDNode           # type: ignore

class ControlNode(DIDNode):
    """
    Node exposing a simple UI in a terminal and encrypts commands using Scurid.
    """
    def __init__(self):
        # Initialize the base DIDNode, which also initializes the ROS node
        super().__init__('control_node')

        # Connect to agent
        self.channel = grpc.insecure_channel('localhost:4040') # Agent address:port
        self.stub = epg.ScuridEdgeAgentAPIStub(self.channel)

        # Publisher
        self.publisher = self.create_publisher(
            ByteMultiArray,     # Message type
            '/secure_cmd',      # ROS topic name
            10                  # Queue size
        )

        # Publisher for the attack_node
        self.observe_publisher = self.create_publisher(
            ByteMultiArray,
            '/secure_cmd_observe',
            10
        )

        # Publisher for arming/disarming the drone
        self.arming_publisher = self.create_publisher(
            String,
            '/scurid_drone/arming',
            10
        )

        self.get_logger().info("Testing! Control Node started!")

    def send_arming_command(self, command: str):
        """
        Arm/Disarms the drone.
        """
        msg = String()
        msg.data = command
        self.arming_publisher.publish(msg)
        self.get_logger().info(f"Sent arming command: {command}")
    
    def signwithidentity(self, payload):
        """
        Call Scurid API.
        """
        try:
            ireq = ep.SignWithIdentityReq(payload=payload, did=self.did)
            req = self.stub.SignWithIdentity(ireq)
            return req
        except grpc.RpcError as e:
            self.get_logger().error(f"Signing failed: {e.details()}")
            return None

    def sign(self, command_dict):
        """
        Signs the data using Scurid API
        """
        # Copy the payload
        payload = dict(command_dict)

        # Convert to bytes object
        payload_bytes = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":")
        ).encode("utf-8")
        
        # Sign the bytes/data
        signed_cmd = self.signwithidentity(payload_bytes)

        if signed_cmd is None:
            self.get_logger().error("Signing failed; command not sent")
            return None

        # Create data packet
        packet = {
            "payload": payload,
            "signature": signed_cmd.signature
        }

        # Convert packet into bytes
        protected_data = json.dumps(packet, separators=(",", ":")).encode("utf-8")
        
        return protected_data

    def send_command(self, command):
        """
        Publish the command.
        """
        if self.did is None:
            self.get_logger().warn("DID not available yet; command not sent")
            return

        # Sign command
        protected_data = self.sign(command)

        if protected_data is None:
            self.get_logger().warn("Protected data is None")
            return

        # Create empty ROS message of type ByteMultiArray
        msg = ByteMultiArray()

        # Fill the message data with the bytes from the protected data.
        # I had to convert the single byte string (protected_data) into a sequence of 1-byte bytes objects
        # due to some mismatch between the Python bytes and the ROS 2 ByteMultiArray type. 
        msg.data = [bytes([b]) for b in protected_data]

        # Publish the message
        self.publisher.publish(msg)
        self.observe_publisher.publish(msg)

        self.get_logger().info(f"Sent command: {command}")

    def run_ui(self):
        """
        Control UI.
        """
        while rclpy.ok():

            print("\n--- Drone Control ---")
            print("1: Move forward")
            print("2: Move backward")
            print("3: Move left")
            print("4: Move right")
            print("5: Move up")
            print("6: Move down")
            print("7: Rotate left")
            print("8: Rotate right")
            print("9: Quit")
            print("10: Arm")
            print("11: Disarm")

            choice = input("Select command: ").strip()

            cmd = {
                "dx": 0.0,
                "dy": 0.0,
                "dz": 0.0,
                "dyaw": 0.0
            }

            if choice == "1":
                cmd["dx"] = 0.5
            elif choice == "2":
                cmd["dx"] = -0.5
            elif choice == "3":
                cmd["dy"] = 0.5
            elif choice == "4":
                cmd["dy"] = -0.5
            elif choice == "5":
                cmd["dz"] = 0.5
            elif choice == "6":
                cmd["dz"] = -0.5
            elif choice == "7":
                cmd["dyaw"] = 10.0
            elif choice == "8":
                cmd["dyaw"] = -10.0
            elif choice == "9":
                break
            elif choice == "10":
                self.send_arming_command("arm")
                continue
            elif choice == "11":
                self.send_arming_command("disarm")
                continue
            else:
                print("Invalid option")
                continue

            self.send_command(cmd)

def main(args=None):
    # Initialize the ROS 2 Python client library
    rclpy.init(args=args)

    # Initialize node
    node = ControlNode()

    # The node is spun in a thread because the UI is blocking the main thread
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    try:
        node.run_ui()
    finally:
        rclpy.shutdown() # Stop spin
        spin_thread.join(timeout=1.0) # Avoid thread hanging
        node.destroy_node() # Destroy node

if __name__ == '__main__':
    main()