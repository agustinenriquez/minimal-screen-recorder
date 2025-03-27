import os
import subprocess

import pytest

AUDIO_FILE = "test_output.wav"
MONITOR_NAME = "record_sink.monitor"


@pytest.fixture(scope="module", autouse=True)
def cleanup_audio_file():
    # Run before test module
    yield
    # Run after test module
    if os.path.exists(AUDIO_FILE):
        os.remove(AUDIO_FILE)


def test_monitor_exists():
    """Check if record_sink.monitor exists"""
    output = subprocess.check_output(["pactl", "list", "short", "sources"]).decode()
    assert MONITOR_NAME in output, (
        f"{MONITOR_NAME} not found. Make sure 'record_sink' is loaded."
    )


def test_audio_recording():
    """Record from record_sink.monitor and verify output file exists"""
    # Use ffmpeg to record 2 seconds of system audio
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-y",  # Overwrite if exists
            "-f",
            "pulse",
            "-i",
            MONITOR_NAME,
            "-t",
            "2",
            AUDIO_FILE,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    proc.wait()

    # Basic checks
    assert os.path.exists(AUDIO_FILE), "Audio file was not created."
    assert os.path.getsize(AUDIO_FILE) > 1000, "Audio file is empty or too small."


VIDEO_FILE = "test_output.avi"
FPS = 30


@pytest.mark.skipif(not os.path.exists(AUDIO_FILE), reason="Audio file not found.")
def test_video_recording():
    """Record video and verify output file exists"""
    from app import ScreenRecorder

    recorder = ScreenRecorder(FPS)
    output_file = recorder.start_recording()
    recorder.stop()

    assert os.path.exists(output_file), "Video file was not created."
    assert os.path.getsize(output_file) > 1000, "Video file is empty or too small."

    # Cleanup
    os.remove(output_file)


@pytest.mark.skipif(
    not os.path.exists(VIDEO_FILE), reason="Merged output video not found"
)
def test_video_has_audio_stream():
    """Check that the merged video contains at least one audio stream"""
    try:
        result = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                VIDEO_FILE,
            ]
        )
        audio_streams = result.decode().strip().splitlines()
        assert len(audio_streams) > 0, "No audio streams found in the video."
    except subprocess.CalledProcessError as e:
        pytest.fail(f"ffprobe failed: {e}")


@pytest.mark.skipif(
    not os.path.exists(VIDEO_FILE), reason="Merged output video not found"
)
def test_video_has_video_stream():
    """Check that the merged video contains at least one video stream"""
    try:
        result = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                VIDEO_FILE,
            ]
        )
        video_streams = result.decode().strip().splitlines()
        assert len(video_streams) > 0, "No video streams found in the file."
    except subprocess.CalledProcessError as e:
        pytest.fail(f"ffprobe failed: {e}")
