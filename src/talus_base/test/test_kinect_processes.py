from talus_base.kinect_validation.processes import find_relevant_process_lines


def test_finds_ros_kinect_and_rtabmap_processes():
    ps_text = """\
felip 100 1 0 ? 00:00:01 /usr/bin/python3 /opt/ros/jazzy/bin/ros2 launch talus_bringup kinect.launch.py
felip 101 1 0 ? 00:00:01 /home/felip/talus-droid/install/kinect_ros2/lib/kinect_ros2/kinect_ros2_node
felip 102 1 0 ? 00:00:01 /opt/ros/jazzy/lib/rtabmap_odom/rgbd_odometry
root  200 1 0 ? 00:00:00 /usr/sbin/sshd
"""
    lines = find_relevant_process_lines(ps_text)
    assert len(lines) == 3
    assert all("sshd" not in line for line in lines)


def test_ignores_empty_and_header_lines():
    assert find_relevant_process_lines("PID CMD\n") == []


def test_ignores_own_diagnostic_runner_processes():
    ps_text = """\
103682 103681 Ssl ros2 /usr/bin/python3 /opt/ros/jazzy/bin/ros2 run talus_base talus_kinect_validate preflight
103701 103682 S talus_kinect_va /usr/bin/python3 /home/felip/talus-droid/install/talus_base/lib/talus_base/talus_kinect_validate preflight
103900 103682 S talus_kinect_sa /usr/bin/python3 /home/felip/talus-droid/install/talus_base/lib/talus_base/talus_kinect_sample_image /image_raw
"""
    assert find_relevant_process_lines(ps_text) == []
