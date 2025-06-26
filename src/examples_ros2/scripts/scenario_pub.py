#!/usr/bin/env python3
import rclpy, time
from rclpy.node import Node
from examples_ros2.msg import A, B, C, End

class ScenarioPublisher(Node):
    def __init__(self):
        super().__init__('scenario_publisher')
        self.a_pub = self.create_publisher(A, 'event_a', 10)
        self.b_pub = self.create_publisher(B, 'event_b', 10)
        self.c_pub = self.create_publisher(C, 'event_c', 10)
        self.end_pub = self.create_publisher(End, 'end', 10)
        self.timer = self.create_timer(1.0, self.run_scenario)
        self.step = 0

    def run_scenario(self):
        msg_map = {0: (self.a_pub, A(x=42)),
                   1: (self.b_pub, B(x=42)),
                   2: (self.c_pub, C(x=42)),
                   3: (self.end_pub, End())}
        if self.step in msg_map:
            pub, msg = msg_map[self.step]
            pub.publish(msg)
            self.get_logger().info(f'Published step {self.step}: {msg}')
            self.step += 1
        else:
            # all done → stop this node
            rclpy.shutdown()

def main():
    rclpy.init()
    rclpy.spin(ScenarioPublisher())

if __name__ == '__main__':
    main()
