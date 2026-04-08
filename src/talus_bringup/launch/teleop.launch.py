from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    joy_params_file = LaunchConfiguration("joy_params_file")
    teleop_params_file = LaunchConfiguration("teleop_params_file")
    joy_device_id = LaunchConfiguration("joy_device_id")

    return LaunchDescription(
        [
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
            DeclareLaunchArgument("joy_device_id", default_value="0"),
            Node(
                package="joy",
                executable="joy_node",
                name="joy_node",
                output="screen",
                parameters=[
                    joy_params_file,
                    {"device_id": ParameterValue(joy_device_id, value_type=int)},
                ],
            ),
            Node(
                package="teleop_twist_joy",
                executable="teleop_node",
                name="teleop_twist_joy_node",
                output="screen",
                parameters=[teleop_params_file],
            ),
        ]
    )
