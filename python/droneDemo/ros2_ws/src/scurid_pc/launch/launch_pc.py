from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='scurid_pc',
            executable='pc_telemetry_node.py',
            output='screen'
        ),
    ])