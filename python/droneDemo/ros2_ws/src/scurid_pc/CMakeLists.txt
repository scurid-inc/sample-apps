cmake_minimum_required(VERSION 3.8)
project(scurid_pc)

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)

# Install all Python scripts in src/operation as executables
install(PROGRAMS
  src/attack_node.py
  src/control_node.py
  src/pc_telemetry_node.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY src
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()