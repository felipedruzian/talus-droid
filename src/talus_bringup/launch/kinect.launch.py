from pathlib import Path

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
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


def _camera_tf_nodes(context):
    driver_mode = LaunchConfiguration("driver_mode").perform(context)
    frames_file = LaunchConfiguration("frames_file").perform(context)

    nodes = [
        _make_static_tf_node(
            "camera_mount_static_tf", _load_frame_entry(frames_file, "camera_mount")
        )
    ]
    if driver_mode == "modular":
        nodes.extend(
            [
                _make_static_tf_node(
                    "camera_rgb_optical_static_tf",
                    _load_frame_entry(frames_file, "camera_rgb_optical"),
                ),
                _make_static_tf_node(
                    "camera_depth_optical_static_tf",
                    _load_frame_entry(frames_file, "camera_depth_optical"),
                ),
            ]
        )
    return nodes


def generate_launch_description() -> LaunchDescription:
    driver_mode = LaunchConfiguration("driver_mode")
    rgb_camera_info_url = LaunchConfiguration("rgb_camera_info_url")
    depth_camera_info_url = LaunchConfiguration("depth_camera_info_url")

    modular_condition = IfCondition(
        PythonExpression(["'", driver_mode, "' == 'modular'"])
    )
    unified_condition = IfCondition(
        PythonExpression(["'", driver_mode, "' == 'unified'"])
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("driver_mode", default_value="modular"),
            DeclareLaunchArgument(
                "frames_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("talus_bringup"), "config", "frames.yaml"]
                ),
            ),
            DeclareLaunchArgument(
                "rgb_camera_info_url",
                default_value=[
                    "file://",
                    PathJoinSubstitution(
                        [FindPackageShare("kinect_ros2"), "cfg", "calibration_rgb.yaml"]
                    ),
                ],
            ),
            DeclareLaunchArgument(
                "depth_camera_info_url",
                default_value=[
                    "file://",
                    PathJoinSubstitution(
                        [FindPackageShare("kinect_ros2"), "cfg", "calibration_depth.yaml"]
                    ),
                ],
            ),
            OpaqueFunction(function=_camera_tf_nodes),
            Node(
                package="ros2_kinect_rgb",
                executable="rgb_node",
                name="kinect_rgb_node",
                output="screen",
                condition=modular_condition,
                parameters=[{"camera_info_url": rgb_camera_info_url}],
                remappings=[
                    ("kinect/rgb/image_raw", "image_raw"),
                    ("kinect/rgb/camera_info", "camera_info"),
                ],
            ),
            Node(
                package="ros2_kinect_depth",
                executable="depth_node",
                name="kinect_depth_node",
                output="screen",
                condition=modular_condition,
                parameters=[
                    {"camera_info_url": depth_camera_info_url, "encoding": "16UC1"}
                ],
                remappings=[
                    ("kinect/depth/image_raw", "depth/image_raw"),
                    ("kinect/depth/camera_info", "depth/camera_info"),
                ],
            ),
            Node(
                package="kinect_ros2",
                executable="kinect_ros2_node",
                name="kinect_ros2_node",
                output="screen",
                condition=unified_condition,
            ),
        ]
    )
