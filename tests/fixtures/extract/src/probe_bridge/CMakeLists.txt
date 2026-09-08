cmake_minimum_required(VERSION 3.8)
project(probe_bridge)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(generate_parameter_library REQUIRED)

generate_parameter_library(probe_bridge_node src/probe_bridge_parameters.yaml)

add_executable(probe_bridge_node src/probe_bridge.cpp)
ament_target_dependencies(probe_bridge_node rclcpp std_msgs)

install(TARGETS probe_bridge_node DESTINATION lib/${PROJECT_NAME})
ament_package()
