#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scurid drone control — offboard position control via PoseStamped input.

Subscribes to /scurid_drone/relative_pose_cmd (PoseStamped) for desired
relative movement in the NED frame.  Publishes TrajectorySetpoint and
OffboardControlMode to PX4 via the DDS bridge (v1.16).

Author: Erik Winkler
Date: 13.03.2026
"""

###############################################
# Standard Imports                            #
###############################################
import math

###############################################
# ROS Imports                                 #
###############################################
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSReliabilityPolicy,
    QoSHistoryPolicy,
    QoSDurabilityPolicy,
)
from rclpy.executors import MultiThreadedExecutor

###############################################
# ROS Topic messages                          #
###############################################
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String

from px4_msgs.msg import (
    VehicleCommand,
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleStatus,
    VehicleLocalPosition,
    VehicleGlobalPosition,
    VehicleAttitude,
)


###############################################
# Main Control class                          #
###############################################


class ScuridDrone(Node):

    def __init__(self):
        super().__init__('scurid_drone')

        # ── QoS for PX4 DDS bridge ──────────────────────────────
        qos_profile_pub = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=0,
        )

        qos_profile_sub = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=0,
        )

        # ── Publishers ──────────────────────────────────────────
        self.publisher_offboard_mode = self.create_publisher(
            OffboardControlMode, '/fmu/in/offboard_control_mode', qos_profile_pub)
        self.publisher_trajectory = self.create_publisher(
            TrajectorySetpoint, '/fmu/in/trajectory_setpoint', qos_profile_pub)
        self.cmd_pub_px4 = self.create_publisher(
            VehicleCommand, '/fmu/in/vehicle_command', qos_profile_pub)

        # ── Subscribers (PX4) ───────────────────────────────────
        self.status_sub = self.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status',
            self.vehicle_status_callback, qos_profile_sub)

        self.local_pos_sub = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position',
            self.local_position_callback, qos_profile_sub)

        self.global_pos_sub = self.create_subscription(
            VehicleGlobalPosition, '/fmu/out/vehicle_global_position',
            self.global_pos_callback, qos_profile_sub)

        self.attitude_sub = self.create_subscription(
            VehicleAttitude, '/fmu/out/vehicle_attitude',
            self.attitude_callback, qos_profile_sub)

        # ── Subscriber (relative pose command) ──────────────────
        self.pose_cmd_sub = self.create_subscription(
            PoseStamped, '/scurid_drone/relative_pose_cmd',
            self.pose_cmd_callback, 10)

        # ── Subscriber (arming command from joystick) ───────────
        self.arming_sub = self.create_subscription(
            String, '/scurid_drone/arming',
            self.arming_callback, 10)

        # ── State variables ─────────────────────────────────────
        self.nav_state = VehicleStatus.NAVIGATION_STATE_MAX
        self.arming_state = VehicleStatus.ARMING_STATE_DISARMED

        # Current local NED position from PX4
        self.local_pos_ned = [0.0, 0.0, 0.0]   # x(N), y(E), z(D)
        self.current_yaw = 0.0                   # rad
        self.local_pos_valid = False

        # Desired setpoint (absolute NED), initialised on first position fix
        self.setpoint_ned = [float('nan')] * 3
        self.setpoint_yaw = float('nan')
        self.setpoint_initialised = False

        # ── Timer: publish offboard heartbeat + setpoint @ 20 Hz
        self.offboard_timer = self.create_timer(0.05, self.offboard_loop)

        self.get_logger().info('ScuridDrone node started — waiting for position fix …')

    # ─────────────────────────────────────────────────────────────
    # PX4 Callbacks
    # ─────────────────────────────────────────────────────────────

    def vehicle_status_callback(self, msg):
        self.nav_state = msg.nav_state
        self.arming_state = msg.arming_state

    def arming_callback(self, msg: String):
        """Handle arm/disarm commands from /scurid_drone/arming topic."""
        cmd = msg.data.strip().lower()
        if cmd == 'arm':
            self.get_logger().info('Arm requested via topic')
            self.send_vehicle_command(command=400, param1=1.0)   # ARM
        elif cmd == 'disarm':
            self.get_logger().info('Disarm requested via topic')
            self.send_vehicle_command(command=400, param1=0.0)   # DISARM
        else:
            self.get_logger().warn(f'Unknown arming command: "{msg.data}"')

    def local_position_callback(self, msg: VehicleLocalPosition):
        if msg.xy_valid and msg.z_valid:
            self.local_pos_ned = [msg.x, msg.y, msg.z]
            self.current_yaw = msg.heading
            self.local_pos_valid = True

            # Initialise setpoint to current position on first valid fix
            if not self.setpoint_initialised:
                self.setpoint_ned = [msg.x, msg.y, msg.z]
                self.setpoint_yaw = msg.heading
                self.setpoint_initialised = True
                self.get_logger().info(
                    f'Setpoint initialised to [{msg.x:.2f}, {msg.y:.2f}, {msg.z:.2f}] yaw={msg.heading:.2f}')

    def global_pos_callback(self, msg):
        pass  # placeholder — extend for GPS‑based logic / UTM conversion

    def attitude_callback(self, msg):
        pass  # placeholder — extend if quaternion attitude is needed

    # ─────────────────────────────────────────────────────────────
    # Relative pose command (from joystick_input or any other source)
    # ─────────────────────────────────────────────────────────────

    def pose_cmd_callback(self, msg: PoseStamped):
        """
        Interpret inbound PoseStamped as a *relative* body-frame offset:
          position.x  → body forward  (metres)
          position.y  → body right    (metres)
          position.z  → body down     (metres — negative = climb)

        The body-frame deltas are rotated into NED using the current
        heading before being added to the absolute setpoint.

        Yaw is taken from the quaternion z‑component as a simple
        Δyaw (rad) for convenience (single‑axis rotation around D).
        """
        self.get_logger().info('CONTROLLING DRONE!')
        if not self.setpoint_initialised:
            return


        dx_body = msg.pose.position.x   # body forward
        dy_body = msg.pose.position.y   # body right
        dz_body = msg.pose.position.z   # body down (negative = up)

        # Rotate body-frame XY into NED using current yaw
        cos_yaw = math.cos(self.current_yaw)
        sin_yaw = math.sin(self.current_yaw)
        dn = dx_body * cos_yaw - dy_body * sin_yaw   # North
        de = dx_body * sin_yaw + dy_body * cos_yaw   # East

        self.setpoint_ned[0] += dn
        self.setpoint_ned[1] += de
        self.setpoint_ned[2] += dz_body

        # Simple yaw delta from quaternion z component (small‑angle approx.)
        dyaw = msg.pose.orientation.z
        self.setpoint_yaw += dyaw
        # Wrap to [-π, π]
        self.setpoint_yaw = math.atan2(
            math.sin(self.setpoint_yaw), math.cos(self.setpoint_yaw))


    # ─────────────────────────────────────────────────────────────
    # Offboard control loop (20 Hz timer)
    # ─────────────────────────────────────────────────────────────

    def offboard_loop(self):
        """Publish OffboardControlMode + TrajectorySetpoint and handle
        arming / mode transitions."""

        # Always publish the offboard control mode so PX4 sees the heartbeat
        offboard_msg = OffboardControlMode()
        offboard_msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        offboard_msg.position = True
        offboard_msg.velocity = False
        offboard_msg.acceleration = False
        offboard_msg.attitude = False
        offboard_msg.body_rate = False
        offboard_msg.thrust_and_torque = False
        offboard_msg.direct_actuator = False
        self.publisher_offboard_mode.publish(offboard_msg)

        # Publish trajectory setpoint (even before arming — PX4 needs it to
        # accept offboard mode)
        if self.setpoint_initialised:
            sp = TrajectorySetpoint()
            sp.timestamp = int(self.get_clock().now().nanoseconds / 1000)
            sp.position = [
                float(self.setpoint_ned[0]),
                float(self.setpoint_ned[1]),
                float(self.setpoint_ned[2]),
            ]
            sp.velocity = [float('nan')] * 3
            sp.acceleration = [float('nan')] * 3
            sp.jerk = [float('nan')] * 3
            sp.yaw = float(self.setpoint_yaw)
            sp.yawspeed = float('nan')
            self.publisher_trajectory.publish(sp)

        # ── Request OFFBOARD mode (arming is handled via /scurid_drone/arming) ──
        if self.nav_state != VehicleStatus.NAVIGATION_STATE_OFFBOARD:
            self.get_logger().info('Requesting OFFBOARD mode …', throttle_duration_sec=2.0)
            self.send_vehicle_command(
                command=176,     # MAV_CMD_DO_SET_MODE
                param1=1.0,      # Custom mode flag
                param2=6.0,      # PX4 OFFBOARD mode
            )

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def send_vehicle_command(self, command, param1=0.0, param2=0.0):
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
        self.cmd_pub_px4.publish(msg)

    def shutdown(self):
        """Clean shutdown: disarm the vehicle."""
        self.get_logger().info('Running clean shutdown routine …')
        self.send_vehicle_command(command=400, param1=0.0)  # DISARM


###############################################
# Entry point                                 #
###############################################

def main(args=None):
    rclpy.init(args=args)
    executor = MultiThreadedExecutor()
    scurid_drone = ScuridDrone()
    executor.add_node(scurid_drone)

    try:
        executor.spin()
    except KeyboardInterrupt:
        scurid_drone.get_logger().info('Shutting down from keyboard interrupt.')
    finally:
        scurid_drone.shutdown()
        executor.spin_once(timeout_sec=1)

    scurid_drone.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()