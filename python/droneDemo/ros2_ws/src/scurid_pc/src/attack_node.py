#!/usr/bin/env python3

import json
import threading

import rclpy                                # type: ignore
from rclpy.node import Node                 # type: ignore
from std_msgs.msg import ByteMultiArray     # type: ignore

class AttackSimulatorNode(Node):
    """
    Node used to inject spoofed or tamperede messages into the control stream.
    """
    def __init__(self):
        # Initialize base ROS Node class
        super().__init__('attack_simulator_node')

        # Publisher
        self.publisher = self.create_publisher(
            ByteMultiArray,
            '/secure_cmd',
            10
        )

        # Subscriber
        self.subscription = self.create_subscription(
            ByteMultiArray,
            '/secure_cmd_observe',
            self.listener_callback,
            10
        )

        # Saving the last received message
        self.last_message = None

        self.get_logger().info("Attack Simulator Node started")

    def listener_callback(self, msg):
        """
        Store the last observed protected packet exactly as received.
        """
        # Reconstruct the original bytes object
        self.last_message = b''.join(msg.data)

        self.get_logger().info("Stored last observed message from /secure_cmd_observe")

    def publish_bytes(self, data_bytes):
        """
        Publish raw bytes in the same ByteMultiArray format as the other nodes.
        """
        msg = ByteMultiArray()
        msg.data = [bytes([b]) for b in data_bytes]
        self.publisher.publish(msg)

    def send_spoofed_command(self):
        """
        Inject a fake command packet with a random signature.
        This should be rejected by the verification.
        """
        # Create a spoofed packet with a random signature
        spoofed_packet = {
            "payload": {
                "dx": 1.0,
                "dy": 2.0,
                "dz": 3.0,
                "dyaw": 45.0
            },
            "signature": "0x546c65719c6c48f4e5f214ded11d171cd6d6ee97f5c889d2e573d4c5832e3e4936d02fe1b1c3a608c0257e29bb5ae613c2e83bb74f61fcfd94e4853d4d305c2b1b"
        }

        # Convert to bytes
        protected_data = json.dumps(
            spoofed_packet,
            separators=(",", ":")
        ).encode("utf-8")

        # Publish spoofed packet
        self.publish_bytes(protected_data)

        self.get_logger().info(f"Sent spoofed packet: {spoofed_packet}")

    # def send_replay_attack(self):
    #     """
    #     Replay the last valid observed protected packet exactly.
    #     This will likely succeed unless replay protection exists.
    #     """
    #     if self.last_message is None:
    #         self.get_logger().info("No message stored yet")
    #         return

    #     self.publish_bytes(self.last_message)
    #     self.get_logger().info("Replayed last observed message")

    def send_tampered_command(self):
        """
        Modify a valid observed packet without updating the signature.
        This should fail verification.
        """
        # Make sure it has a packet to tamper with
        if self.last_message is None:
            self.get_logger().info("No message stored yet")
            return

        try:
            # Convert to dict
            packet = json.loads(self.last_message.decode("utf-8"))

            # Change only the payload, keep the old signature
            packet["payload"]["dx"] = 9.9

            # Convert back to bytes
            tampered_bytes = json.dumps(
                packet,
                separators=(",", ":")
            ).encode("utf-8")

            # Publish tampered data
            self.publish_bytes(tampered_bytes)

            self.get_logger().info(f"Sent tampered packet: {packet}")
        except Exception as e:
            self.get_logger().error(f"Failed to tamper with packet: {e}")

    def run_ui(self):
        while rclpy.ok():
            print("\n--- Attack Simulator ---")
            print("1: Send spoofed command")
            print("2: Send tampered command")
            # print("3: Replay last command")
            print("9: Quit")

            choice = input("Select attack: ")

            if choice == "1":
                self.send_spoofed_command()
            elif choice == "2":
                self.send_tampered_command()
            # elif choice == "3":
                # self.send_replay_attack()
            elif choice == "9":
                break
            else:
                print("Invalid option")

def main(args=None):
    # Initialize the ROS 2 Python client library
    rclpy.init(args=args)

    # Initialize node
    node = AttackSimulatorNode()

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