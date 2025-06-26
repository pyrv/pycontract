cmake_minimum_required(VERSION 3.5)
project(pycontract_examples)

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

# Find Python
find_package(Python3 COMPONENTS Interpreter Development)

# Install examples
install(DIRECTORY .
  DESTINATION share/${PROJECT_NAME}
  PATTERN "*.py")
