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
    frames_file = LaunchConfiguration("frames_file")
    joy_params_file = LaunchConfiguration("joy_params_file")
    teleop_params_file = LaunchConfiguration("teleop_params_file")
    kinect_driver_mode = LaunchConfiguration("kinect_driver_mode")
    kinect_enable_point_cloud = LaunchConfiguration("kinect_enable_point_cloud")

    return LaunchDescription(
        [
            DeclareLaunchArgument("enable_teleop", default_value="true"),
            DeclareLaunchArgument("enable_kinect", default_value="false"),
            DeclareLaunchArgument("serial_port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("joy_device_id", default_value="0"),
            DeclareLaunchArgument("kinect_driver_mode", default_value="unified"),
            DeclareLaunchArgument("kinect_enable_point_cloud", default_value="false"),
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
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("talus_bringup"), "launch", "base.launch.py"]
                    )
                ),
                launch_arguments={
                    "bridge_params_file": bridge_params_file,
                    "imu_filter_params_file": imu_filter_params_file,
                    "frames_file": frames_file,
                    "serial_port": serial_port,
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
                    "frames_file": frames_file,
                    "driver_mode": kinect_driver_mode,
                    "enable_point_cloud": kinect_enable_point_cloud,
                }.items(),
            ),
        ]
    )
