"""Video capture functionality for the screen recorder."""

import logging
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

import cv2
import mss
import numpy as np

from utils import CallbackLogger, safe_remove_file


class VideoCaptureError(Exception):
    """Custom exception for video capture errors."""

    pass


class ScreenRecorder:
    """Handles screen recording with improved performance and error handling."""

    def __init__(
        self,
        fps: float,
        monitor_index: int = 1,
        codec: str = "XVID",
        quality: int = 95,
        log_callback: Callable[[str], None] | None = None,
    ):
        # Validate inputs
        if fps <= 0 or fps > 120:
            raise VideoCaptureError(f"Invalid FPS: {fps}. Must be between 0 and 120.")

        if quality < 1 or quality > 100:
            raise VideoCaptureError(
                f"Invalid quality: {quality}. Must be between 1 and 100."
            )

        self.fps = fps
        self.monitor_index = monitor_index
        self.codec = codec
        self.quality = quality
        self.recording = False
        self.paused = False
        self.output_file: str | None = None
        self.video_writer: cv2.VideoWriter | None = None
        self.recording_thread: threading.Thread | None = None

        # Performance settings
        self.frame_buffer_size = 30  # frames to buffer
        self.frame_drop_threshold = 0.1  # seconds

        # Statistics
        self.frames_recorded = 0
        self.frames_dropped = 0
        self.start_time: float | None = None

        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.callback_logger = CallbackLogger(self.logger, log_callback)

        # Validate monitor index
        self._validate_monitor_index()

    def _validate_monitor_index(self) -> None:
        """Validate that the monitor index is available."""
        try:
            with mss.mss() as sct:
                if self.monitor_index < 1 or self.monitor_index >= len(sct.monitors):
                    raise VideoCaptureError(
                        f"Invalid monitor index: {self.monitor_index}. "
                        f"Available monitors: 1-{len(sct.monitors) - 1}"
                    )
        except Exception as e:
            raise VideoCaptureError(f"Failed to validate monitor: {e}")

    def get_screen_info(self) -> dict:
        """Get information about the selected screen."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[self.monitor_index]
                return {
                    "width": monitor["width"],
                    "height": monitor["height"],
                    "left": monitor["left"],
                    "top": monitor["top"],
                }
        except Exception as e:
            raise VideoCaptureError(f"Failed to get screen info: {e}")

    def detect_screens(self) -> list[dict]:
        """Detect available screens/monitors."""
        try:
            with mss.mss() as sct:
                screens = []
                for i, monitor in enumerate(
                    sct.monitors[1:], 1
                ):  # Skip first (combined) monitor
                    screens.append(
                        {
                            "index": i,
                            "width": monitor["width"],
                            "height": monitor["height"],
                            "left": monitor["left"],
                            "top": monitor["top"],
                            "name": f"Screen {i}",
                        }
                    )
                return screens
        except Exception as e:
            raise VideoCaptureError(f"Failed to detect screens: {e}")

    def _get_codec_fourcc(self, codec: str) -> int:
        """Get OpenCV fourcc code for codec."""
        codec_map = {
            "XVID": cv2.VideoWriter_fourcc(*"XVID"),
            "MJPG": cv2.VideoWriter_fourcc(*"MJPG"),
            "mp4v": cv2.VideoWriter_fourcc(*"mp4v"),
            "H264": cv2.VideoWriter_fourcc(*"H264"),
            "VP80": cv2.VideoWriter_fourcc(*"VP80"),
            "VP90": cv2.VideoWriter_fourcc(*"VP90"),
        }

        if codec not in codec_map:
            self.callback_logger.warning(f"Unknown codec '{codec}', using XVID")
            return codec_map["XVID"]

        return codec_map[codec]

    def _create_video_writer(
        self, output_file: str, screen_size: tuple[int, int]
    ) -> cv2.VideoWriter:
        """Create and validate video writer."""
        fourcc = self._get_codec_fourcc(self.codec)

        writer = cv2.VideoWriter(output_file, fourcc, self.fps, screen_size)

        if not writer.isOpened():
            raise VideoCaptureError(
                f"Failed to create video writer with codec {self.codec}"
            )

        return writer

    def _recording_loop(self) -> None:
        """Main recording loop running in separate thread."""
        try:
            screen_info = self.get_screen_info()
            screen_size = (screen_info["width"], screen_info["height"])

            self.video_writer = self._create_video_writer(self.output_file, screen_size)
            frame_delay = 1.0 / self.fps

            self.callback_logger.info(
                f"Recording started: {screen_size[0]}x{screen_size[1]} @ {self.fps}fps"
            )

            with mss.mss() as sct:
                monitor = sct.monitors[self.monitor_index]

                while self.recording:
                    if self.paused:
                        time.sleep(0.1)
                        continue

                    frame_start = time.time()

                    try:
                        # Capture frame
                        screenshot = sct.grab(monitor)
                        frame = np.array(screenshot)[:, :, :3]  # Remove alpha channel

                        # MSS captures in BGRA format, removing alpha gives us BGR
                        # OpenCV VideoWriter expects BGR format, so no conversion needed

                        # Write frame
                        self.video_writer.write(frame)
                        self.frames_recorded += 1

                        # Frame timing - ensure consistent frame rate
                        frame_time = time.time() - frame_start
                        sleep_time = max(0.0, frame_delay - frame_time)

                        # Always sleep for the remaining frame time to maintain consistent FPS
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                        elif frame_time > frame_delay + self.frame_drop_threshold:
                            # Only count as dropped if significantly over time
                            self.frames_dropped += 1
                            self.logger.debug(
                                f"Frame processing took {frame_time:.3f}s (target: {frame_delay:.3f}s)"
                            )

                    except Exception as e:
                        self.callback_logger.error(f"Error capturing frame: {e}")
                        break

            # Clean up video writer
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

            # Check if video file was created and has content
            if self.output_file and Path(self.output_file).exists():
                file_size = Path(self.output_file).stat().st_size
                self.callback_logger.info(
                    f"Video file created: {self.output_file} ({file_size} bytes)"
                )
            else:
                self.callback_logger.error(
                    f"Video file was not created: {self.output_file}"
                )

            # Log statistics
            total_time = time.time() - self.start_time if self.start_time else 0
            self.callback_logger.info(
                f"Recording completed: {self.frames_recorded} frames, "
                f"{self.frames_dropped} dropped, {total_time:.1f}s"
            )

        except Exception as e:
            self.callback_logger.error(f"Recording failed: {e}")
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

    def start_recording(self, output_file: str) -> str:
        """Start screen recording."""
        if self.recording:
            raise VideoCaptureError("Recording already in progress")

        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        self.output_file = output_file
        self.recording = True
        self.paused = False
        self.frames_recorded = 0
        self.frames_dropped = 0
        self.start_time = time.time()

        # Start recording in separate thread
        self.recording_thread = threading.Thread(
            target=self._recording_loop, daemon=True
        )
        self.recording_thread.start()

        return output_file

    def pause_recording(self) -> None:
        """Pause the recording."""
        if not self.recording:
            raise VideoCaptureError("No recording in progress")

        self.paused = not self.paused
        status = "paused" if self.paused else "resumed"
        self.callback_logger.info(f"Recording {status}")

    def stop_recording(self) -> str | None:
        """Stop recording and return output file path."""
        if not self.recording:
            return None

        self.recording = False
        self.paused = False

        # Wait for recording thread to finish with a shorter timeout
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2.0)
            if self.recording_thread.is_alive():
                self.callback_logger.warning("Recording thread did not stop gracefully")
                # Force cleanup if thread is still running
                if self.video_writer:
                    try:
                        self.video_writer.release()
                        self.video_writer = None
                    except Exception as e:
                        self.callback_logger.error(f"Error releasing video writer: {e}")

        output_file = self.output_file
        self.output_file = None

        return output_file

    def get_recording_stats(self) -> dict:
        """Get current recording statistics."""
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        return {
            "recording": self.recording,
            "paused": self.paused,
            "frames_recorded": self.frames_recorded,
            "frames_dropped": self.frames_dropped,
            "elapsed_time": elapsed_time,
            "fps_actual": self.frames_recorded / elapsed_time
            if elapsed_time > 0
            else 0,
            "drop_rate": self.frames_dropped / max(1, self.frames_recorded) * 100,
        }


def merge_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    video_codec: str = "copy",
    audio_codec: str = "aac",
    audio_delay_ms: int = 100,
    log_callback: Callable[[str], None] | None = None,
) -> bool:
    """Merge audio and video files using FFmpeg."""

    logger = logging.getLogger(__name__)
    callback_logger = CallbackLogger(logger, log_callback)

    try:
        # Validate input files exist
        if not Path(video_path).exists():
            raise VideoCaptureError(f"Video file not found: {video_path}")

        if not Path(audio_path).exists():
            raise VideoCaptureError(f"Audio file not found: {audio_path}")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        callback_logger.info("Merging audio and video...")

        # Handle audio delay compensation
        if audio_delay_ms != 0:
            if audio_delay_ms > 0:
                # Positive delay - delay audio
                filter_complex = (
                    f"[1:a]adelay={audio_delay_ms}|{audio_delay_ms}[delayed_audio]"
                )
                audio_map = "[delayed_audio]"
            else:
                # Negative delay - advance audio (delay video)
                video_delay = abs(audio_delay_ms)
                filter_complex = (
                    f"[0:v]tpad=start_duration={video_delay / 1000}[delayed_video]"
                )
                audio_map = "1:a"

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-i",
                audio_path,
                "-c:v",
                video_codec,
                "-c:a",
                audio_codec,
                "-b:a",
                "128k",
                "-filter_complex",
                filter_complex,
                "-map",
                "[delayed_video]" if audio_delay_ms < 0 else "0:v",
                "-map",
                audio_map,
                "-shortest",
                output_path,
            ]
        else:
            # No delay needed
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-i",
                audio_path,
                "-c:v",
                video_codec,
                "-c:a",
                audio_codec,
                "-b:a",
                "128k",
                "-shortest",
                output_path,
            ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout for long recordings
        )

        if result.returncode == 0:
            # Check if output file was actually created and has reasonable size
            if Path(output_path).exists():
                output_size = Path(output_path).stat().st_size
                callback_logger.info(
                    f"Successfully merged to: {output_path} ({output_size} bytes)"
                )
                return True
            else:
                callback_logger.error("FFmpeg completed but no output file was created")
                return False
        else:
            callback_logger.error(f"FFmpeg merge failed (code {result.returncode})")
            callback_logger.error(f"FFmpeg stderr: {result.stderr}")
            callback_logger.error(f"FFmpeg stdout: {result.stdout}")
            return False

    except subprocess.TimeoutExpired:
        callback_logger.error("Merge operation timed out")
        return False
    except Exception as e:
        callback_logger.error(f"Merge failed: {e}")
        return False


def cleanup_temp_files(
    files: list[str], log_callback: Callable[[str], None] | None = None
) -> int:
    """Clean up temporary files."""

    logger = logging.getLogger(__name__)
    callback_logger = CallbackLogger(logger, log_callback)

    cleaned_count = 0

    for file_path in files:
        if safe_remove_file(file_path, logger):
            cleaned_count += 1
        else:
            callback_logger.warning(f"Failed to remove temporary file: {file_path}")

    if cleaned_count > 0:
        callback_logger.info(f"Cleaned up {cleaned_count} temporary files")

    return cleaned_count
