#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Position relay — reads VehicleLocalPosition from PX4 and publishes
it as a geometry_msgs/PoseStamped on /scurid_drone/output_pos.

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

###############################################
# ROS Topic messages                          #
###############################################
from geometry_msgs.msg import PoseStamped
from px4_msgs.msg import VehicleLocalPosition


class PositionRelay(Node):
    """Subscribe to PX4 local position and republish as PoseStamped."""

    def __init__(self):
        super().__init__('position_relay')

        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.pos_sub = self.create_subscription(
            VehicleLocalPosition, 
            '/fmu/out/vehicle_local_position',
            self.local_position_callback, 
            qos_profile)
        
        self.pos_sub_v1 = self.create_subscription(
            VehicleLocalPosition, 
            '/fmu/out/vehicle_local_position_v1',
            self.local_position_callback, 
            qos_profile)

        self.pos_pub = self.create_publisher(
            PoseStamped, 
            '/scurid_drone/output_pos', 
            10)

        self.get_logger().info('PositionRelay started — publishing on /scurid_drone/output_pos')

    def local_position_callback(self, msg: VehicleLocalPosition):
        self.get_logger().info('SENDING POSITION!')
        if not (msg.xy_valid and msg.z_valid):
            return

        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = 'map_ned'

        pose.pose.position.x = float(msg.x)
        pose.pose.position.y = float(msg.y)
        pose.pose.position.z = float(msg.z)

        # Convert heading to quaternion (rotation around D / z-axis)
        yaw = float(msg.heading)
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)

        self.pos_pub.publish(pose)


def main(args=None):
    rclpy.init(args=args)
    node = PositionRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down PositionRelay.')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
