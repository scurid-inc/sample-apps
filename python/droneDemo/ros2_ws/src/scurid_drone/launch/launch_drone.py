from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='scurid_drone',
            executable='main.py',
            output='screen'
        ),
        Node(
            package='scurid_drone',
            executable='verification_node.py',
            output='screen'
        ),
        Node(
            package='scurid_drone',
            executable='drone_telemetry_node.py',
            output='screen'
        ),
    ])