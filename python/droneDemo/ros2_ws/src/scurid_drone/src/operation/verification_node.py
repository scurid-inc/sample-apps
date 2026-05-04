#!/usr/bin/env python3

import sys
import json
import shutil
import textwrap
from pathlib import Path
from datetime import datetime

import grpc
import rclpy                                # type: ignore
from std_msgs.msg import ByteMultiArray     # type: ignore
from geometry_msgs.msg import PoseStamped   # type: ignore

import pb2.edgeagent_pb2 as ep              # type: ignore
import pb2.edgeagent_pb2_grpc as epg        # type: ignore
from scurid_utils.did_node import DIDNode   # type: ignore


class VerificationNode(DIDNode):
    def __init__(self):
        super().__init__('verification_node')

        self.channel = grpc.insecure_channel('localhost:4040')
        self.stub = epg.ScuridEdgeAgentAPIStub(self.channel)

        self.subscription = self.create_subscription(
            ByteMultiArray,
            '/secure_cmd',
            self.listener_callback,
            10
        )

        self.pose_publisher = self.create_publisher(
            PoseStamped,
            "/scurid_drone/relative_pose_cmd",
            10
        )

        self.latest_timestamp = "Never"
        self.latest_status = "Waiting for command"
        self.latest_result = "-"
        self.latest_payload = "-"
        self.latest_signature = "-"
        self.latest_did = "-"
        self.latest_color = ""

        self.ui_timer = self.create_timer(1.0, self._render_ui)
        
        # Communication with Autonomous Edge
        self.rejected_command_log = Path("../scurid_rejected_commands.jsonl")

        self.get_logger().info("Verification Node started")

    def _timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _fit(self, text, width):
        text = str(text)
        if width <= 0:
            return ""
        if len(text) <= width:
            return text
        if width <= 3:
            return text[:width]
        return text[:width - 3] + "..."

    def _wrap(self, text, width):
        if not text:
            return [""]
        return textwrap.wrap(
            str(text),
            width=max(1, width),
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=False
        ) or [""]

    # Communication with Autonomous Edge
    def _emit_rejected_command_event(self, payload, signature, did, reason):
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "command_rejected",
            "reason": str(reason),
            "payload": payload,
            "signature": str(signature),
            "did": str(did),
        }

        try:
            with open(self.rejected_command_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, separators=(",", ":")) + "\n")
        except Exception:
            pass

    def _render_ui(self):
        cols, rows = shutil.get_terminal_size(fallback=(80, 24))
        width = max(20, cols - 2)

        reset = "\033[0m"
        red = "\033[31m"
        green = "\033[32m"

        payload_lines = self._wrap(self.latest_payload, width)
        signature_lines = self._wrap(self.latest_signature, width)
        did_lines = self._wrap(self.latest_did, width)

        status_value = self.latest_status
        result_value = self.latest_result

        if self.latest_color == "green":
            status_value = f"{green}{status_value}{reset}"
            result_value = f"{green}{result_value}{reset}"
        elif self.latest_color == "red":
            status_value = f"{red}{status_value}{reset}"
            result_value = f"{red}{result_value}{reset}"

        lines = [
            "VERIFICATION NODE",
            "-" * min(width, 60),
            f"Timestamp       {self._timestamp()}",
            f"Last command    {self.latest_timestamp}",
            f"Status          {status_value}",
            f"Result          {result_value}",
            "",
            "Payload",
            *payload_lines,
            "",
            "Signature",
            *signature_lines,
            "",
            "DID",
            *did_lines,
        ]

        visible = []
        for line in lines[:max(1, rows - 1)]:
            visible.append(self._fit(line, width))

        frame = "\n".join(visible)

        sys.stdout.write("\033[2J\033[H" + frame + "\n")
        sys.stdout.flush()

    def _set_ui(self, status, result, payload=None, signature=None, did=None, color=""):
        self.latest_timestamp = self._timestamp()
        self.latest_status = status
        self.latest_result = result
        self.latest_color = color

        if payload is not None:
            self.latest_payload = json.dumps(payload, separators=(", ", ": "))

        if signature is not None:
            self.latest_signature = str(signature)

        if did is not None:
            self.latest_did = str(did)

        self._render_ui()

    def verify(self, protected_data):
        try:
            data = json.loads(protected_data.decode("utf-8"))
        except Exception:
            return None, False, None, None, "Invalid JSON"

        signature = data["signature"]
        payload = data["payload"]
        signer_did = data["DID"]

        try:
            use_scurid = data["use_scurid"]
            if not use_scurid:
                return payload, True, signature, signer_did, "VALID SIGNATURE"
        except:  # noqa: E722
            pass

        payload_bytes = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":")
        ).encode("utf-8")

        try:
            req = self.stub.VerifySignature(
                ep.VerifySignatureReq(
                    signature=signature,
                    payload=payload_bytes,
                    did=signer_did
                )
            )

            if req.isValid:
                return payload, True, signature, signer_did, "VALID SIGNATURE"

            return payload, False, signature, signer_did, "Signature is not valid. Wrong Signer"

        except grpc.RpcError as e:
            details = e.details() if e.details() else "Verification RPC failed"
            return payload, False, signature, signer_did, details

    def publish_pose_command(self, cmd: dict):
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

    def listener_callback(self, msg):
        protected_data = b"".join(msg.data)

        verified_data, req, signature, signer_did, result = self.verify(protected_data)

        if not req:
            self._set_ui(
                "Command rejected",
                result,
                payload=verified_data,
                signature=signature,
                did=signer_did,
                color="red"
            )

            self._emit_rejected_command_event(
                payload=verified_data,
                signature=signature,
                did=signer_did,
                reason=result,
            )

            return

        self.publish_pose_command(verified_data)

        self._set_ui(
            "Command accepted",
            result,
            payload=verified_data,
            signature=signature,
            did=signer_did,
            color="green"
        )


def main(args=None):
    rclpy.init(args=args)

    node = VerificationNode()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
