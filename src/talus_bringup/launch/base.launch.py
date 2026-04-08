from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    bridge_params_file = LaunchConfiguration("bridge_params_file")
    imu_filter_params_file = LaunchConfiguration("imu_filter_params_file")
    serial_port = LaunchConfiguration("serial_port")
    enable_imu_filter = LaunchConfiguration("enable_imu_filter")
    imu_parent_frame = LaunchConfiguration("imu_parent_frame")
    imu_frame = LaunchConfiguration("imu_frame")
    imu_x = LaunchConfiguration("imu_x")
    imu_y = LaunchConfiguration("imu_y")
    imu_z = LaunchConfiguration("imu_z")
    imu_roll = LaunchConfiguration("imu_roll")
    imu_pitch = LaunchConfiguration("imu_pitch")
    imu_yaw = LaunchConfiguration("imu_yaw")

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
            DeclareLaunchArgument("serial_port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("enable_imu_filter", default_value="true"),
            DeclareLaunchArgument("imu_parent_frame", default_value="base_link"),
            DeclareLaunchArgument("imu_frame", default_value="imu_link"),
            DeclareLaunchArgument("imu_x", default_value="0.0"),
            DeclareLaunchArgument("imu_y", default_value="0.0"),
            DeclareLaunchArgument("imu_z", default_value="0.0"),
            DeclareLaunchArgument("imu_roll", default_value="0.0"),
            DeclareLaunchArgument("imu_pitch", default_value="0.0"),
            DeclareLaunchArgument("imu_yaw", default_value="0.0"),
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
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="imu_static_tf",
                output="screen",
                arguments=[
                    "--x",
                    imu_x,
                    "--y",
                    imu_y,
                    "--z",
                    imu_z,
                    "--roll",
                    imu_roll,
                    "--pitch",
                    imu_pitch,
                    "--yaw",
                    imu_yaw,
                    "--frame-id",
                    imu_parent_frame,
                    "--child-frame-id",
                    imu_frame,
                ],
            ),
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
