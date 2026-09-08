"""Fixture launch file for tests/extract_golden.py."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")

    bridge = Node(
        package="probe_bridge",
        executable="probe_bridge_node",
        name="probe_bridge",
        parameters=[{"interface": "eth1", "enable_probe": True}],
        output="both",
    )

    pilot = Node(
        package="probe_pilot",
        executable="probe_pilot_node",
        name="probe_pilot",
        parameters=[{"enabled": True, "period_sec": 0.25}],
        output="both",
    )

    # A node that resolves against the vendored catalogue rather than this fixture's own source.
    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"use_sim_time": use_sim_time}],
        output="both",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            bridge,
            pilot,
            rsp,
        ]
    )
