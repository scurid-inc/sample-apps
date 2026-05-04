#!/usr/bin/env python3

import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSReliabilityPolicy,
    QoSHistoryPolicy,
    QoSDurabilityPolicy,
)

from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleCommandAck,
    VehicleStatus,
)


class OffboardMode(Node):
    """PX4-facing node: handles OFFBOARD/ARM and forwards app-level setpoints."""

    def __init__(self):
        super().__init__("offboard_mode")

        qos_pub = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )
        qos_sub = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.declare_parameter("default_altitude", 5.0)
        self.default_altitude = float(self.get_parameter("default_altitude").value)

        self.nav_state = VehicleStatus.NAVIGATION_STATE_MAX
        self.arming_state = VehicleStatus.ARMING_STATE_DISARMED
        self.offboard_setpoint_counter = 0
        self.last_mode_arm_request_s = 0.0
        self.last_state_log_s = 0.0
        self.last_nav_state_logged = None
        self.last_arm_state_logged = None
        self.vehicle_status_received = False

        self.target_x = 0.0
        self.target_y = 0.0
        self.target_z_up = self.default_altitude

        self._subscriptions = []
        self._subscriptions.append(
            self.create_subscription(
                VehicleStatus,
                "/fmu/out/vehicle_status",
                self._vehicle_status_cb,
                qos_sub,
            )
        )
        self._subscriptions.append(
            self.create_subscription(
                VehicleStatus,
                "/fmu/out/vehicle_status_v2",
                self._vehicle_status_cb,
                qos_sub,
            )
        )
        self._subscriptions.append(
            self.create_subscription(
                VehicleCommandAck,
                "/fmu/out/vehicle_command_ack",
                self._vehicle_command_ack_cb,
                qos_sub,
            )
        )
        self._subscriptions.append(
            self.create_subscription(
                VehicleCommandAck,
                "/fmu/out/vehicle_command_ack_v1",
                self._vehicle_command_ack_cb,
                qos_sub,
            )
        )
        self._subscriptions.append(
            self.create_subscription(
                Point,
                "/offboard/position_setpoint",
                self._position_setpoint_cb,
                10,
            )
        )

        self.pub_offboard_mode = self.create_publisher(
            OffboardControlMode, "/fmu/in/offboard_control_mode", qos_pub
        )
        self.pub_trajectory = self.create_publisher(
            TrajectorySetpoint, "/fmu/in/trajectory_setpoint", qos_pub
        )
        self.pub_vehicle_cmd = self.create_publisher(
            VehicleCommand, "/fmu/in/vehicle_command", qos_pub
        )

        self.dt = 0.02
        self.timer = self.create_timer(self.dt, self._cmdloop_cb)

        self.get_logger().info(
            f"OffboardMode started (default_altitude={self.default_altitude} m)"
        )

    def _vehicle_status_cb(self, msg: VehicleStatus):
        self.vehicle_status_received = True
        self.nav_state = msg.nav_state
        self.arming_state = msg.arming_state

    def _position_setpoint_cb(self, msg: Point):
        self.target_x = float(msg.x)
        self.target_y = float(msg.y)
        self.target_z_up = max(0.5, float(msg.z))

    def _vehicle_command_ack_cb(self, msg: VehicleCommandAck):
        tracked_commands = {
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE: "DO_SET_MODE",
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM: "ARM_DISARM",
        }
        if msg.command not in tracked_commands:
            return

        result_names = {}
        for constant_name in dir(VehicleCommandAck):
            if not constant_name.startswith("VEHICLE_CMD_RESULT_"):
                continue
            value = getattr(VehicleCommandAck, constant_name)
            result_names[value] = constant_name.replace("VEHICLE_CMD_RESULT_", "")

        command_name = tracked_commands[msg.command]
        result_name = result_names.get(msg.result, str(msg.result))
        self.get_logger().info(f"ACK: {command_name} -> {result_name}")

    @staticmethod
    def _nav_state_name(nav_state: int) -> str:
        names = {}
        for constant_name in dir(VehicleStatus):
            if not constant_name.startswith("NAVIGATION_STATE_"):
                continue
            value = getattr(VehicleStatus, constant_name)
            names[value] = constant_name.replace("NAVIGATION_STATE_", "")
        return names.get(nav_state, f"UNKNOWN({nav_state})")

    @staticmethod
    def _arm_state_name(arm_state: int) -> str:
        names = {}
        for constant_name in dir(VehicleStatus):
            if not constant_name.startswith("ARMING_STATE_"):
                continue
            value = getattr(VehicleStatus, constant_name)
            names[value] = constant_name.replace("ARMING_STATE_", "")
        return names.get(arm_state, f"UNKNOWN({arm_state})")

    def _cmdloop_cb(self):
        now_us = int(self.get_clock().now().nanoseconds / 1000)
        now_s = now_us / 1e6

        if not self.vehicle_status_received and (now_s - self.last_state_log_s) >= 1.0:
            self.last_state_log_s = now_s
            self.get_logger().warn("Waiting for PX4 vehicle status topic...")

        offboard_msg = OffboardControlMode()
        offboard_msg.timestamp = now_us
        offboard_msg.position = True
        offboard_msg.velocity = False
        offboard_msg.acceleration = False
        self.pub_offboard_mode.publish(offboard_msg)

        is_offboard = self.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        is_armed = self.arming_state == VehicleStatus.ARMING_STATE_ARMED

        if self.vehicle_status_received and (
            self.nav_state != self.last_nav_state_logged
            or self.arming_state != self.last_arm_state_logged
        ):
            self.last_nav_state_logged = self.nav_state
            self.last_arm_state_logged = self.arming_state
            self.get_logger().info(
                f"State: nav={self._nav_state_name(self.nav_state)} arm={self._arm_state_name(self.arming_state)}"
            )

        if (
            self.offboard_setpoint_counter >= 50
            and (not is_offboard or not is_armed)
            and (now_s - self.last_mode_arm_request_s) >= 0.5
        ):
            self._publish_vehicle_command(
                VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0, 6.0
            )
            self._publish_vehicle_command(
                VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0
            )
            self.last_mode_arm_request_s = now_s
            self.get_logger().info("Requested OFFBOARD mode + ARM")

        traj = TrajectorySetpoint()
        traj.timestamp = now_us
        traj.position[0] = self.target_x
        traj.position[1] = self.target_y
        traj.position[2] = -self.target_z_up
        self.pub_trajectory.publish(traj)

        if self.offboard_setpoint_counter <= 50:
            self.offboard_setpoint_counter += 1

    def _publish_vehicle_command(self, command, param1=0.0, param2=0.0):
        msg = VehicleCommand()
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        msg.param1 = param1
        msg.param2 = param2
        msg.command = command
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        self.pub_vehicle_cmd.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = OffboardMode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
