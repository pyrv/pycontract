#!/usr/bin/env python3
import pycontract
import rclpy
from dataclasses import field
from rclpy.node import Node

from examples_ros2.msg import A, B, C, D, E, F, End
from typing import Any

import importlib
from rosidl_runtime_py.utilities import get_message
from rosidl_runtime_py.set_message import set_message_fields

def enable_pattern_matching_for_ros2_message(msg_cls):
    """Add __match_args__ so PEP-634 pattern matching works on ROS 2 messages.

    We take the field names from the generator-provided ``_fields_and_field_types``
    dict because it already lists the *public* message fields (without leading
    underscores) and omits internal attributes like ``_serialization_padding``.
    If that attribute is missing we fall back to stripping leading underscores
    from ``__slots__``.
    """
    if hasattr(msg_cls, "_fields_and_field_types"):
        msg_cls.__match_args__ = tuple(msg_cls._fields_and_field_types.keys())
    else:
        # Fallback – strip leading underscore that ROS puts in __slots__ entries
        msg_cls.__match_args__ = tuple(s.lstrip("_") for s in getattr(msg_cls, "__slots__", ()))
    return msg_cls

def enable_pattern_matching_for_ros2_package(pkg_name):
    """Enable pattern matching for every message class in the given ROS-2 package.

    We cannot rely on ``examples_ros2.msg.__all__`` because the generator does
    not create that attribute. Instead, we scan the module attributes and pick
    any class that has the marker ``_fields_and_field_types`` (present on all
    generated message classes).
    """
    msg_mod = importlib.import_module(pkg_name + '.msg')
    for attr_name in dir(msg_mod):
        cls = getattr(msg_mod, attr_name)
        if isinstance(cls, type) and hasattr(cls, '_fields_and_field_types'):
            enable_pattern_matching_for_ros2_message(cls)

# Assume the OrMonitor and contract logic is similar to examples/run_monitor.py, but events are now ROS2 messages

class ROS2RunMonitorNode(Node):
    def __init__(self) -> None:
        super().__init__('ros2_run_monitor')
        enable_pattern_matching_for_ros2_package('examples_ros2')
        self.monitor = OrMonitor(self.get_logger())
        # Subscribe to all six event topics
        self.a_sub = self.create_subscription(A, 'event_a', self.a_callback, 10)
        self.b_sub = self.create_subscription(B, 'event_b', self.b_callback, 10)
        self.c_sub = self.create_subscription(C, 'event_c', self.c_callback, 10)
        self.d_sub = self.create_subscription(D, 'event_d', self.d_callback, 10)
        self.e_sub = self.create_subscription(E, 'event_e', self.e_callback, 10)
        self.f_sub = self.create_subscription(F, 'event_f', self.f_callback, 10)
        self.end_sub = self.create_subscription(End, 'end', self.end_callback, 10)

    def end_callback(self, msg: End) -> None:
        event = msg
        self.get_logger().info(f"Received End: {event}")
        self.monitor.end()
        rclpy.shutdown()

    def a_callback(self, msg: A) -> None:
        event = msg
        self.get_logger().info(f"Received A: {event}")
        self.monitor.eval(event)

    def b_callback(self, msg: B) -> None:
        event = msg
        self.get_logger().info(f"Received B: {event}")
        self.monitor.eval(event)

    def c_callback(self, msg: C) -> None:
        event = msg
        self.get_logger().info(f"Received C: {event}")
        self.monitor.eval(event)

    def d_callback(self, msg: D) -> None:
        event = msg
        self.get_logger().info(f"Received D: {event}")
        self.monitor.eval(event)

    def e_callback(self, msg: E) -> None:
        event = msg
        self.get_logger().info(f"Received E: {event}")
        self.monitor.eval(event)

    def f_callback(self, msg: F) -> None:
        event = msg
        self.get_logger().info(f"Received F: {event}")
        self.monitor.eval(event)

class OrMonitor(pycontract.Monitor):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger

    """Example monitor using ROS2 messages as events."""
    
    def transition(self, event):
        match event:
            case A(x):
                self.logger.info(f"Processing A: {event}")
                return pycontract.OrState(
                    OrMonitor.Expect_B_NotD_C(self.logger, x),
                    OrMonitor.Expect_D_NotF_E(self.logger, x)
                )

    @pycontract.data
    class Expect_B_NotD_C(pycontract.HotState):
        logger: Any = field(repr=False, compare=False)
        x: int

        def transition(self, event):
            match event:
                case B(self.x):
                    self.logger.info(f"Processing B: {event}")
                    return OrMonitor.Expect_NotD_C(self.logger, self.x)

    @pycontract.data
    class Expect_NotD_C(pycontract.HotState):
        logger: Any = field(repr=False, compare=False)
        x: int

        def transition(self, event):
            match event:
                case D(self.x):
                    self.logger.info(f"Processing D: {event}")
                    return pycontract.error("D is not allowed in this branch")
                case C(self.x):
                    self.logger.info(f"Processing C: {event}")
                    return pycontract.ok

    @pycontract.data
    class Expect_D_NotF_E(pycontract.HotState):
        logger: Any = field(repr=False, compare=False)
        x: int

        def transition(self, event: Any):
            match event:
                case D(self.x):
                    self.logger.info(f"Processing D: {event}")
                    return OrMonitor.Expect_NotF_E(self.logger, self.x)

    @pycontract.data
    class Expect_NotF_E(pycontract.HotState):
        logger: Any = field(repr=False, compare=False)
        x: int

        def transition(self, event: Any):
            match event:
                case F(self.x):
                    self.logger.info(f"Processing F: {event}")
                    return pycontract.error("F is not allowed in this branch")
                case E(self.x):
                    self.logger.info(f"Processing E: {event}")
                    return pycontract.ok

def main() -> None:
    rclpy.init()
    node = ROS2RunMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down...')
    finally:
        node.monitor.end()

if __name__ == '__main__':
    main()
