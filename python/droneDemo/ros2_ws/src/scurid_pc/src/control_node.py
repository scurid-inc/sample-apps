#!/usr/bin/env python3

import json
import threading
from datetime import datetime
import shutil
import textwrap

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

        # UI state
        self.latest_status = "No command sent yet."
        self.latest_packet = "No packet sent yet."
        self._ui_lock = threading.Lock()

        self.get_logger().info("Testing! Control Node started!")

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _format_command(self, command) -> str:
        bold = "\033[1m"
        reset = "\033[0m"
        if isinstance(command, dict):
            return f"{bold}{json.dumps(command, separators=(', ', ': '))}{reset}"
        return f"{bold}{str(command)}{reset}"

    def _format_packet(self, packet) -> str:
        bold = "\033[1m"
        reset = "\033[0m"

        # Only bold the payload part
        payload_str = json.dumps(packet["payload"], separators=(", ", ": "))
        signature = packet["signature"]
        did = packet["DID"]

        return (
            '{'
            f'"payload": {bold}{payload_str}{reset}, '
            f'"signature": "{signature}", '
            f'"DID": "{did}"'
            '}'
        )

    def _wrap_line(self, text: str, width: int):
        if width <= 1:
            return [text[:width]] if text else [""]
        if text == "":
            return [""]
        return textwrap.wrap(
            text,
            width=width,
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=False
        ) or [""]

    def _fit_lines(self, lines, width: int):
        wrapped = []
        for line in lines:
            wrapped.extend(self._wrap_line(str(line), width))
        return wrapped

    def _set_status(self, title: str, body: str, packet: str = None):
        with self._ui_lock:
            ts = self._timestamp()

            # Only print timestamp + command (no extra "Command sent:" line)
            if body:
                self.latest_status = f"[{ts}] {body}"
            else:
                self.latest_status = f"[{ts}]"

            if packet is not None:
                self.latest_packet = packet

            self._render_ui()

    def _render_ui(self):
        cols, rows = shutil.get_terminal_size(fallback=(80, 24))
        content_width = max(10, cols - 2)

        menu_lines = [
            # " DRONE CONTROL ",
            "1  Move forward            [dx   =   3.0 m]",
            "2  Move backward           [dx   =  -3.0 m]",
            "3  Move left               [dy   =  -3.0 m]",
            "4  Move right              [dy   =   3.0 m]",
            "5  Move up                 [dz   =  -1.5 m]",
            "6  Move down               [dz   =   1.5 m]",
            "7  Rotate left             [dyaw =  -1.0]",
            "8  Rotate right            [dyaw =   1.0]",
            "10 Arm",
            "11 Land",
            "12 Return to start position",
        ]

        status_lines = [
            "########## LATEST SENT COMMAND ##########",
            *self.latest_status.splitlines()
        ]

        packet_lines = [
            "########## LATEST SIGNED PACKET ##########",
            self.latest_packet
        ]

        menu_lines = self._fit_lines(menu_lines, content_width)
        status_lines = self._fit_lines(status_lines, content_width)
        packet_lines = self._fit_lines(packet_lines, content_width)

        prompt_line = "Select command: "

        fixed_lines = len(menu_lines) + 1 + len(status_lines) + 1 + len(packet_lines) + 1
        blank_lines = max(0, rows - fixed_lines)

        screen_lines = []
        screen_lines.extend(menu_lines)
        screen_lines.append("")
        screen_lines.extend(status_lines)
        screen_lines.append("")
        screen_lines.extend(packet_lines)
        screen_lines.extend([""] * blank_lines)

        print("\033[2J\033[H", end="")

        for line in screen_lines[:max(0, rows - 1)]:
            print(line.ljust(content_width))

        print(prompt_line, end="", flush=True)

    def send_arming_command(self, command: str):
        """
        Arm/Disarms the drone.
        """
        msg = String()
        msg.data = command
        self.arming_publisher.publish(msg)
        self.get_logger().info(f"Sent arming command: {command}")
        self._set_status("Arming command sent", command)

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
            self._set_status("Signing failed", str(e.details()))
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
            return None, None

        # Create data packet
        packet = {
            "payload": payload,
            "signature": signed_cmd.signature,
            "DID": self.did
        }

        # Convert packet into bytes
        protected_data = json.dumps(packet, separators=(",", ":")).encode("utf-8")

        return protected_data, packet

    def send_command(self, command):
        """
        Publish the command.
        """
        if self.did is None:
            self.get_logger().warn("DID not available yet; command not sent")
            self._set_status("Command not sent", "DID not available yet.")
            return

        # Sign command
        protected_data, packet = self.sign(command)

        if protected_data is None:
            self.get_logger().warn("Protected data is None")
            self._set_status("Command not sent", "Protected data is None.")
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

        self._set_status(
            "Command sent:",
            self._format_command(command),
            self._format_packet(packet)
        )

    def run_ui(self):
        """
        Control UI.
        """
        while rclpy.ok():
            with self._ui_lock:
                self._render_ui()

            choice = input().strip()

            cmd = {
                "dx": 0.0,
                "dy": 0.0,
                "dz": 0.0,
                "dyaw": 0.0
            }

            if choice == "1":
                cmd["dx"] = 3
            elif choice == "2":
                cmd["dx"] = -3
            elif choice == "3":
                cmd["dy"] = -3
            elif choice == "4":
                cmd["dy"] = 3
            elif choice == "5":
                cmd["dz"] = -1.5
            elif choice == "6":
                cmd["dz"] = 1.5
            elif choice == "7":
                cmd["dyaw"] = -1.0
            elif choice == "8":
                cmd["dyaw"] = 1.0
            elif choice == "9":
                break
            elif choice == "10":
                self.send_arming_command("arm")
                continue
            # elif choice == "11":
            #     self.send_arming_command("disarm")
            #     continue
            elif choice == "11":
                self.send_arming_command("land")
                continue
            elif choice == "12":
                self.send_arming_command("home")
                continue
            else:
                self._set_status("Invalid option", f"Input: {choice}")
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
        rclpy.shutdown()  # Stop spin
        spin_thread.join(timeout=1.0)  # Avoid thread hanging
        node.destroy_node()  # Destroy node


if __name__ == '__main__':
    main()
