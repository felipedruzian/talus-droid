from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    frame_id = LaunchConfiguration("frame_id")
    rgb_topic = LaunchConfiguration("rgb_topic")
    depth_topic = LaunchConfiguration("depth_topic")
    camera_info_topic = LaunchConfiguration("camera_info_topic")
    imu_topic = LaunchConfiguration("imu_topic")
    rtabmap_viz = LaunchConfiguration("rtabmap_viz")
    rviz = LaunchConfiguration("rviz")
    approx_sync = LaunchConfiguration("approx_sync")
    wait_imu_to_init = LaunchConfiguration("wait_imu_to_init")

    return LaunchDescription(
        [
            DeclareLaunchArgument("frame_id", default_value="base_link"),
            DeclareLaunchArgument("rgb_topic", default_value="/image_raw"),
            DeclareLaunchArgument("depth_topic", default_value="/depth/image_raw"),
            DeclareLaunchArgument("camera_info_topic", default_value="/camera_info"),
            DeclareLaunchArgument("imu_topic", default_value="/imu/data"),
            DeclareLaunchArgument("rtabmap_viz", default_value="true"),
            DeclareLaunchArgument("rviz", default_value="false"),
            DeclareLaunchArgument("approx_sync", default_value="true"),
            DeclareLaunchArgument("wait_imu_to_init", default_value="true"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [FindPackageShare("rtabmap_launch"), "launch", "rtabmap.launch.py"]
                    )
                ),
                launch_arguments={
                    "frame_id": frame_id,
                    "rgb_topic": rgb_topic,
                    "depth_topic": depth_topic,
                    "camera_info_topic": camera_info_topic,
                    "imu_topic": imu_topic,
                    "rtabmap_viz": rtabmap_viz,
                    "rviz": rviz,
                    "approx_sync": approx_sync,
                    "rgbd_sync": "true",
                    "subscribe_rgbd": "true",
                    "wait_imu_to_init": wait_imu_to_init,
                    "visual_odometry": "true",
                }.items(),
            ),
        ]
    )
