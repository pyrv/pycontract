from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Monitor node
        Node(
            package='examples_ros2',
            executable='run_monitor.py',
            name='run_monitor'
        ),

        # Publisher node that re-plays the scenario
        Node(
            package='examples_ros2',
            executable='scenario_pub.py',
            name='scenario_publisher'
        ),
    ])
