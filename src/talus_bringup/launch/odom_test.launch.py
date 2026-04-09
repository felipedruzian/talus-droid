from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    serial_port = LaunchConfiguration("serial_port")
    bridge_params_file = LaunchConfiguration("bridge_params_file")
    imu_filter_params_file = LaunchConfiguration("imu_filter_params_file")
    frames_file = LaunchConfiguration("frames_file")
    kinect_driver_mode = LaunchConfiguration("kinect_driver_mode")
    namespace = LaunchConfiguration("namespace")
    frame_id = LaunchConfiguration("frame_id")
    odom_topic = LaunchConfiguration("odom_topic")
    rgb_topic = LaunchConfiguration("rgb_topic")
    depth_topic = LaunchConfiguration("depth_topic")
    camera_info_topic = LaunchConfiguration("camera_info_topic")
    imu_topic = LaunchConfiguration("imu_topic")
    approx_sync = LaunchConfiguration("approx_sync")
    approx_sync_max_interval = LaunchConfiguration("approx_sync_max_interval")
    wait_imu_to_init = LaunchConfiguration("wait_imu_to_init")
    use_rgbd_sync = LaunchConfiguration("use_rgbd_sync")
    topic_queue_size = LaunchConfiguration("topic_queue_size")
    sync_queue_size = LaunchConfiguration("sync_queue_size")
    qos = LaunchConfiguration("qos")
    log_level = LaunchConfiguration("log_level")

    return LaunchDescription(
        [
            DeclareLaunchArgument("serial_port", default_value="/dev/ttyUSB0"),
            DeclareLaunchArgument("kinect_driver_mode", default_value="modular"),
            DeclareLaunchArgument("namespace", default_value="rtabmap"),
            DeclareLaunchArgument("frame_id", default_value="base_link"),
            DeclareLaunchArgument("odom_topic", default_value="odom"),
            DeclareLaunchArgument("rgb_topic", default_value="/image_raw"),
            DeclareLaunchArgument("depth_topic", default_value="/depth/image_raw"),
            DeclareLaunchArgument("camera_info_topic", default_value="/camera_info"),
            DeclareLaunchArgument("imu_topic", default_value="/imu/data"),
            DeclareLaunchArgument("approx_sync", default_value="true"),
            DeclareLaunchArgument("approx_sync_max_interval", default_value="0.01"),
            DeclareLaunchArgument("wait_imu_to_init", default_value="true"),
            DeclareLaunchArgument("use_rgbd_sync", default_value="false"),
            DeclareLaunchArgument("topic_queue_size", default_value="10"),
            DeclareLaunchArgument("sync_queue_size", default_value="10"),
            DeclareLaunchArgument("qos", default_value="0"),
            DeclareLaunchArgument("log_level", default_value="info"),
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
                        [FindPackageShare("talus_bringup"), "launch", "kinect.launch.py"]
                    )
                ),
                launch_arguments={
                    "frames_file": frames_file,
                    "driver_mode": kinect_driver_mode,
                }.items(),
            ),
            Node(
                package="rtabmap_sync",
                executable="rgbd_sync",
                name="rgbd_sync",
                namespace=namespace,
                output="screen",
                emulate_tty=True,
                condition=IfCondition(use_rgbd_sync),
                parameters=[
                    {
                        "approx_sync": approx_sync,
                        "approx_sync_max_interval": approx_sync_max_interval,
                        "topic_queue_size": topic_queue_size,
                        "sync_queue_size": sync_queue_size,
                        "qos": qos,
                        "qos_camera_info": qos,
                    }
                ],
                remappings=[
                    ("rgb/image", rgb_topic),
                    ("depth/image", depth_topic),
                    ("rgb/camera_info", camera_info_topic),
                    ("rgbd_image", "rgbd_image"),
                ],
            ),
            Node(
                package="rtabmap_odom",
                executable="rgbd_odometry",
                name="rgbd_odometry",
                namespace=namespace,
                output="screen",
                emulate_tty=True,
                condition=UnlessCondition(use_rgbd_sync),
                parameters=[
                    {
                        "frame_id": frame_id,
                        "odom_frame_id": odom_topic,
                        "publish_tf": True,
                        "wait_for_transform": 0.2,
                        "wait_imu_to_init": wait_imu_to_init,
                        "always_check_imu_tf": True,
                        "approx_sync": approx_sync,
                        "approx_sync_max_interval": approx_sync_max_interval,
                        "topic_queue_size": topic_queue_size,
                        "sync_queue_size": sync_queue_size,
                        "qos": qos,
                        "qos_camera_info": qos,
                        "qos_imu": qos,
                        "subscribe_rgbd": False,
                    }
                ],
                remappings=[
                    ("rgb/image", rgb_topic),
                    ("depth/image", depth_topic),
                    ("rgb/camera_info", camera_info_topic),
                    ("odom", odom_topic),
                    ("imu", imu_topic),
                ],
                arguments=[
                    "--ros-args",
                    "--log-level",
                    [namespace, ".rgbd_odometry:=", log_level],
                    "--log-level",
                    ["rgbd_odometry:=", log_level],
                ],
            ),
            Node(
                package="rtabmap_odom",
                executable="rgbd_odometry",
                name="rgbd_odometry",
                namespace=namespace,
                output="screen",
                emulate_tty=True,
                condition=IfCondition(use_rgbd_sync),
                parameters=[
                    {
                        "frame_id": frame_id,
                        "odom_frame_id": odom_topic,
                        "publish_tf": True,
                        "wait_for_transform": 0.2,
                        "wait_imu_to_init": wait_imu_to_init,
                        "always_check_imu_tf": True,
                        "approx_sync": False,
                        "topic_queue_size": topic_queue_size,
                        "sync_queue_size": sync_queue_size,
                        "qos": qos,
                        "qos_camera_info": qos,
                        "qos_imu": qos,
                        "subscribe_rgbd": True,
                    }
                ],
                remappings=[
                    ("rgbd_image", "rgbd_image"),
                    ("odom", odom_topic),
                    ("imu", imu_topic),
                ],
                arguments=[
                    "--ros-args",
                    "--log-level",
                    [namespace, ".rgbd_odometry:=", log_level],
                    "--log-level",
                    ["rgbd_odometry:=", log_level],
                ],
            ),
        ]
    )
