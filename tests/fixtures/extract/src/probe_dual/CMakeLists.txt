cmake_minimum_required(VERSION 3.8)
project(probe_dual)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

# REGRESSION FIXTURE: TWO add_executable targets. Two executables are two processes with two
# separate sets of interfaces, and a model that merges them asserts that one binary serves
# both -- a false claim with no flag on it.
add_executable(probe_alpha src/probe_alpha.cpp)
ament_target_dependencies(probe_alpha rclcpp std_msgs)

add_executable(probe_beta src/probe_beta.cpp)
ament_target_dependencies(probe_beta rclcpp std_msgs)

install(TARGETS probe_alpha probe_beta DESTINATION lib/${PROJECT_NAME})
ament_package()
