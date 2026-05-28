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

        self.normal_cmd = {
            "timestamp": "Never",
            "status": "Waiting for normal command",
            "result": "-",
            "payload": "-",
            "signature": "-",
            "did": "-",
            "color": "",
        }

        self.attack_cmd = {
            "timestamp": "Never",
            "status": "Waiting for malicious command",
            "result": "-",
            "payload": "-",
            "signature": "-",
            "did": "-",
            "color": "",
        }

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
        except Exception as e:
            sys.stderr.write(f"[verification_node] failed to write rejected command event: {e}\n")

    def _render_ui(self):
        cols, rows = shutil.get_terminal_size(fallback=(100, 30))
        width = max(20, cols - 2)

        lines = [
            "VERIFICATION NODE",
            f"Timestamp       {self._timestamp()}",
            "",
        ]

        lines.extend(
            self._render_command_block(
                "NORMAL / LEGITIMATE COMMAND",
                self.normal_cmd,
                width,
            )
        )

        lines.extend(
            self._render_command_block(
                "MALICIOUS / ATTACK COMMAND",
                self.attack_cmd,
                width,
            )
        )

        visible = []
        for line in lines[:max(1, rows - 1)]:
            visible.append(self._fit(line, width))

        frame = "\n".join(visible)

        sys.stdout.write("\033[2J\033[H" + frame + "\n")
        sys.stdout.flush()

    def _render_command_block(self, title, state, width):
        reset = "\033[0m"
        red = "\033[31m"
        green = "\033[32m"
        yellow = "\033[33m"

        status = state["status"]
        result = state["result"]

        if state["color"] == "green":
            status = f"{green}{status}{reset}"
            result = f"{green}{result}{reset}"
        elif state["color"] == "red":
            status = f"{red}{status}{reset}"
            result = f"{red}{result}{reset}"
        elif state["color"] == "yellow":
            status = f"{yellow}{status}{reset}"
            result = f"{yellow}{result}{reset}"

        lines = [
            title,
            "-" * min(width, 60),
            f"Last command    {state['timestamp']}",
            f"Status          {status}",
            f"Result          {result}",
            "",
            "Payload",
            *self._wrap(state["payload"], width),
            "",
            "Signature",
            *self._wrap(state["signature"], width),
            "",
            "DID",
            *self._wrap(state["did"], width),
            "",
        ]

        return lines

    def _set_ui(self, target, status, result, payload=None, signature=None, did=None, color=""):
        state = self.attack_cmd if target == "attack" else self.normal_cmd

        state["timestamp"] = self._timestamp()
        state["status"] = status
        state["result"] = result
        state["color"] = color

        if payload is not None:
            state["payload"] = json.dumps(payload, separators=(", ", ": "))

        if signature is not None:
            state["signature"] = str(signature)

        if did is not None:
            state["did"] = str(did)

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

        try:
            raw_packet = json.loads(protected_data.decode("utf-8"))
        except Exception:
            raw_packet = {}

        is_attack = "use_scurid" in raw_packet

        verified_data, req, signature, signer_did, result = self.verify(protected_data)

        target = "attack" if is_attack or not req else "normal"

        if not req:
            self._set_ui(
                target,
                "Command rejected",
                result,
                payload=verified_data,
                signature=signature,
                did=signer_did,
                color="red",
            )

            self._emit_rejected_command_event(
                payload=verified_data,
                signature=signature,
                did=signer_did,
                reason=result,
            )

            return

        self.publish_pose_command(verified_data)

        if target == "attack":
            status = "Malicious command accepted"
            color = "yellow"
        else:
            status = "Command accepted"
            color = "green"

        self._set_ui(
            target,
            status,
            result,
            payload=verified_data,
            signature=signature,
            did=signer_did,
            color=color,
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
