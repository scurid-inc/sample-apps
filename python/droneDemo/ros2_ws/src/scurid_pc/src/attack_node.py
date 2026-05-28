#!/usr/bin/env python3

import json
import threading
from datetime import datetime
import shutil
import textwrap

import rclpy                                # type: ignore
from rclpy.node import Node                 # type: ignore
from std_msgs.msg import ByteMultiArray     # type: ignore

class AttackSimulatorNode(Node):
    """
    Node used to inject spoofed or tampered messages into the control stream.
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

        # UI state
        self.last_observed_str = "No message observed yet."
        self.last_sent_str = "No attack sent yet."
        self._ui_lock = threading.Lock()

        self.get_logger().info("Attack Simulator Node started")

    # ---------- UI HELPERS ----------

    def _timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _wrap_line(self, text, width):
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

    def _fit_lines(self, lines, width):
        wrapped = []
        for line in lines:
            wrapped.extend(self._wrap_line(line, width))
        return wrapped

    def _format_packet_with_bold_payload(self, packet):
        bold = "\033[1m"
        reset = "\033[0m"

        payload_str = json.dumps(packet.get("payload", {}), separators=(", ", ": "))
        signature = packet.get("signature", "-")
        did = packet.get("DID", "-")

        extra = ""
        if "use_scurid" in packet:
            extra = f', "use_scurid": {json.dumps(packet["use_scurid"])}'

        return (
            '{'
            f'"payload": {bold}{payload_str}{reset}, '
            f'"signature": "{signature}", '
            f'"DID": "{did}"'
            f'{extra}'
            '}'
        )

    def _set_observed(self, packet):
        with self._ui_lock:
            ts = self._timestamp()
            formatted = self._format_packet_with_bold_payload(packet)
            self.last_observed_str = f"[{ts}] {formatted}"
            self._render_ui()

    def _set_sent(self, title, packet):
        with self._ui_lock:
            ts = self._timestamp()
            formatted = self._format_packet_with_bold_payload(packet)
            self.last_sent_str = f"[{ts}] {title}\n{formatted}"
            self._render_ui()

    def _render_ui(self):
        cols, rows = shutil.get_terminal_size(fallback=(80, 24))
        width = max(10, cols - 2)

        menu = [
            "1  Send spoofed command",
            "2  Send tampered command",
            "3  Send spoofed command WITHOUT Scurid",
            "4  Send tampered command WITHOUT Scurid",
            "9  Quit",
        ]

        observed = [
            "########## LAST OBSERVED COMMAND ##########",
            "",
            *self.last_observed_str.splitlines()
        ]

        sent = [
            "########## LAST ATTACK SENT ##########",
            "",
            *self.last_sent_str.splitlines()
        ]

        menu = self._fit_lines(menu, width)
        observed = self._fit_lines(observed, width)
        sent = self._fit_lines(sent, width)

        prompt = "Select attack: "

        fixed = len(menu) + 1 + len(observed) + 1 + len(sent) + 1
        blanks = max(0, rows - fixed)

        lines = []
        lines.extend(menu)
        lines.append("")
        lines.extend(observed)
        lines.append("")
        lines.extend(sent)
        lines.extend([""] * blanks)

        print("\033[2J\033[H", end="")

        for line in lines[:max(0, rows - 1)]:
            print(line.ljust(width))

        print(prompt, end="", flush=True)

    # ---------- ROS CALLBACK ----------

    def listener_callback(self, msg):
        """
        Store the last observed protected packet exactly as received.
        """
        # Reconstruct the original bytes object
        self.last_message = b''.join(msg.data)
        packet = json.loads(self.last_message.decode("utf-8"))

        self.get_logger().info("Stored last observed message")
        self._set_observed(packet)

    # ---------- ATTACK METHODS ----------

    def publish_bytes(self, data_bytes):
        """
        Publish raw bytes in the same ByteMultiArray format as the other nodes.
        """
        msg = ByteMultiArray()
        msg.data = [bytes([b]) for b in data_bytes]
        self.publisher.publish(msg)

    def send_spoofed_command(self, use_scurid=True):
        if self.last_message is None:
            self._set_sent("Error", {"reason": "No message stored yet"})
            return

        packet = json.loads(self.last_message.decode("utf-8"))

        signer_did = packet["DID"]

        # Create a spoofed packet with a random signature
        spoofed_packet = {
            "payload": {
                "dx": 1.0,
                "dy": 0.0,
                "dz": -2.0,
                "dyaw": 0.0
            },
            "signature": "0x546c65719c6c48f4e5f214ded11d171cd6d6ee97f5c889d2e573d4c5832e3e4936d02fe1b1c3a608c0257e29bb5ae613c2e83bb74f61fcfd94e4853d4d305c2b1b",
            "DID": signer_did,
            "use_scurid": use_scurid
        }

        # Convert to bytes
        protected_data = json.dumps(
            spoofed_packet,
            separators=(",", ":")
        ).encode("utf-8")

        # Publish spoofed packet
        self.publish_bytes(protected_data)
        self.get_logger().info("Sent spoofed packet")

        title = "Spoofed packet" if use_scurid else "Spoofed packet WITHOUT Scurid"
        self._set_sent(title, spoofed_packet)

    def send_tampered_command(self, use_scurid=True):
        if self.last_message is None:
            self._set_sent("Error", {"reason": "No message stored yet"})
            return

        try:
            # Convert to dict
            packet = json.loads(self.last_message.decode("utf-8"))

            packet["payload"]["dz"] = -3
            packet["use_scurid"] = use_scurid

            # Convert back to bytes
            tampered_bytes = json.dumps(
                packet,
                separators=(",", ":")
            ).encode("utf-8")

            # Publish tampered data
            self.publish_bytes(tampered_bytes)
            self.get_logger().info("Sent tampered packet")

            title = "Tampered packet" if use_scurid else "Tampered packet WITHOUT Scurid"
            self._set_sent(title, packet)

        except Exception as e:
            self.get_logger().error(f"Failed to tamper with packet: {e}")
            self._set_sent("Error", {"exception": str(e)})

    # ---------- UI LOOP ----------

    def run_ui(self):
        while rclpy.ok():
            with self._ui_lock:
                self._render_ui()

            choice = input().strip()

            if choice == "1":
                self.send_spoofed_command(True)
            elif choice == "2":
                self.send_tampered_command(True)
            elif choice == "3":
                self.send_spoofed_command(False)
            elif choice == "4":
                self.send_tampered_command(False)
            elif choice == "9":
                break
            else:
                with self._ui_lock:
                    self.last_sent_str = f"[{self._timestamp()}] Invalid option: {choice}"
                    self._render_ui()


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
        rclpy.shutdown()
        spin_thread.join(timeout=1.0)
        node.destroy_node()


if __name__ == '__main__':
    main()
