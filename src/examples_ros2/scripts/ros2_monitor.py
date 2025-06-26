#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from pycontract import *
from examples_ros2.msg import Command, Status
import time

class ROS2MonitorNode(Node):
    monitor: 'CommandStatusMonitor'
    command_sub: rclpy.subscription.Subscription
    status_sub: rclpy.subscription.Subscription

    def __init__(self) -> None:
        super().__init__('pycontract_ros2_monitor')
        self.monitor: CommandStatusMonitor = CommandStatusMonitor()
        # Subscribe to both topics
        self.command_sub: rclpy.subscription.Subscription = self.create_subscription(
            Command,
            'commands',
            self.command_callback,
            10
        )
        self.status_sub: rclpy.subscription.Subscription = self.create_subscription(
            Status,
            'status',
            self.status_callback,
            10
        )
        
    def command_callback(self, msg: Command) -> None:
        """Convert Command message to pycontract event"""
        event = CommandEvent(
            cmd=msg.cmd,
            id=msg.id,
            timestamp=msg.timestamp
        )
        self.monitor.eval(event)

    def status_callback(self, msg: Status) -> None:
        """Convert Status message to pycontract event"""
        event = StatusEvent(
            status=msg.status,
            id=msg.id,
            timestamp=msg.timestamp
        )
        self.monitor.eval(event)

class CommandStatusMonitor(Monitor):
    """Monitor that ensures commands are completed within 3 seconds"""
    def transition(self, event: 'Event') -> object:
        match event:
            case CommandEvent(cmd, id, timestamp):
                return WaitingStatus(cmd, id, timestamp)
            case StatusEvent(status, id, timestamp):
                return error(f"Received status without matching command: {status}")

@data
class WaitingStatus(HotState):
    cmd: str
    id: int
    timestamp: float

    def transition(self, event: 'Event') -> object:
        match event:
            case StatusEvent(status, self.id, timestamp):
                if timestamp - self.timestamp <= 3.0:
                    return ok
                else:
                    return error(f"Command {self.cmd} took too long to complete")
            case CommandEvent(cmd, self.id, timestamp):
                return error(f"Duplicate command received: {cmd}")

@data
class CommandEvent(Event):
    cmd: str
    id: int
    timestamp: float

@data
class StatusEvent(Event):
    status: str
    id: int
    timestamp: float

def main() -> None:
    rclpy.init()
    node = ROS2MonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down...')
    finally:
        node.monitor.end()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
