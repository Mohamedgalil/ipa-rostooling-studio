# Popular ROS 2 Packages Reference

**Sources:** metrics.ros.org and awesome_ros_packages_and_tools (fetched during this session)

This document catalogs commonly-used ROS 2 packages extracted from two authoritative sources:
- **metrics.ros.org/repos_table.html** — quantitative metrics (stars, forks, activity)
- **github.com/vovaekb/awesome_ros_packages_and_tools** — curated ecosystem overview by category

Packages appearing in both sources are marked **(both)**.

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

## Infrastructure & Messaging

| Package | Purpose | Source |
|---------|---------|--------|
| **topic_tools** | Tools for directing, throttling, and manipulating ROS 2 topics | awesome-list |
| **flex_sync** | Headers-only library for message synchronization filtering | awesome-list |
| **proto2ros** | Interoperability bridge between Protobuf and ROS messages | awesome-list |
| **ros2systemd** | ROS2 command extension for managing launches and nodes as systemd services | awesome-list |
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
| **ros2-tensorflow** | Tensorflow inference wrapper | awesome-list |
| **Surround Vision for ROS 2** | Fisheye camera fusion with top-down visualization | awesome-list |
| **Focus Peaking ROS2** | Manual lens focusing assistance with edge highlighting | awesome-list |

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

---

## Localization & Navigation

| Package | Purpose | Source |
|---------|---------|--------|
| **apriltag_detector** | AprilTag detection and pose publishing | awesome-list |
| **wayp_plan_tools** | Waypoint and planner tools with minimal dependencies | awesome-list |
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

---

## Robot Simulation & Modeling

| Package | Purpose | Source |
|---------|---------|--------|
| **Gazebo** (gazebo_ros_pkgs) | Simulation integration | metrics.ros.org **(both)** |
| **sw2robot** | SolidWorks to URDF converter | awesome-list |
| **Conveyor Simulation ROS 2 Package** | Gazebo conveyor belt simulation | awesome-list |
| **URDF Architect** | Web-based visual URDF creation environment | awesome-list |

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

---

## Specialized Domains

| Package | Purpose | Source |
|---------|---------|--------|
| **ROS 2: Sim-to-Real Robot Control** | Industrial and collaborative robot packages | awesome-list |
| **ROS2 RAG** | RAG system lifecycle node | awesome-list |
| **ROS MCP Server** | AI model-robot connection via MCP protocol | awesome-list |
| **Nav2 MCP Server** | Nav2 control and monitoring MCP server | awesome-list |
| **reductstore_agent** | High-performance topic recording to ReductStore | awesome-list |

---

## Legacy (ROS 1)

| Package | Purpose | Source |
|---------|---------|--------|
| **MiniROS cpp distribution** | Standalone C++17 ROS1 client | awesome-list |

---

## Notes

- **metrics.ros.org** provides the most-starred and most-forked projects; the fetched content included representative high-activity packages but may not be exhaustive due to pagination/rendering.
- **awesome_ros_packages_and_tools** is a curated community collection organized by functional category. The awesome-list captures a much broader ecosystem snapshot, including specialized and emerging tools.
- Overlap between sources is limited; the high-activity packages from metrics.ros.org (ros_comm, navigation, gazebo, cartographer, MoveIt) represent foundational infrastructure, while the awesome-list emphasizes integration tools, visualization, and application-domain packages.

---

**Maintenance:** This file is refreshed by the `/update-ros-catalog` command, which re-fetches
the two standing sources above via a cheap (haiku) agent and can also merge in additional
source URLs passed as arguments.
