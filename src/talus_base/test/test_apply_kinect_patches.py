from pathlib import Path


def test_apply_kinect_patches_sets_unified_rgb_video_mode_before_starting_streams():
    script = Path(__file__).parents[3] / "scripts" / "apply-kinect-patches"

    text = script.read_text()

    assert "freenect_set_video_mode" in text
    assert "FREENECT_RESOLUTION_MEDIUM, FREENECT_VIDEO_RGB" in text
    assert "Failed to set RGB video mode" in text


def test_apply_kinect_patches_processes_freenect_events_in_background_thread():
    script = Path(__file__).parents[3] / "scripts" / "apply-kinect-patches"

    text = script.read_text()

    assert "std::thread event_thread_" in text
    assert "std::atomic_bool running_" in text
    assert "void KinectRosComponent::freenect_loop()" in text
    assert "event_thread_ = std::thread(&KinectRosComponent::freenect_loop, this);" in text
