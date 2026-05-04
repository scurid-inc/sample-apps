#!/usr/bin/env python3

import json

import grpc
import rclpy                                # type: ignore
from std_msgs.msg import ByteMultiArray     # type: ignore
from geometry_msgs.msg import PoseStamped   # type: ignore

import pb2.edgeagent_pb2 as ep              # type: ignore
import pb2.edgeagent_pb2_grpc as epg        # type: ignore
from scurid_utils.did_node import DIDNode   # type: ignore


class DroneTelemetryNode(DIDNode):
    """
    Telemetry sender running on the drone.
    It receives telemetry data from "the bridge", signs it, and publishes the protected data.
    """
    def __init__(self):
        # Initialize the base DIDNode, which also initializes the ROS node
        super().__init__('drone_telem_node')

        self.prev_cpu_total = None
        self.prev_cpu_idle = None

        # Rough board power model for LattePanda companion
        self.idle_power_w = 6.0
        self.max_power_w = 12.0

        # Connect to agent
        self.channel = grpc.insecure_channel('localhost:4040') # Agent address:port
        self.stub = epg.ScuridEdgeAgentAPIStub(self.channel)

        # Timing: publish/sign at fixed max frequency
        self.publish_frequency = 1.0  # Hz
        self.publish_period = 1.0 / self.publish_frequency
        self.last_publish_time = 0.0

        # Subscriber
        self.subscriber = self.create_subscription(
            PoseStamped,
            "/scurid_drone/output_pos",
            self.listener_callback,
            10
        )

        # Publisher
        self.publisher = self.create_publisher(
            ByteMultiArray,
            '/telemetry_out',
            10
        )

        self.get_logger().info("Drone telemetry node started!")

    def signwithidentity(self, payload):
        """
        Call Scurid API.
        """
        try:
            ireq = ep.SignWithIdentityReq(payload=payload, did=self.did)
            req = self.stub.SignWithIdentity(ireq)
            return req
        except grpc.RpcError as e:
            self.get_logger().error(f'signwithidentity failed: {e.details()}')
            return None        

    def read_cpu_times(self):
        """
        Read aggregate CPU times from /proc/stat.
        Returns (total, idle)
        """
        with open("/proc/stat", "r") as f:
            first = f.readline().strip()

        parts = first.split()
        if parts[0] != "cpu":
            raise RuntimeError("Could not read /proc/stat cpu line")

        values = [int(x) for x in parts[1:]]
        idle = values[3] + values[4]   # idle + iowait
        total = sum(values)
        return total, idle

    def estimate_companion_power_w(self):
        """
        Rough linear estimate based on CPU utilization.
        """
        try:
            total, idle = self.read_cpu_times()

            if self.prev_cpu_total is None:
                self.prev_cpu_total = total
                self.prev_cpu_idle = idle
                return None

            d_total = total - self.prev_cpu_total
            d_idle = idle - self.prev_cpu_idle

            self.prev_cpu_total = total
            self.prev_cpu_idle = idle

            if d_total <= 0:
                return None

            cpu_usage = 1.0 - (d_idle / d_total)
            cpu_usage = max(0.0, min(1.0, cpu_usage))

            power_w = self.idle_power_w + cpu_usage * (self.max_power_w - self.idle_power_w)
            return round(power_w, 2)

        except Exception as e:
            self.get_logger().warn(f"Failed estimating companion power: {e}")
            return None

    def pose_to_dict(self, msg: PoseStamped) -> dict:
        """
        Convert PoseStamped into a JSON-serializable dict.
        """
        return {
            "header": {
                "stamp": {
                    "sec": int(msg.header.stamp.sec),
                    "nanosec": int(msg.header.stamp.nanosec),
                },
                "frame_id": msg.header.frame_id,
            },
            "pose": {
                "position": {
                    "x": float(msg.pose.position.x),
                    "y": float(msg.pose.position.y),
                    "z": float(msg.pose.position.z),
                },
                "orientation": {
                    "x": float(msg.pose.orientation.x),
                    "y": float(msg.pose.orientation.y),
                    "z": float(msg.pose.orientation.z),
                    "w": float(msg.pose.orientation.w),
                },
            },
        }

    def sign(self, telem_data):
        """
        Signs the data using Scurid API
        """
        # Check for DID
        if self.did is None:
            self.get_logger().warn("DID not available yet; command not signed")
            return

        # Copy the payload
        payload = dict(telem_data)

        # Convert to bytes object
        payload_bytes = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":")
        ).encode("utf-8")
        
        # Sign the bytes/data
        signed_cmd = self.signwithidentity(payload_bytes)

        if signed_cmd is None:
            return None

        # Create data packet
        packet = {
            "payload": payload,
            "signature": signed_cmd.signature,
            "DID": self.did
        }

        # Convert entire packet into bytes
        protected_telem_data = json.dumps(packet, separators=(",", ":")).encode("utf-8")
        
        return protected_telem_data

    def listener_callback(self, msg):
        """
        Runs when a telemetry message is received.
        It signs the message and republishes it. 
        """
        current_time = self.get_clock().now().nanoseconds / 1e9

        if current_time - self.last_publish_time < self.publish_period:
            return

        self.last_publish_time = current_time

        # Convert to dict
        telem_data = self.pose_to_dict(msg)

        # Add companien computer info
        power_w = self.estimate_companion_power_w()
        comp = {}
        if power_w is not None:
            comp["estimated_power_w"] = power_w

        if comp:
            telem_data["companion_computer"] = comp

        # Sign
        signed_telem_data = self.sign(telem_data)

        if signed_telem_data is None:
            self.get_logger().info("None")
            return

        # Create and publish the signed telemetry data as a ByteMultiArray
        out_msg = ByteMultiArray()
        out_msg.data = [bytes([b]) for b in signed_telem_data]
        self.publisher.publish(out_msg)

        self.get_logger().info(f"Published signed telemetry data: {signed_telem_data}")

def main(args=None):
    # Initialize the ROS 2 Python client library
    rclpy.init(args=args)

    # Initialize node
    node = DroneTelemetryNode()

    # Spin/start node, and handle shutdown
    try:
        rclpy.spin(node)
    finally:
        rclpy.shutdown()
        node.destroy_node()

if __name__ == '__main__':
    main()