#!/usr/bin/env python3

import math

import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node


class ControlDrone(Node):
    """Simple controller node that publishes desired position setpoints."""

    def __init__(self):
        super().__init__("control_drone")

        self.declare_parameter("radius", 10.0)
        self.declare_parameter("omega", 0.5)
        self.declare_parameter("altitude", 5.0)

        self.radius = float(self.get_parameter("radius").value)
        self.omega = float(self.get_parameter("omega").value)
        self.altitude = float(self.get_parameter("altitude").value)

        self.theta = 0.0
        self.dt = 0.05

        self.pub_setpoint = self.create_publisher(Point, "/offboard/position_setpoint", 10)
        self.timer = self.create_timer(self.dt, self._timer_cb)

        self.get_logger().info(
            f"ControlDrone started  r={self.radius} m  omega={self.omega} rad/s  alt={self.altitude} m"
        )

    def _timer_cb(self):
        msg = Point()
        msg.x = self.radius * math.cos(self.theta)
        msg.y = self.radius * math.sin(self.theta)
        msg.z = self.altitude
        self.pub_setpoint.publish(msg)

        self.theta += self.omega * self.dt


def main(args=None):
    rclpy.init(args=args)
    node = ControlDrone()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
