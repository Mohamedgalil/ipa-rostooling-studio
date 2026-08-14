# Popular ROS 2 Packages Reference

**Sources:** metrics.ros.org, awesome_ros_packages_and_tools, and awesome-ros2 (fetched during this session)

This document catalogs commonly-used ROS 2 packages extracted from three authoritative sources:
- **metrics.ros.org/repos_table.html** — quantitative metrics (stars, forks, activity)
- **github.com/vovaekb/awesome_ros_packages_and_tools** — curated ecosystem overview by category
- **github.com/fkromer/awesome-ros2** — comprehensive ROS 2 infrastructure and application packages

Packages appearing in multiple sources are marked **(multi-source)**.

---

## High-Activity Core Packages (from metrics.ros.org)

| Package | Purpose | Source |
|---------|---------|--------|
| **ros/ros_comm** | Core ROS communication framework (920 forks, 801 stars) | metrics.ros.org |
| **ros-planning/navigation** | Navigation stack (1,832 forks, 2,642 stars) | metrics.ros.org |
| **ros-simulation/gazebo_ros_pkgs** | Gazebo simulation integration (784 forks, 860 stars) | metrics.ros.org |
| **googlecartographer/cartographer_ros** | SLAM system (1,282 forks, 1,834 stars) | metrics.ros.org |
| **MoveIt** | Motion planning framework | metrics.ros.org |

---

## Core Libraries & Infrastructure

| Package | Purpose | Source |
|---------|---------|--------|
| **rcl** | ROS client library (C implementation) | awesome-ros2 **(new)** |
| **rclcpp** | C++ ROS client library | awesome-ros2 **(new)** |
| **rclpy** | Python ROS client library | awesome-ros2 **(new)** |
| **rcljava** | Java ROS client library | awesome-ros2 **(new)** |
| **rclc** | C ROS client library for micro-ROS | awesome-ros2 **(new)** |
| **rcl_interfaces** | Message definitions and services for client libraries | awesome-ros2 **(new)** |
| **ros2_rust** | Rust bindings for ROS 2 | awesome-ros2 **(new)** |
| **rclnodejs** | JavaScript and TypeScript APIs | awesome-list |
| **rclgo** | Go wrapper for ROS2 | awesome-list |
| **rclada** | Ada ROS 2 client library | awesome-ros2 **(new)** |
| **rclobjc** | Objective-C ROS 2 client library | awesome-ros2 **(new)** |
| **ros2_dotnet** | .NET binding for ROS 2 | awesome-ros2 **(new)** |
| **ros2cs** | C# bindings for ROS 2 | awesome-ros2 **(new)** |

---

## DDS & Middleware Implementations

| Package | Purpose | Source |
|---------|---------|--------|
| **rmw** | ROS Middleware abstraction layer | awesome-ros2 **(new)** |
| **rmw_fastrtps_cpp** | Fast-RTPS DDS middleware implementation | awesome-ros2 **(new)** |
| **rmw_cyclonedds** | Eclipse Cyclone DDS middleware | awesome-ros2 **(new)** |
| **rmw_connext_cpp** | RTI Connext DDS middleware | awesome-ros2 **(new)** |
| **rmw_opensplice_cpp** | OpenSplice DDS middleware | awesome-ros2 **(new)** |
| **rmw_coredx** | CoreDX DDS middleware | awesome-ros2 **(new)** |
| **rmw_dps** | Intel DPS middleware | awesome-ros2 **(new)** |
| **rmw_zenoh** | Eclipse Zenoh middleware backend | awesome-ros2 **(new)** |
| **rmw_iceoryx** | Eclipse iceoryx middleware | awesome-ros2 **(new)** |
| **rmw_freertps** | FreeRTPS middleware | awesome-ros2 **(new)** |
| **Fast-RTPS** | eProsima Fast-RTPS DDS implementation | awesome-ros2 **(new)** |
| **Connext DDS** | RTI Connext DDS platform | awesome-ros2 **(new)** |
| **OpenSplice** | ADLINK OpenSplice DDS | awesome-ros2 **(new)** |
| **CoreDX DDS** | RETX CoreDX DDS implementation | awesome-ros2 **(new)** |
| **cdds (Cyclone DDS)** | Eclipse Cyclone DDS open-source implementation | awesome-ros2 **(new)** |
| **Micro-XRCE-DDS** | eProsima Micro XRCE-DDS for embedded systems | awesome-ros2 **(new)** |
| **freertps** | Open-source RTPS implementation | awesome-ros2 **(new)** |
| **rcutils** | ROS C utilities library | awesome-ros2 **(new)** |
| **Eclipse Zenoh** | Pub/sub protocol for ROS 2 | awesome-ros2 **(new)** |
| **Eclipse Zenoh-Plugin-DDS** | DDS bridge plugin for Zenoh | awesome-ros2 **(new)** |

---

## IDL & Build Infrastructure

| Package | Purpose | Source |
|---------|---------|--------|
| **rosidl** | ROS Interface Definition Language | awesome-ros2 **(new)** |
| **rosidl_dds** | DDS-specific IDL generator | awesome-ros2 **(new)** |
| **rosidl_generator_cpp** | C++ code generator from ROS IDL | awesome-ros2 **(new)** |
| **rosidl_generator_c** | C code generator from ROS IDL | awesome-ros2 **(new)** |
| **rosidl_generator_java** | Java code generator from ROS IDL | awesome-ros2 **(new)** |
| **rosidl_generator_objc** | Objective-C code generator from ROS IDL | awesome-ros2 **(new)** |
| **rmw_implementation_cmake** | CMake utilities for RMW implementation selection | awesome-ros2 **(new)** |
| **ament_cmake_export_jars** | Ament build system support for Java JAR exports | awesome-ros2 **(new)** |
| **meta-ros2** | Yocto layer for ROS 2 build system | awesome-ros2 **(new)** |
| **ci** | CI infrastructure for ROS 2 project | awesome-ros2 **(new)** |
| **rmw_implementation** | RMW implementation selection mechanism | awesome-ros2 **(new)** |

---

## Infrastructure & Messaging

| Package | Purpose | Source |
|---------|---------|--------|
| **topic_tools** | Tools for directing, throttling, and manipulating ROS 2 topics | awesome-list |
| **flex_sync** | Headers-only library for message synchronization filtering | awesome-list |
| **proto2ros** | Interoperability bridge between Protobuf and ROS messages | awesome-list |
| **ros2systemd** | ROS2 command extension for managing launches and nodes as systemd services | awesome-list |
| **ros2_message_filters** | Message filtering and time synchronization | awesome-ros2 **(new)** |
| **angles** | Mathematical utilities for angle operations | awesome-list |

---

## Logging, Diagnostics & Introspection

| Package | Purpose | Source |
|---------|---------|--------|
| **rcl_logging_syslog** | Alternative logging backend via syslog | awesome-list |
| **ros2_fmt_logger** | Modern logging with fmt-style formatting | awesome-list |
| **diagnostic_remote_logging** | Logs diagnostics to InfluxDB for trend analysis and Grafana visualization | awesome-list |
| **ros2probe** | Host-level observability for ROS 2 DDS traffic | awesome-list |
| **ros_tap** | Zero-configuration telemetry tap for network robots | awesome-list |
| **log_view** | ncurses UI for viewing and filtering rosout logs | awesome-list |
| **breadcrumb** | ROS2 graph static analysis tool | awesome-list |
| **ros2_medkit** | Automotive-grade diagnostics framework | awesome-list |
| **tf_tree_terminal** | Terminal-based TF tree visualization | awesome-list |
| **ros2_tracing** | Tracing instrumentation for core ROS 2 | awesome-list |

---

## Visualization & Monitoring

| Package | Purpose | Source |
|---------|---------|--------|
| **PlotJuggler** | Time series visualization tool | awesome-list |
| **terminal_pcl_visualizer** | Real-time 3D point cloud terminal visualizer | awesome-list |
| **R'DASH** | Cross-platform real-time robot data visualization dashboard | awesome-list |
| **ros2plot** | Terminal-based real-time plotting for topics | awesome-list |
| **ROSboard** | Web server for robot visualizations | awesome-list |
| **system_webview** | Real-time system monitoring dashboard with web UI | awesome-list |
| **RQml** | QML-based robotics visualization toolbox | awesome-list |
| **Phantom Bridge** | WebRTC ROS2 bridge for real-time visualization | awesome-list |
| **bt_visualizer_pkg** | Behavior tree visualization tool | awesome-list |
| **urdf-viz** | URDF file viewer (cross-platform) | awesome-list |
| **rqt_frame_editor_plugin** | Frame manipulation via dragging | awesome-list |
| **ROSplat** | Gaussian splatting-enabled visualizer | awesome-list |
| **RVizSplat** | 3D Gaussian splat rendering in RViz2 | awesome-list |
| **Altara** | React components for telemetry dashboards | awesome-list |
| **TermViz2** | Terminal visualizer for maps, scans, clouds, and markers | awesome-list |

---

## Perception: Vision & Computer Vision

| Package | Purpose | Source |
|---------|---------|--------|
| **opencv_ros2** | OpenCV applications with ROS2 | awesome-list |
| **SAM3 ROS Wrapper** | Segment Anything Model 3 wrapper | awesome-list |
| **dinov3_ros** | DINOv3-based vision tasks (detection, segmentation, depth) | awesome-list |
| **ROS 2 YOLOs-CPP** | Production-grade object detection and segmentation | awesome-list |
| **ROS 2 OpenCV Face Tracker** | Zero-latency face tracking | awesome-list |
| **robovision_ros2** | Robot vision introduction examples | awesome-list |
| **ros2-object-detection-pipeline** | Phone camera YOLO detection | awesome-list |
| **yolo_ros** | YOLO wrapper for detection, tracking, and pose estimation | awesome-list |
| **ros2-tensorflow** | Tensorflow inference wrapper | awesome-list **(multi-source)** |
| **ros2_pytorch** | PyTorch inference wrapper | awesome-ros2 **(new)** |
| **ros2_pytorch_cuda** | PyTorch CUDA-accelerated inference wrapper | awesome-ros2 **(new)** |
| **Surround Vision for ROS 2** | Fisheye camera fusion with top-down visualization | awesome-list |
| **Focus Peaking ROS2** | Manual lens focusing assistance with edge highlighting | awesome-list |
| **darknet_ros** | Darknet YOLO integration for ROS 2 | awesome-ros2 **(new)** |

---

## Perception: LiDAR & 3D Point Clouds

| Package | Purpose | Source |
|---------|---------|--------|
| **mola_lidar_odometry** | LiDAR odometry package | awesome-list |
| **GenZ-ICP** | Robust LiDAR odometry solution | awesome-list |
| **omnivision** | 360° image and 3D LiDAR data fusion | awesome-list |
| **multisensor_calibration** | Universal calibration toolbox for multi-sensor systems | awesome-list |
| **ros2_camera_lidar_fusion** | Camera-LiDAR integration package | awesome-list |
| **POLKA** | Multi-LiDAR fusion node with optional CUDA acceleration | awesome-list |
| **PCL Point Cloud Processing Pipeline** | Configurable processing library | awesome-list |
| **GSeg3D** | Grid-based ground segmentation for autonomous systems | awesome-list |
| **Perception Vault** | Comprehensive sensor data perception framework | awesome-list |
| **pointcloud_concatenate_ros2** | Multi-pointcloud concatenation | awesome-list |
| **pcdet_ros2** | OpenPCDet LIDAR 3D object detection wrapper | awesome-list |
| **pointcloud_to_grid** | PointCloud2 to OccupancyGrid conversion | awesome-list |
| **ros2_pcl_segmentation** | PCL-based point cloud segmentation | awesome-list |
| **octomap_server2** | 3D occupancy mapping with octrees | awesome-ros2 **(new)** |

---

## SLAM & Mapping

| Package | Purpose | Source |
|---------|---------|--------|
| **cartographer** | Google Cartographer SLAM system | awesome-ros2 **(multi-source)** |
| **ros2-ORB_SLAM2** | ORB-SLAM2 visual SLAM wrapper | awesome-ros2 **(new)** |
| **basalt_ros2** | Basalt visual-inertial SLAM | awesome-ros2 **(new)** |
| **slam_gmapping** | GMapping-based SLAM backend | awesome-ros2 **(new)** |
| **slam_toolbox** | Modern SLAM toolbox for ROS 2 | awesome-ros2 **(new)** |
| **lidarslam_ros2** | LiDAR-based SLAM system | awesome-ros2 **(new)** |
| **li_slam_ros2** | Lightweight LiDAR-based SLAM | awesome-ros2 **(new)** |

---

## Localization & Navigation

| Package | Purpose | Source |
|---------|---------|--------|
| **apriltag_detector** | AprilTag detection and pose publishing | awesome-list |
| **apriltag_ros** | AprilTag ROS package | awesome-ros2 **(new)** |
| **wayp_plan_tools** | Waypoint and planner tools with minimal dependencies | awesome-list **(multi-source)** |
| **Open Navigation's Nav2 Complete Coverage** | Coverage path planning integration | awesome-list |
| **FlexCloud** | Point cloud georeferencing and drift correction | awesome-list |
| **VoxelNav** | Real-time semantic voxel mapping | awesome-list |
| **mogi_trajectory_server** | Trajectory visualization for ROS2 | awesome-list |
| **collision_restraint** | Obstacle avoidance via velocity restraint | awesome-list |
| **ROS2 Planning System** | PDDL-based planning system for robotics developers | awesome-list |

---

## Control, Teleoperation & Human-Robot Interaction

| Package | Purpose | Source |
|---------|---------|--------|
| **TeleopXR** | VR/AR headset robot controller | awesome-list |
| **ros2_teleoperation** | QT-based teleoperation interface | awesome-list |
| **teleop_twist_keyboard** | Keyboard-based robot teleoperation | awesome-ros2 **(new)** |
| **teleop_twist_joy** | Joystick-based teleoperation | awesome-ros2 **(new)** |
| **ros2_teleop_keyboard** | Alternative keyboard teleoperation interface | awesome-ros2 **(new)** |
| **rosforge** | Workspace scaffolder and multi-machine diagnostics | awesome-list |
| **OpenTelemetry** | Production-grade integration library for instrumenting ROS2 applications | awesome-list |
| **Telegraf Resource Monitor** | System resource monitoring integration | awesome-list |
| **LGDXRobot Cloud** | AGV management system | awesome-list |
| **Agent ROS Bridge** | Universal bridge for AI agents (WebSocket, MQTT, gRPC) | awesome-list |
| **ROSGPT** | ChatGPT interface for ROS2 | awesome-list |
| **ROS2 Clean Architecture Environment** | Claude Code skills for ROS2 | awesome-list |
| **RosClaw** | OpenClaw-ROS2 integration plugin | awesome-list |

---

## Networking & Security

| Package | Purpose | Source |
|---------|---------|--------|
| **ROS 2 Cross-Platform Network Fixer** | Automates DDS discovery configuration | awesome-list |
| **RoboShield** | Lightweight network intrusion detection for ROS 2 | awesome-list |
| **ROS 2 Kinematic Guard** | Lightweight safety middleware for mobile robots | awesome-list |
| **Husarnet VPN** | VPN network stack for ROS 2 multi-robot systems | awesome-ros2 **(new)** |

---

## Robot Simulation & Modeling

| Package | Purpose | Source |
|---------|---------|--------|
| **Gazebo** (gazebo_ros_pkgs) | Simulation integration | metrics.ros.org **(multi-source)** |
| **Webots** | Open-source robot simulator | awesome-ros2 **(new)** |
| **LGSVL** | LGSVL simulator for autonomous vehicles | awesome-ros2 **(new)** |
| **Unity Robotics Hub** | Unity integration for ROS 2 simulation | awesome-ros2 **(new)** |
| **ROS2 For Unity** | ROS 2 C# communication for Unity | awesome-ros2 **(new)** |
| **sw2robot** | SolidWorks to URDF converter | awesome-list |
| **Conveyor Simulation ROS 2 Package** | Gazebo conveyor belt simulation | awesome-list |
| **URDF Architect** | Web-based visual URDF creation environment | awesome-list |

---

## URDF & Geometry

| Package | Purpose | Source |
|---------|---------|--------|
| **urdfdom** | URDF parsing and manipulation library | awesome-ros2 **(new)** |
| **urdfdom_headers** | Header files for urdfdom | awesome-ros2 **(new)** |
| **geometry2** | Geometric transforms and utilities (TF2) | awesome-ros2 **(new)** |
| **robot_state_publisher** | Publishes robot state from URDF | awesome-ros2 **(new)** |
| **common_interfaces** | Common message and service definitions | awesome-ros2 **(new)** |

---

## Bag File Tools & Data Analysis

| Package | Purpose | Source |
|---------|---------|--------|
| **bag2mesh** | Convert RGB-D bag files to 3D meshes | awesome-list |
| **ROS2 Bag Manager** | Web-based bag file management | awesome-list |
| **rospeek** | Fast Rust-based bag analyzer | awesome-list |
| **ros2_unbag** | Export bags to human-readable formats | awesome-list |
| **ros2bag_tools** | CLI extensions for ros2bag | awesome-list |
| **rosbag-resurrector** | Pandas-like analysis tool for MCAP bags | awesome-list |
| **rosbag2** | ROS 2 bag file recording and playback | awesome-ros2 **(new)** |

---

## Development & Tooling

| Package | Purpose | Source |
|---------|---------|--------|
| **ROS Dev Toolkit** | VS Code extension for ROS development | awesome-list |
| **ROS 2 Project Builder** | CLI package and node creation | awesome-list |
| **launch_graph** | Launch file structure visualization | awesome-list |
| **rsl** | C++17 utilities collection for ROS | awesome-list |
| **ROS 2 Environment Manager for VS Code** | VS Code environment management | awesome-list |
| **ament_ruff** | Python linting with ament integration | awesome-list |
| **rtest** | ROS 2 unit testing framework | awesome-list |
| **ros2_console_tools** | Terminal-first inspection and visualization | awesome-list |
| **rostree** | CLI tool for package dependency exploration | awesome-list |
| **synchros2** | Simplified ROS 2 programming approach | awesome-list |
| **robotdatapy** | Robot and geometric data manipulation | awesome-list |
| **fri** | Fuzzy fzf wrapper for ROS2 | awesome-list |
| **dynamic_reconfigure** | RViz2 parameter reconfiguration GUI | awesome-list |
| **sdf_to_urdf** | SDF to URDF conversion tool | awesome-list |
| **ros2mock** | Service and action mocking tool | awesome-list |
| **ROS 2 Launch GUI** | Visual launch file monitoring | awesome-list |
| **ros2cli** | ROS 2 command line interface tools | awesome-ros2 **(new)** |

---

## Testing & Benchmarking

| Package | Purpose | Source |
|---------|---------|--------|
| **ros2_benchmarking** | ROS 2 performance benchmarking framework | awesome-ros2 **(new)** |
| **performance_test** | Middleware performance measurement tool | awesome-ros2 **(new)** |
| **system_tests** | ROS 2 system testing infrastructure | awesome-ros2 **(new)** |
| **aztarna** | Footprinting and reconnaissance tool for ROS systems | awesome-ros2 **(new)** |
| **ros2_fuzzer** | Fuzzing framework for ROS 2 security testing | awesome-ros2 **(new)** |

---

## Hardware Integration & Drivers

| Package | Purpose | Source |
|---------|---------|--------|
| **rplidar_ros2_driver** | Refactored, fault-tolerant RPLIDAR driver with lifecycle support | awesome-list |
| **Qualcomm QRB-ROS** | Hardware acceleration packages for Qualcomm platforms | awesome-list |
| **oxide_gnss** | Rust-based GNSS driver with NTRIP client | awesome-list |
| **Servo Control Interface for ROS 2** | Arduino servo motor control | awesome-list |
| **Crosstalk** | Single-header C++17 serial communication library | awesome-list |
| **ros2_imu** | ESP32-based IMU node via Micro ROS | awesome-list |
| **Mobile Sensor Bridge for ROS2** | Android smartphone sensor streaming | awesome-list |
| **joystick_drivers** | Generic joystick/gamepad support | awesome-ros2 **(new)** |
| **joystick_drivers_from_scratch** | Joystick driver implementation | awesome-ros2 **(new)** |
| **joystick_ros2** | ROS 2 joystick node | awesome-ros2 **(new)** |
| **ros_astra_camera** | Astra camera driver | awesome-ros2 **(new)** |
| **ros2_usb_camera** | Generic USB camera driver | awesome-ros2 **(new)** |
| **ros2_intel_realsense** | Intel RealSense camera integration | awesome-ros2 **(new)** |
| **ydlidar_ros2** | YDLiDAR driver for ROS 2 | awesome-ros2 **(new)** |
| **zed-ros2-wrapper** | Stereolabs ZED camera wrapper | awesome-ros2 **(new)** |
| **sick_scan2** | SICK LiDAR driver for ROS 2 | awesome-ros2 **(new)** |
| **ros2_ouster_drivers** | Ouster LiDAR driver | awesome-ros2 **(new)** |
| **ros2_denso_radar** | DENSO radar integration | awesome-ros2 **(new)** |
| **ros2_track_imu** | IMU tracking and fusion | awesome-ros2 **(new)** |
| **raspicam2_node** | Raspberry Pi camera driver | awesome-ros2 **(new)** |
| **ros2_raspicam_node** | Alternative Raspberry Pi camera driver | awesome-ros2 **(new)** |
| **ros2_android_drivers** | Android device drivers for ROS 2 | awesome-ros2 **(new)** |
| **HRIM** | Hardware Robot Interface and Modules | awesome-ros2 **(new)** |
| **FIROS2** | Firmware interaction framework for ROS 2 | awesome-ros2 **(new)** |
| **px4_to_ros** | PX4 autopilot bridge for ROS 2 | awesome-ros2 **(new)** |
| **multiwii_ros2** | MultiWii flight controller integration | awesome-ros2 **(new)** |
| **odrive_ros2_control** | ODrive motor controller integration | awesome-ros2 **(new)** |
| **duro_gps_driver** | Duro RTK GPS driver | awesome-ros2 **(new)** |
| **Universal Robots** | Universal Robots collaborative arm drivers | awesome-ros2 **(new)** |
| **Blickfeld Cube 1 & Cube Range** | Blickfeld LiDAR integration | awesome-ros2 **(new)** |
| **Microros_hardware** | Micro-ROS hardware support packages | awesome-ros2 **(new)** |

---

## Embedded & Micro-ROS

| Package | Purpose | Source |
|---------|---------|--------|
| **Micro XRCE-DDS Agent** | Agent for Micro XRCE-DDS communication | awesome-ros2 **(new)** |
| **Micro XRCE-DDS Client** | Embedded client for Micro XRCE-DDS | awesome-ros2 **(new)** |
| **micro-ROS-Agent** | Micro-ROS communication agent | awesome-ros2 **(new)** |
| **micro_ros_arduino** | Micro-ROS implementation for Arduino | awesome-ros2 **(new)** |
| **micro_ros_zephyr_module** | Micro-ROS module for Zephyr RTOS | awesome-ros2 **(new)** |

---

## Multi-Language Support

| Package | Purpose | Source |
|---------|---------|--------|
| **jros2** | Java ROS 2 library with Fast-DDS | awesome-list |
| **rclgo** | Go wrapper for ROS2 | awesome-list |
| **swift-ros2** | Native Swift client library | awesome-list |
| **rclnodejs** | JavaScript and TypeScript APIs | awesome-list |
| **tf2_rs** | Rust bindings for TF2 | awesome-list |

---

## Mathematics & Core Utilities

| Package | Purpose | Source |
|---------|---------|--------|
| **refx** | Header-only C++ library for mobile robotics with compile-time safety | awesome-list |
| **ICEY** | Modern async client API using C++20 coroutines | awesome-list |
| **Copper Runtime & SDK** | Operating system for deterministic robot execution | awesome-list |
| **orocos_kinematics_dynamics** | KDL kinematics and dynamics library | awesome-ros2 **(new)** |

---

## Robotics Platforms & Demonstrations

| Package | Purpose | Source |
|---------|---------|--------|
| **turtlebot3** | TurtleBot3 robot platform and drivers | awesome-ros2 **(new)** |
| **turtlebot2_demo** | TurtleBot2 demonstration packages | awesome-ros2 **(new)** |
| **adlink_ddsbot** | ADLINK DDS-based robot platform | awesome-ros2 **(new)** |
| **adlink_neuronbot** | ADLINK NeuroBot platform | awesome-ros2 **(new)** |
| **Autoware.Auto** | Open-source autonomous vehicle software | awesome-ros2 **(new)** |
| **Autoware.IO** | Autoware I/O interface layer | awesome-ros2 **(new)** |
| **Apex.Autonomy** | Apex.AI autonomy stack | awesome-ros2 **(new)** |
| **ROS 2: Sim-to-Real Robot Control** | Industrial and collaborative robot packages | awesome-list |
| **lino2_upper** | Lino2 upper body robot | awesome-ros2 **(new)** |
| **RysROS2** | Rys robot platform | awesome-ros2 **(new)** |

---

## Motion Control & Manipulation

| Package | Purpose | Source |
|---------|---------|--------|
| **ros2_control** | Framework for robot controller implementations | awesome-ros2 **(new)** |
| **ros2_controllers** | Generic controllers for ros2_control | awesome-ros2 **(new)** |
| **ros2_grasp_library** | Grasp planning and execution library | awesome-ros2 **(new)** |
| **easy_manipulation_deployment** | Simplified manipulation task deployment | awesome-ros2 **(new)** |
| **pid** | PID control library for ROS 2 | awesome-ros2 **(new)** |
| **ros2_pid_library** | Alternative PID control implementation | awesome-ros2 **(new)** |

---

## Computer Vision & AI Integration

| Package | Purpose | Source |
|---------|---------|--------|
| **vision_opencv** | OpenCV integration and image transport | awesome-ros2 **(new)** |
| **ros2_object_map** | Object mapping and tracking | awesome-ros2 **(new)** |
| **ros2_object_analytics** | Object detection and analytics | awesome-ros2 **(new)** |
| **ros2_intel_movidius_ncs** | Intel Movidius NCS neural compute stick | awesome-ros2 **(new)** |
| **ros2_moving_object** | Moving object detection and tracking | awesome-ros2 **(new)** |
| **ros2_openvino_toolkit** | OpenVINO toolkit integration | awesome-ros2 **(new)** |
| **easy_perception_deployment** | Simplified perception model deployment | awesome-ros2 **(new)** |

---

## System Abstraction & Interoperability

| Package | Purpose | Source |
|---------|---------|--------|
| **system_tests** | ROS 2 system testing infrastructure | awesome-ros2 **(new)** |
| **system-modes** | System modes for ROS 2 state management | awesome-ros2 **(new)** |
| **rclandroid** | ROS 2 Android integration | awesome-ros2 **(new)** |
| **riot-ros2** | RIOT OS integration with ROS 2 | awesome-ros2 **(new)** |
| **ROS2-Integration-Service** | ROS 2 integration with external systems | awesome-ros2 **(new)** |
| **soss** | System of Systems Middleware | awesome-ros2 **(new)** |
| **ros2_xmlrpc_interface** | XML-RPC bridge for ROS 2 | awesome-ros2 **(new)** |

---

## Containerization & Deployment

| Package | Purpose | Source |
|---------|---------|--------|
| **docker-ros2-ospl-ce** | Docker image with ROS 2 and OpenSplice | awesome-ros2 **(new)** |
| **docker-ros2-desktop-vnc** | Docker ROS 2 desktop with VNC support | awesome-ros2 **(new)** |
| **ros2_java_docker** | Docker setup for ROS 2 Java development | awesome-ros2 **(new)** |
| **ros-tooling/cross_compile** | Cross-compilation tools for ROS 2 | awesome-ros2 **(new)** |
| **osrf/docker_images** | Official OSRF ROS 2 Docker images | awesome-ros2 **(new)** |

---

## Ecosystem & Integration

| Package | Purpose | Source |
|---------|---------|--------|
| **Link ROS** | Link protocol integration for ROS 2 | awesome-ros2 **(new)** |
| **rviz** | 3D visualization tool (core ROS 2 component) | awesome-ros2 **(new)** |
| **urdfdom** | URDF parsing library | awesome-ros2 **(new)** |
| **pydds** | Python DDS bindings | awesome-ros2 **(new)** |
| **Jupyter ROS2** | Jupyter notebook integration for ROS 2 | awesome-ros2 **(new)** |
| **Foxglove Studio** | Web-based visualization studio for ROS 2 | awesome-ros2 **(new)** |
| **rosbridge_suite** | JSON API bridge for ROS 2 web applications | awesome-ros2 **(new)** |

---

## Specialized Domains

| Package | Purpose | Source |
|---------|---------|--------|
| **ROS2 RAG** | RAG system lifecycle node | awesome-list |
| **ROS MCP Server** | AI model-robot connection via MCP protocol | awesome-list |
| **Nav2 MCP Server** | Nav2 control and monitoring MCP server | awesome-list |
| **reductstore_agent** | High-performance topic recording to ReductStore | awesome-list |
| **cozmo_driver_ros2** | Cozmo robot driver for ROS 2 | awesome-ros2 **(new)** |
| **sphero_ros2** | Sphero robot integration | awesome-ros2 **(new)** |
| **flock2** | Flock robotics platform integration | awesome-ros2 **(new)** |

---

## Legacy (ROS 1)

| Package | Purpose | Source |
|---------|---------|--------|
| **MiniROS cpp distribution** | Standalone C++17 ROS1 client | awesome-list |

---

## Notes

- **metrics.ros.org** provides the most-starred and most-forked projects; the fetched content included representative high-activity packages but may not be exhaustive due to pagination/rendering.
- **awesome_ros_packages_and_tools** is a curated community collection organized by functional category, emphasizing integration tools, visualization, and application-domain packages.
- **awesome-ros2** is a comprehensive infrastructure-focused collection covering ROS 2 core libraries, middleware implementations, drivers, platforms, and deployment tools. This source surfaces much broader ecosystem coverage including foundational DDS/RMW implementations, client libraries across multiple languages, robotics platforms, and system-level integration packages.
- Overlap between sources exists but is limited to high-profile projects (navigation, Gazebo, cartographer). The first two sources complement each other well; the third source adds critical infrastructure and platform-specific integrations.

---

**Maintenance:** This file is refreshed by the `/update-ros-catalog` command, which re-fetches
the three standing sources above via a cheap (haiku) agent and can also merge in additional
source URLs passed as arguments.
