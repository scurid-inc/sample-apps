#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Joystick → PoseStamped relay for scurid_drone.

Reads a sensor_msgs/Joy topic and publishes a geometry_msgs/PoseStamped
on /scurid_drone/relative_pose_cmd with desired *relative* body-frame
movement so the main node can rotate it into NED and integrate it into
the trajectory setpoint.

Stick mapping (Xbox-style controller):
  Left stick  Y (axes[1])  → Δx  (body forward / back)
  Left stick  X (axes[0])  → Δyaw (heading change)
  Button A    (buttons[0]) → Arm
  Button B    (buttons[1]) → Disarm
  Right stick X (axes[3])  → Δy  (body sideways left / right)
  Right trigger (axes[5])  → descend   (body z positive = down)
  Left trigger  (axes[2])  → climb     (body z negative = up)

Scaling is applied per axis so the output PoseStamped contains
metre/rad increments suitable for a 20 Hz control loop.
The main node converts body-frame deltas to NED using the current heading.

Author: Erik Winkler
Date: 13.03.2026
"""

###############################################
# Standard Imports                            #
###############################################

###############################################
# ROS Imports                                 #
###############################################
import rclpy
from rclpy.node import Node

###############################################
# ROS Topic messages                          #
###############################################
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Joy
from std_msgs.msg import String


###############################################
# Joystick relay node                         #
###############################################


class JoystickRelay(Node):
    """Translate Joy messages into PoseStamped relative-movement commands."""

    def __init__(self):
        super().__init__('joystick_relay')

        # ── Parameters (can be overridden via ROS params) ───────
        self.declare_parameter('deadzone', 0.05)
        self.declare_parameter('scale_xy', 0.15)    # m per tick @ 20 Hz → ~3 m/s max
        self.declare_parameter('scale_z', 0.10)     # m per tick
        self.declare_parameter('scale_yaw', 0.05)   # rad per tick → ~1 rad/s max

        self.deadzone   = self.get_parameter('deadzone').value
        self.scale_xy   = self.get_parameter('scale_xy').value
        self.scale_z    = self.get_parameter('scale_z').value
        self.scale_yaw  = self.get_parameter('scale_yaw').value

        # ── Publishers ──────────────────────────────────────────
        self.pose_pub = self.create_publisher(
            PoseStamped, '/scurid_drone/relative_pose_cmd', 10)
        self.arming_pub = self.create_publisher(
            String, '/scurid_drone/arming', 10)

        # ── Subscriber ──────────────────────────────────────────
        self.joy_sub = self.create_subscription(
            Joy, '/joy', self.joy_callback, 10)

        self.get_logger().info(
            'JoystickRelay started — publishing on /scurid_drone/relative_pose_cmd')

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def apply_deadzone(self, value: float) -> float:
        return 0.0 if abs(value) < self.deadzone else value

    # ─────────────────────────────────────────────────────────────
    # Joy callback
    # ─────────────────────────────────────────────────────────────

    def joy_callback(self, msg: Joy):
        # ── Button handling: arm / disarm ────────────────────
        try:
            if msg.buttons[0]:  # Button A → Arm
                arm_msg = String()
                arm_msg.data = 'arm'
                self.arming_pub.publish(arm_msg)
            if msg.buttons[1]:  # Button B → Disarm
                disarm_msg = String()
                disarm_msg.data = 'disarm'
                self.arming_pub.publish(disarm_msg)
        except IndexError as e:
            self.get_logger().warn('Error: ', e)

        try:
            # Stick inputs (with deadzone)
            forward  = self.apply_deadzone(msg.axes[1])   # Left stick Y  → body forward
            sideways = self.apply_deadzone(msg.axes[3])   # Right stick X → body sideways
            yaw_in   = self.apply_deadzone(msg.axes[0])   # Left stick X  → Yaw

            # Right trigger: raw value goes from 1 (released) to -1 (pressed)
            # Normalise to 0 … 1  →  map to descent (positive D)
            # Left trigger for climb (negative D)
            rt = (-msg.axes[5] + 1.0) / 2.0   # 0..1  (descend)
            lt = (-msg.axes[2] + 1.0) / 2.0   # 0..1  (climb)
            vertical = rt - lt                  # positive = down, negative = up
        except IndexError:
            self.get_logger().warn('Joy axes incomplete — ignoring message.', throttle_duration_sec=2.0)
            return

        # Scale to metre / rad increments (body frame)
        dx_body =  forward  * self.scale_xy      # body forward
        dy_body =  sideways * self.scale_xy       # body sideways
        dz_body =  vertical * self.scale_z        # body down
        dyaw    = -yaw_in   * self.scale_yaw      # yaw (negative so stick-left = yaw-left)

        # Build PoseStamped (body-frame deltas)
        pose_msg = PoseStamped()
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        pose_msg.header.frame_id = 'base_link'

        pose_msg.pose.position.x = dx_body
        pose_msg.pose.position.y = dy_body
        pose_msg.pose.position.z = dz_body

        # Encode Δyaw in the quaternion z component (simple convention)
        pose_msg.pose.orientation.x = 0.0
        pose_msg.pose.orientation.y = 0.0
        pose_msg.pose.orientation.z = dyaw
        pose_msg.pose.orientation.w = 1.0

        self.pose_pub.publish(pose_msg)


###############################################
# Entry point                                 #
###############################################


def main(args=None):
    rclpy.init(args=args)
    node = JoystickRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down JoystickRelay.')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()