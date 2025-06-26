# Change Log

## 2025-06-25

### Build Fixes
* Added `empy` and `catkin_pkg` to requirements to satisfy ROS message generation and package parsing.

### Fixes
* `enable_pattern_matching_for_ros2_package` now scans the message module for classes with `_fields_and_field_types` instead of relying on missing `__all__`, preventing `AttributeError` on launch.

### Features
* Enhanced `src/examples_ros2/scripts/run_monitor.py.enable_pattern_matching` to derive `__match_args__` from the ROS-generated `_fields_and_field_types`, enabling clean structural pattern matching without internal slots.

### Dependency Fixes
* Added `PyYAML` to `src/pycontract/requirements.txt` to satisfy ROS 2's `rclpy` dependency.

### Documentation
* Updated `README.md` installation instructions to match new `src/` layout:
  * Dependencies are now installed via `pip install -r src/pycontract/requirements.txt`.
  * Editable install is performed with `pip install -e src/pycontract` instead of root-level `pip install -e .`.


### User Updates
* Added `End.msg` and updated `CMakeLists.txt` to generate the new message.
* Added `launch/` directory installation rule and created `launch/test_monitor.launch.py` to automate multi-node test.
* Added `scripts/scenario_pub.py` to replay the A–B–C–End scenario.
* Enhanced `scripts/run_monitor.py`:
  * Subscribes to `/end` topic to shut down automatically.
  * Injects `logger` into monitor states; replaced direct `print` with ROS logging.
  * Converted inner state classes to `@pycontract.data` dataclasses eliminating manual `__init__`.
* Updated `README-ROS2.md`:
  * Replaced manual node instructions with single launch command.
  * Added Mermaid sequence diagram illustrating test interactions.


### Build Fixes
* Added proper shebang (`#!/usr/bin/env python3`) to `command_publisher.py`, `status_publisher.py`, and `ros2_monitor.py` in `src/examples_ros2/scripts/`.
* Added `<member_of_group>rosidl_interface_packages</member_of_group>` to `src/examples_ros2/package.xml` to fix `colcon build` error requiring this entry for packages installing interfaces.
* Build error about missing `ament_package` (ModuleNotFoundError) was resolved by installing `ros-jazzy-desktop-full` (not by installing `python3-ament-package` or using pip).


## 2025-06-24

### Project restructuring
* Moved source code into `src/` layout and staged git renames for former top-level directories (`examples`, `examples-ros2`, `pycontract`).

### New build / package files
* **src/examples**
  * Added `CMakeLists.txt` (assistant) and updated it to install `run_monitor.py` only (user).
  * Added `package.xml` (assistant) and updated maintainer + switched to `ament_python` (user / assistant).
* **src/examples_ros2**
  * Added `pycontract` dependency to `package.xml` (assistant).
  * Updated maintainers in `package.xml` (user).
* **src/pycontract**
  * Added `setup.py` for ament_python build (assistant).
  * Converted `package.xml` to use `ament_python`; removed ROS 2 specific deps and added a single `<export><build_type>ament_python</build_type></export>` section (assistant).

### Repository meta
* Updated `.gitignore` to exclude `build`, `install`, and `log` directories (user).
* Created (and later removed) top-level `CMakeLists.txt` while investigating colcon graph visibility (assistant then user deleted).

### Build status
* Converted **src/examples_ros2** from `ament_python` to `ament_cmake`:
  * Added `CMakeLists.txt` to generate custom messages and install scripts (removed unnecessary `find_package(pycontract)`).
  * Updated `package.xml` to use `ament_cmake`, add `rosidl_default_generators/runtime` deps.
  * Removed need for `setup.py`; build error fixed.
* Added `setup.py` and `resource/pycontract_examples` to **src/examples** so that package `pycontract_examples` builds correctly with `ament_python`.
* `colcon graph` now shows three packages: `pycontract`, `pycontract_examples`, `examples_ros2`.
* Added `resource/pycontract` file required by ament to register the package, fixing the previous colcon build error.
* Re-run `colcon build` should now succeed for all packages.
