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

# MicroXRCEAgent serial --dev /dev/ttyUSB0 -b 921600

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
            depth=1,
        )

        qos_profile_sub = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # ── Publishers ──────────────────────────────────────────
        self.publisher_offboard_mode = self.create_publisher(
            OffboardControlMode, '/fmu/in/offboard_control_mode', qos_profile_pub)
        self.publisher_trajectory = self.create_publisher(
            TrajectorySetpoint, '/fmu/in/trajectory_setpoint', qos_profile_pub)
        self.cmd_pub_px4 = self.create_publisher(
            VehicleCommand, '/fmu/in/vehicle_command', qos_profile_pub)

        # ── Subscribers (PX4) ───────────────────────────────────
        self.status_sub_v3 = self.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status_v3',
            self.vehicle_status_callback, qos_profile_sub)
        
        self.status_sub = self.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status',
            self.vehicle_status_callback, qos_profile_sub)

        self.local_pos_sub_v1 = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position_v1',
            self.local_position_callback, qos_profile_sub)
        
        self.local_pos_sub = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position',
            self.local_position_callback, qos_profile_sub)

        # self.global_pos_sub = self.create_subscription(
        #     VehicleGlobalPosition, '/fmu/out/vehicle_global_position',
        #     self.global_pos_callback, qos_profile_sub)

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
        self.arming_state = VehicleStatus.ARMING_STATE_DISARMED   #ARMING_STATE_STANDBY

        # self.get_logger().info(f"VehicleStatus.ARMING_STATE_DISARMED: {VehicleStatus.ARMING_STATE_DISARMED}")

        # Current local NED position from PX4
        self.local_pos_ned = [0.0, 0.0, 0.0]   # x(N), y(E), z(D)
        self.current_yaw = 0.0                   # rad
        self.local_pos_valid = False

        # Desired setpoint (absolute NED), initialised on first position fix
        self.setpoint_ned = [float('nan')] * 3
        self.setpoint_yaw = float('nan')
        self.setpoint_initialised = False

        # OFFBOARD / ARM handshake state
        self.offboard_setpoint_counter = 0
        self.arm_requested = False
        self.last_mode_request_s = 0.0
        self.last_arm_request_s = 0.0

        # ── Timer: publish offboard heartbeat + setpoint @ 20 Hz
        self.offboard_timer = self.create_timer(0.05, self.offboard_loop)

        self.get_logger().info('ScuridDrone node started — waiting for position fix …')
        self.land_requested = False
        self.land_command_sent = False

        self.home_xy_ned = None
        self.home_yaw = None
        self.home_captured = False

    # ─────────────────────────────────────────────────────────────
    # PX4 Callbacks
    # ─────────────────────────────────────────────────────────────

    def vehicle_status_callback(self, msg):
        self.nav_state = msg.nav_state
        self.arming_state = msg.arming_state

    def arming_callback(self, msg: String):
        """Handle arm/disarm/land commands from /scurid_drone/arming topic."""
        cmd = msg.data.strip().lower()

        if cmd == 'arm':
            self.arm_requested = True
            self.land_requested = False
            self.land_command_sent = False

            # Reset target to current vehicle pose before arming
            if self.setpoint_initialised:
                self.setpoint_ned = list(self.local_pos_ned)
                self.setpoint_yaw = self.current_yaw

                # Capture takeoff / landing reference once
                self.home_xy_ned = [self.local_pos_ned[0], self.local_pos_ned[1]]
                self.home_yaw = self.current_yaw
                self.home_captured = True

            self.get_logger().info(
                f'ARM topic received | arm_requested={self.arm_requested} '
                f'setpoint=[{self.setpoint_ned[0]:.2f}, {self.setpoint_ned[1]:.2f}, {self.setpoint_ned[2]:.2f}] '
                f'home_xy={self.home_xy_ned} '
                f'nav_state={self.nav_state} '
                f'arming_state={self.arming_state}'
            )

        elif cmd == 'land':
            self.get_logger().info(
                f'Land requested via topic | nav_state={self.nav_state} '
                f'arming_state={self.arming_state}'
            )
            self.arm_requested = False
            self.land_requested = True
            self.land_command_sent = False

        elif cmd == 'disarm':
            self.get_logger().warn('Disarm requested via topic')
            self.arm_requested = False
            self.land_requested = False
            self.land_command_sent = False
            self.send_vehicle_command(command=400, param1=0.0)   # DISARM
        elif cmd == 'home':
            if not self.home_captured or self.home_xy_ned is None:
                self.get_logger().warn('HOME requested but no home position has been captured yet')
                return

            is_offboard = self.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
            is_armed = self.arming_state == VehicleStatus.ARMING_STATE_ARMED

            if not (is_offboard and is_armed):
                self.get_logger().warn('HOME requested but vehicle is not armed and in OFFBOARD')
                return

            # Return to remembered XY, keep current altitude
            self.setpoint_ned[0] = self.home_xy_ned[0]
            self.setpoint_ned[1] = self.home_xy_ned[1]

            self.get_logger().info(
                f'Returning to home XY: x={self.home_xy_ned[0]:.2f}, '
                f'y={self.home_xy_ned[1]:.2f}, keeping z={self.setpoint_ned[2]:.2f}'
            )
        else:
            self.get_logger().warn(f'Unknown command: "{msg.data}"')

    def land(self):
        """Request PX4 Land mode."""
        self.get_logger().info('Requesting LAND ...')
        self.send_vehicle_command(
            command=21,   # VEHICLE_CMD_NAV_LAND / MAV_CMD_NAV_LAND
        )

    def local_position_callback(self, msg: VehicleLocalPosition):
        self.get_logger().info(
            f'Local pos received: x={msg.x:.2f}, y={msg.y:.2f}, z={msg.z:.2f}, '
            f'heading={msg.heading:.2f}, xy_valid={msg.xy_valid}, z_valid={msg.z_valid}',
            throttle_duration_sec=2.0
        )
        # Always cache the latest estimate coming from PX4
        self.local_pos_ned = [msg.x, msg.y, msg.z]
        self.current_yaw = msg.heading
        self.local_pos_valid = bool(msg.xy_valid and msg.z_valid)

        # Initialise setpoint from the first local position message we receive,
        # even if PX4 does not mark xy/z as valid in this setup.
        if not self.setpoint_initialised:
            self.setpoint_ned = [msg.x, msg.y, msg.z]
            self.setpoint_yaw = msg.heading
            self.setpoint_initialised = True
            self.get_logger().info(
                f'Setpoint initialised to [{msg.x:.2f}, {msg.y:.2f}, {msg.z:.2f}] '
                f'yaw={msg.heading:.2f} | xy_valid={msg.xy_valid} z_valid={msg.z_valid}'
            )

    def global_pos_callback(self, msg):
        pass  # placeholder — extend for GPS‑based logic / UTM conversion

    def attitude_callback(self, msg):
        pass  # placeholder — extend if quaternion attitude is needed

    # ─────────────────────────────────────────────────────────────
    # Relative pose command (from joystick_input or any other source)
    # ─────────────────────────────────────────────────────────────

    def pose_cmd_callback(self, msg: PoseStamped):
        if not self.setpoint_initialised:
            return

        is_offboard = self.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        is_armed = self.arming_state == VehicleStatus.ARMING_STATE_ARMED

        if not (is_armed and is_offboard):
            return

        dx_body = msg.pose.position.x
        dy_body = msg.pose.position.y
        dz_body = msg.pose.position.z

        cos_yaw = math.cos(self.current_yaw)
        sin_yaw = math.sin(self.current_yaw)
        dn = dx_body * cos_yaw - dy_body * sin_yaw
        de = dx_body * sin_yaw + dy_body * cos_yaw

        self.setpoint_ned[0] += dn
        self.setpoint_ned[1] += de
        self.setpoint_ned[2] += dz_body

        dyaw = msg.pose.orientation.z
        self.setpoint_yaw += dyaw
        self.setpoint_yaw = math.atan2(
            math.sin(self.setpoint_yaw), math.cos(self.setpoint_yaw)
        )


    # ─────────────────────────────────────────────────────────────
    # Offboard control loop (20 Hz timer)
    # ─────────────────────────────────────────────────────────────

    def offboard_loop(self):
        """Publish OffboardControlMode + TrajectorySetpoint and handle
        OFFBOARD / arming transitions in the correct PX4 order."""

        now_us = int(self.get_clock().now().nanoseconds / 1000)
        now_s = now_us / 1e6

        # If LAND was requested, stop offboard publishing and hand control to PX4
        if self.land_requested:
            is_armed = self.arming_state == VehicleStatus.ARMING_STATE_ARMED

            if not is_armed:
                self.get_logger().warn('LAND requested but vehicle is not armed')
                self.land_requested = False
                self.land_command_sent = False
                return

            if not self.land_command_sent:
                self.get_logger().info(
                    f'Sending LAND command | nav_state={self.nav_state} '
                    f'arming_state={self.arming_state}'
                )
                self.land()
                self.land_command_sent = True
                self.last_mode_request_s = now_s

            # IMPORTANT:
            # Do NOT publish OffboardControlMode or TrajectorySetpoint anymore.
            # Do NOT try to switch back to OFFBOARD.
            return

        # Always publish the offboard heartbeat so PX4 sees the stream
        offboard_msg = OffboardControlMode()
        offboard_msg.timestamp = now_us
        offboard_msg.position = True
        offboard_msg.velocity = False
        offboard_msg.acceleration = False
        offboard_msg.attitude = False
        offboard_msg.body_rate = False
        # offboard_msg.thrust_and_torque = False
        # offboard_msg.direct_actuator = False
        self.publisher_offboard_mode.publish(offboard_msg)

        # Publish trajectory setpoint continuously once initialised
        if self.setpoint_initialised:
            sp = TrajectorySetpoint()
            sp.timestamp = now_us
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

            if self.offboard_setpoint_counter < 50:
                self.offboard_setpoint_counter += 1
                if self.offboard_setpoint_counter == 50:
                    self.get_logger().info('OFFBOARD warmup complete (50 setpoints sent)')

        if not self.setpoint_initialised:
            self.get_logger().info(
                'Waiting for valid local position / setpoint initialisation...',
                throttle_duration_sec=2.0
            )
            return

        is_offboard = self.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        is_armed = self.arming_state == VehicleStatus.ARMING_STATE_ARMED
        warmup_done = self.offboard_setpoint_counter >= 50

        # Step 1: after warmup, request OFFBOARD mode
        if warmup_done and not is_offboard and (now_s - self.last_mode_request_s) >= 0.5:
            self.get_logger().info(
                f'Requesting OFFBOARD mode ... nav_state={self.nav_state} '
                f'arming_state={self.arming_state}'
            )
            self.send_vehicle_command(
                command=176,   # VEHICLE_CMD_DO_SET_MODE
                param1=1.0,    # custom mode flag
                param2=6.0,    # PX4 OFFBOARD
            )
            self.last_mode_request_s = now_s
            return

        if self.arm_requested and (now_s - self.last_arm_request_s) >= 0.5 and not is_armed:
            self.get_logger().info(
                f'ARM pending | warmup_done={warmup_done} '
                f'is_offboard={is_offboard} '
                f'nav_state={self.nav_state} '
                f'arming_state={self.arming_state}'
            )

        # Step 2: only arm after OFFBOARD is active and an arm was requested
        if (
            self.arm_requested
            and warmup_done
            and is_offboard
            and not is_armed
            and (now_s - self.last_arm_request_s) >= 0.5
        ):
            self.get_logger().info('Requesting ARM ...')
            self.send_vehicle_command(
                command=400,   # VEHICLE_CMD_COMPONENT_ARM_DISARM
                param1=1.0,
            )
            self.last_arm_request_s = now_s

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
