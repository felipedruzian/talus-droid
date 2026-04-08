from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    enable_camera_tf = LaunchConfiguration("enable_camera_tf")
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
            DeclareLaunchArgument("enable_camera_tf", default_value="true"),
            DeclareLaunchArgument("camera_parent_frame", default_value="base_link"),
            DeclareLaunchArgument("camera_frame", default_value="camera_link"),
            DeclareLaunchArgument("camera_x", default_value="0.0"),
            DeclareLaunchArgument("camera_y", default_value="0.0"),
            DeclareLaunchArgument("camera_z", default_value="0.0"),
            DeclareLaunchArgument("camera_roll", default_value="0.0"),
            DeclareLaunchArgument("camera_pitch", default_value="0.0"),
            DeclareLaunchArgument("camera_yaw", default_value="0.0"),
            Node(
                package="kinect_ros2",
                executable="kinect_ros2_node",
                name="kinect_ros2_node",
                output="screen",
            ),
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name="kinect_static_tf",
                output="screen",
                condition=IfCondition(enable_camera_tf),
                arguments=[
                    "--x",
                    camera_x,
                    "--y",
                    camera_y,
                    "--z",
                    camera_z,
                    "--roll",
                    camera_roll,
                    "--pitch",
                    camera_pitch,
                    "--yaw",
                    camera_yaw,
                    "--frame-id",
                    camera_parent_frame,
                    "--child-frame-id",
                    camera_frame,
                ],
            ),
        ]
    )
