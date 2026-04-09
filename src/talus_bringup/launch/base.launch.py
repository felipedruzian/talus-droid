from pathlib import Path

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _load_frame_entry(frames_file: str, key: str) -> dict:
    frames = yaml.safe_load(Path(frames_file).read_text()).get("frames", {})
    if key not in frames:
        raise KeyError(f"Missing frame entry '{key}' in {frames_file}")
    return frames[key]


def _make_static_tf_node(name: str, frame: dict) -> Node:
    xyz = [str(value) for value in frame.get("xyz", [0.0, 0.0, 0.0])]
    rpy = [str(value) for value in frame.get("rpy", [0.0, 0.0, 0.0])]
    return Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name=name,
        output="screen",
        arguments=[
            "--x",
            xyz[0],
            "--y",
            xyz[1],
            "--z",
            xyz[2],
            "--roll",
            rpy[0],
            "--pitch",
            rpy[1],
            "--yaw",
            rpy[2],
            "--frame-id",
            frame["parent"],
            "--child-frame-id",
            frame["child"],
        ],
    )


def _imu_tf_node(context):
    frames_file = LaunchConfiguration("frames_file").perform(context)
    return [_make_static_tf_node("imu_static_tf", _load_frame_entry(frames_file, "imu"))]


def generate_launch_description() -> LaunchDescription:
    bridge_params_file = LaunchConfiguration("bridge_params_file")
    imu_filter_params_file = LaunchConfiguration("imu_filter_params_file")
    serial_port = LaunchConfiguration("serial_port")
    enable_imu_filter = LaunchConfiguration("enable_imu_filter")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "bridge_params_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("talus_base"), "config", "bridge.yaml"]
                ),
            ),
            DeclareLaunchArgument(
                "imu_filter_params_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("talus_bringup"), "config", "imu_filter.yaml"]
                ),
            ),
            DeclareLaunchArgument(
                "frames_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("talus_bringup"), "config", "frames.yaml"]
                ),
            ),
            DeclareLaunchArgument("serial_port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("enable_imu_filter", default_value="true"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("talus_base"), "launch", "bridge.launch.py"]
                    )
                ),
                launch_arguments={
                    "params_file": bridge_params_file,
                    "serial_port": serial_port,
                }.items(),
            ),
            OpaqueFunction(function=_imu_tf_node),
            Node(
                package="imu_filter_madgwick",
                executable="imu_filter_madgwick_node",
                name="imu_filter",
                output="screen",
                condition=IfCondition(enable_imu_filter),
                parameters=[imu_filter_params_file],
            ),
        ]
    )
