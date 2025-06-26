#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from examples_ros2.msg import Command
import argparse
import time

class CommandPublisher(Node):
    publisher_: rclpy.publisher.Publisher
    timer: rclpy.timer.Timer
    id: int

    def __init__(self) -> None:
        super().__init__('command_publisher')
        self.publisher_ = self.create_publisher(Command, 'commands', 10)
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.id = 0

    def timer_callback(self) -> None:
        msg = Command()
        msg.cmd = f'cmd_{self.id}'
        msg.id = self.id
        msg.timestamp = self.get_clock().now().to_msg().sec + self.get_clock().now().to_msg().nanosec / 1e9
        self.publisher_.publish(msg)
        self.get_logger().info(f'Sending command: {msg.cmd} with id: {msg.id}')
        self.id += 1

def main() -> None:
    rclpy.init()
    node = CommandPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down...')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
