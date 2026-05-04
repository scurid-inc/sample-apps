#!/usr/bin/env python3

import sys
import json
import shutil
from datetime import datetime

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
        self.channel = grpc.insecure_channel('localhost:4040')
        self.stub = epg.ScuridEdgeAgentAPIStub(self.channel)

        # Subscriber
        self.subscriber = self.create_subscription(ByteMultiArray,
                                                   '/telemetry_out',
                                                   self.listener_callback, 10)

        # UI state
        self.latest_status = "Waiting for telemetry"
        self.last_update_time = "Never"
        self.telemetry = None

        # Redraw once per second
        self.ui_timer = self.create_timer(1.0, self._render_ui)

        self.get_logger().info("PC telemetry node started")

    def _timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _safe_float(self, value, decimals=2):
        try:
            return f"{float(value):.{decimals}f}"
        except Exception:
            return "-"

    def _fit(self, text, width):
        text = str(text)
        if width <= 0:
            return ""
        if len(text) <= width:
            return text
        if width <= 3:
            return text[:width]
        return text[:width - 3] + "..."

    def _sep(self, width):
        return "-" * max(8, width)

    def _render_ui(self):
        # pass
        cols, rows = shutil.get_terminal_size(fallback=(80, 18))
        width = max(20, cols)

        now = self._timestamp()

        if self.telemetry is None:
            frame_id = "-"
            stamp = "-"
            pos_x = pos_y = pos_z = "-"
            ori_x = ori_y = ori_z = ori_w = "-"
            power_draw = "-"
        else:
            header = self.telemetry["header"]
            pose = self.telemetry["pose"]
            pos = pose["position"]
            ori = pose["orientation"]

            frame_id = header["frame_id"]
            stamp = f"{header['stamp']['sec']}.{header['stamp']['nanosec']}"
            pos_x = self._safe_float(pos["x"], 2)
            pos_y = self._safe_float(pos["y"], 2)
            pos_z = self._safe_float(pos["z"], 2)
            ori_x = self._safe_float(ori["x"], 3)
            ori_y = self._safe_float(ori["y"], 3)
            ori_z = self._safe_float(ori["z"], 3)
            ori_w = self._safe_float(ori["w"], 3)
            comp = self.telemetry.get("companion_computer", {})
            power_draw = comp.get("estimated_power_w")

            if power_draw is None:
                power_draw = "-"

        lines = [
            self._fit("SCURID TELEMETRY RECEIVER", width),
            self._fit(f"Timestamp      {now}", width),
            self._fit(f"Status         {self.latest_status}", width),
            self._fit(f"Last telemetry {self.last_update_time}", width),
            self._fit(f"Frame          {frame_id}", width),
            self._fit(f"Stamp          {stamp}", width),
            self._fit(f"Position       x={pos_x}  y={pos_y}  z={pos_z}",
                      width),
            self._fit(
                f"Orientation    x={ori_x}  y={ori_y}  z={ori_z}  w={ori_w}",
                width),
            self._fit(f"Power draw     {power_draw}", width),
        ]

        visible_lines = [line[:cols] for line in lines[:max(1, rows - 1)]]
        frame = "\n".join(visible_lines)

        sys.stdout.write("\033[2J\033[H" + frame + "\n")
        sys.stdout.flush()

    def verify(self, protected_data):
        """
        Uses Scurid API to verify messages.
        """
        # Convert to dict
        data = json.loads(protected_data.decode("utf-8"))

        # Separate signature and payload
        signature = data["signature"]
        payload = data["payload"]
        signer_did = data["DID"]

        payload_bytes = json.dumps(payload,
                                   sort_keys=True,
                                   separators=(",", ":")).encode("utf-8")

        # Verify the payload
        try:
            req = self.stub.VerifySignature(
                ep.VerifySignatureReq(signature=signature,
                                      payload=payload_bytes,
                                      did=signer_did))
            return payload, req.isValid
        except grpc.RpcError as e:
            self.get_logger().error(f"VerifySignature failed: {e.details()}")

        return payload, False


    def format_data(self, data):
        header = data["header"]
        pose = data["pose"]

        formatted = {
            "stamp":
            json.dumps({
                "sec": header["stamp"]["sec"],
                "nanosec": header["stamp"]["nanosec"]
            }),
            "frame_id":
            header["frame_id"],
            "position":
            json.dumps(pose["position"]),
            "orientation":
            json.dumps(pose["orientation"]),
            "scurid_appliance_power_draw_w":
            str(data["companion_computer"]["estimated_power_w"])
        }

        return formatted

    def send_to_server(self, data):
        """
        Send data to Cockroach Database.
        """
        formatted_data = self.format_data(data)
        str_data = json.dumps(formatted_data)

        # Send data
        try:
            ireq = ep.SendDeviceDataWithCustomFieldsReq(agentDID=self.did, data=[str_data])
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
            self.latest_status = "Rejected telemetry"
            return

        # Send data to server/CDB
        self.send_to_server(verified_data)

        self.latest_status = "Telemetry OK"
        self.last_update_time = self._timestamp()
        self.telemetry = verified_data


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
