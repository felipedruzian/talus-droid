from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    enable_teleop = LaunchConfiguration("enable_teleop")
    enable_kinect = LaunchConfiguration("enable_kinect")
    serial_port = LaunchConfiguration("serial_port")
    joy_device_id = LaunchConfiguration("joy_device_id")
    bridge_params_file = LaunchConfiguration("bridge_params_file")
    imu_filter_params_file = LaunchConfiguration("imu_filter_params_file")
    joy_params_file = LaunchConfiguration("joy_params_file")
    teleop_params_file = LaunchConfiguration("teleop_params_file")
    imu_parent_frame = LaunchConfiguration("imu_parent_frame")
    imu_frame = LaunchConfiguration("imu_frame")
    imu_x = LaunchConfiguration("imu_x")
    imu_y = LaunchConfiguration("imu_y")
    imu_z = LaunchConfiguration("imu_z")
    imu_roll = LaunchConfiguration("imu_roll")
    imu_pitch = LaunchConfiguration("imu_pitch")
    imu_yaw = LaunchConfiguration("imu_yaw")
    camera_parent_frame = LaunchConfiguration("camera_parent_frame")
    camera_frame = LaunchConfiguration("camera_frame")
    camera_x = LaunchConfiguration("camera_x")
    camera_y = LaunchConfiguration("camera_y")
    camera_z = LaunchConfiguration("camera_z")
    camera_roll = LaunchConfiguration("camera_roll")
    camera_pitch = LaunchConfiguration("camera_pitch")
    camera_yaw = LaunchConfiguration("camera_yaw")

    return LaunchDescription(
        [
            DeclareLaunchArgument("enable_teleop", default_value="true"),
            DeclareLaunchArgument("enable_kinect", default_value="false"),
            DeclareLaunchArgument("serial_port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("joy_device_id", default_value="0"),
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
                "joy_params_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("talus_bringup"), "config", "joy.yaml"]
                ),
            ),
            DeclareLaunchArgument(
                "teleop_params_file",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("talus_bringup"),
                        "config",
                        "teleop_twist_joy.yaml",
                    ]
                ),
            ),
            DeclareLaunchArgument("imu_parent_frame", default_value="base_link"),
            DeclareLaunchArgument("imu_frame", default_value="imu_link"),
            DeclareLaunchArgument("imu_x", default_value="0.0"),
            DeclareLaunchArgument("imu_y", default_value="0.0"),
            DeclareLaunchArgument("imu_z", default_value="0.0"),
            DeclareLaunchArgument("imu_roll", default_value="0.0"),
            DeclareLaunchArgument("imu_pitch", default_value="0.0"),
            DeclareLaunchArgument("imu_yaw", default_value="0.0"),
            DeclareLaunchArgument("camera_parent_frame", default_value="base_link"),
            DeclareLaunchArgument("camera_frame", default_value="camera_link"),
            DeclareLaunchArgument("camera_x", default_value="0.0"),
            DeclareLaunchArgument("camera_y", default_value="0.0"),
            DeclareLaunchArgument("camera_z", default_value="0.0"),
            DeclareLaunchArgument("camera_roll", default_value="0.0"),
            DeclareLaunchArgument("camera_pitch", default_value="0.0"),
            DeclareLaunchArgument("camera_yaw", default_value="0.0"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("talus_bringup"), "launch", "base.launch.py"]
                    )
                ),
                launch_arguments={
                    "bridge_params_file": bridge_params_file,
                    "imu_filter_params_file": imu_filter_params_file,
                    "serial_port": serial_port,
                    "imu_parent_frame": imu_parent_frame,
                    "imu_frame": imu_frame,
                    "imu_x": imu_x,
                    "imu_y": imu_y,
                    "imu_z": imu_z,
                    "imu_roll": imu_roll,
                    "imu_pitch": imu_pitch,
                    "imu_yaw": imu_yaw,
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("talus_bringup"), "launch", "teleop.launch.py"]
                    )
                ),
                condition=IfCondition(enable_teleop),
                launch_arguments={
                    "joy_params_file": joy_params_file,
                    "teleop_params_file": teleop_params_file,
                    "joy_device_id": joy_device_id,
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("talus_bringup"), "launch", "kinect.launch.py"]
                    )
                ),
                condition=IfCondition(enable_kinect),
                launch_arguments={
                    "camera_parent_frame": camera_parent_frame,
                    "camera_frame": camera_frame,
                    "camera_x": camera_x,
                    "camera_y": camera_y,
                    "camera_z": camera_z,
                    "camera_roll": camera_roll,
                    "camera_pitch": camera_pitch,
                    "camera_yaw": camera_yaw,
                }.items(),
            ),
        ]
    )
