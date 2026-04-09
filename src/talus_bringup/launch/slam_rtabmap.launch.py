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
    approx_sync_max_interval = LaunchConfiguration("approx_sync_max_interval")
    use_rgbd_sync = LaunchConfiguration("use_rgbd_sync")
    wait_imu_to_init = LaunchConfiguration("wait_imu_to_init")
    namespace = LaunchConfiguration("namespace")
    database_path = LaunchConfiguration("database_path")
    qos = LaunchConfiguration("qos")
    log_level = LaunchConfiguration("log_level")
    odom_log_level = LaunchConfiguration("odom_log_level")

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
            DeclareLaunchArgument("approx_sync_max_interval", default_value="0.01"),
            DeclareLaunchArgument("use_rgbd_sync", default_value="false"),
            DeclareLaunchArgument("wait_imu_to_init", default_value="true"),
            DeclareLaunchArgument("namespace", default_value="rtabmap"),
            DeclareLaunchArgument("database_path", default_value="~/.ros/rtabmap.db"),
            DeclareLaunchArgument("qos", default_value="0"),
            DeclareLaunchArgument("log_level", default_value="info"),
            DeclareLaunchArgument("odom_log_level", default_value="info"),
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
                    "namespace": namespace,
                    "database_path": database_path,
                    "rtabmap_viz": rtabmap_viz,
                    "rviz": rviz,
                    "approx_sync": approx_sync,
                    "approx_rgbd_sync": approx_sync,
                    "approx_sync_max_interval": approx_sync_max_interval,
                    "wait_imu_to_init": wait_imu_to_init,
                    "visual_odometry": "true",
                    "rgbd_sync": use_rgbd_sync,
                    "subscribe_rgbd": use_rgbd_sync,
                    "compressed": "false",
                    "qos": qos,
                    "log_level": log_level,
                    "odom_log_level": odom_log_level,
                }.items(),
            ),
        ]
    )
