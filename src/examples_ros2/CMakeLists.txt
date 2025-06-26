cmake_minimum_required(VERSION 3.5)
project(examples_ros2)

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Message files
set(msg_files
  "msg/End.msg"
  "msg/Command.msg"
  "msg/Status.msg"
  "msg/A.msg"
  "msg/B.msg"
  "msg/C.msg"
  "msg/D.msg"
  "msg/E.msg"
  "msg/F.msg"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  DEPENDENCIES std_msgs
)

# Install Python scripts
install(PROGRAMS
  scripts/command_publisher.py
  scripts/status_publisher.py
  scripts/run_monitor.py
  scripts/ros2_monitor.py
  scripts/scenario_pub.py
  DESTINATION lib/${PROJECT_NAME}
)

# Install launch files
install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

# Install resource marker and package.xml
install(FILES
  resource/examples_ros2
  package.xml
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
