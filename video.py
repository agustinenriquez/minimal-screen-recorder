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
        video_writer = None
        try:
            self.callback_logger.info("=== VIDEO RECORDING LOOP STARTED ===")
            screen_info = self.get_screen_info()
            screen_size = (screen_info["width"], screen_info["height"])
            self.callback_logger.info(f"Screen info: {screen_info}")

            self.callback_logger.info(f"Creating video writer for: {self.output_file}")
            video_writer = self._create_video_writer(self.output_file, screen_size)
            self.video_writer = video_writer  # Store reference for external access
            frame_delay = 1.0 / self.fps
            self.callback_logger.info(
                f"Video writer created successfully. Frame delay: {frame_delay}s"
            )

            self.callback_logger.info(
                f"Recording started: {screen_size[0]}x{screen_size[1]} @ {self.fps}fps"
            )

            consecutive_errors = 0
            max_consecutive_errors = 10

            with mss.mss() as sct:
                monitor = sct.monitors[self.monitor_index]

                while self.recording and consecutive_errors < max_consecutive_errors:
                    if self.paused:
                        time.sleep(0.1)
                        consecutive_errors = 0  # Reset error count when paused
                        continue

                    frame_start = time.time()

                    try:
                        # Capture frame
                        screenshot = sct.grab(monitor)
                        frame = np.array(screenshot)[:, :, :3]  # Remove alpha channel

                        # MSS captures in BGRA format, removing alpha gives us BGR
                        # OpenCV VideoWriter expects BGR format, so no conversion needed

                        # Verify frame dimensions match expected size
                        if frame.shape[:2] != (screen_size[1], screen_size[0]):
                            self.callback_logger.warning(
                                f"Frame size mismatch: got {frame.shape[:2]}, expected {(screen_size[1], screen_size[0])}"
                            )
                            continue

                        # Write frame - ensure writer is still valid
                        if video_writer and video_writer.isOpened():
                            video_writer.write(frame)
                            self.frames_recorded += 1
                            consecutive_errors = (
                                0  # Reset error count on successful write
                            )

                            # Log every 60 frames (about once per second at 60fps)
                            if self.frames_recorded % 60 == 0:
                                self.callback_logger.info(
                                    f"Recorded {self.frames_recorded} frames"
                                )
                        else:
                            self.callback_logger.error(
                                "Video writer is not opened, stopping recording"
                            )
                            break

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
                        consecutive_errors += 1
                        self.callback_logger.error(
                            f"Error capturing frame (attempt {consecutive_errors}/{max_consecutive_errors}): {e}"
                        )
                        if consecutive_errors >= max_consecutive_errors:
                            self.callback_logger.error(
                                "Too many consecutive errors, stopping recording"
                            )
                            break
                        # Small delay before retrying
                        time.sleep(0.1)

            self.callback_logger.info(
                f"=== RECORDING LOOP ENDED - Recorded {self.frames_recorded} frames ==="
            )
            # Ensure we have some frames before considering this a successful recording
            if self.frames_recorded == 0:
                self.callback_logger.error("ERROR: No frames were recorded")

        except Exception as e:
            self.callback_logger.error(f"Recording failed with exception: {e}")
            import traceback

            self.callback_logger.error(f"Traceback: {traceback.format_exc()}")

        finally:
            # Always clean up video writer in finally block to ensure proper file closure
            self.callback_logger.info("=== VIDEO WRITER CLEANUP STARTED ===")
            try:
                if video_writer:
                    self.callback_logger.info("Releasing video writer...")
                    video_writer.release()
                    # Add a small delay to ensure file is fully written to disk
                    time.sleep(0.5)
                    self.callback_logger.info("Video writer released successfully")
                else:
                    self.callback_logger.warning("Video writer was None during cleanup")
            except Exception as e:
                self.callback_logger.error(
                    f"Error releasing video writer in finally block: {e}"
                )
            finally:
                self.video_writer = None
                self.callback_logger.info("Video writer reference cleared")

            # Check if video file was created and has content
            if self.output_file and Path(self.output_file).exists():
                file_size = Path(self.output_file).stat().st_size
                self.callback_logger.info(
                    f"✓ Video file created: {self.output_file} ({file_size} bytes, {self.frames_recorded} frames)"
                )
            else:
                self.callback_logger.error(
                    f"✗ Video file was not created: {self.output_file}"
                )

            # Log statistics
            total_time = time.time() - self.start_time if self.start_time else 0
            self.callback_logger.info(
                f"=== RECORDING STATS: {self.frames_recorded} frames, "
                f"{self.frames_dropped} dropped, {total_time:.1f}s ==="
            )

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
        self.callback_logger.info("=== STOP RECORDING CALLED ===")
        if not self.recording:
            self.callback_logger.warning(
                "Stop recording called but not currently recording"
            )
            return None

        self.callback_logger.info("Setting recording=False and paused=False")
        self.recording = False
        self.paused = False

        # Wait for recording thread to finish with a longer timeout for proper cleanup
        if self.recording_thread and self.recording_thread.is_alive():
            self.callback_logger.info("Waiting for recording thread to finish...")
            self.recording_thread.join(
                timeout=10.0
            )  # Increased timeout to allow proper file finalization
            if self.recording_thread.is_alive():
                self.callback_logger.warning(
                    "Recording thread did not stop gracefully within 10 seconds"
                )
                # Try a final attempt to stop the thread cleanly
                self.recording_thread.join(timeout=5.0)
                if self.recording_thread.is_alive():
                    self.callback_logger.error(
                        "Recording thread is stuck, forcing cleanup"
                    )
                    # Force cleanup if thread is still running
                    if self.video_writer:
                        try:
                            self.video_writer.release()
                            self.video_writer = None
                        except Exception as e:
                            self.callback_logger.error(
                                f"Error releasing video writer: {e}"
                            )
            else:
                self.callback_logger.info("Recording thread stopped gracefully")

        # Ensure video writer is properly released even if thread finished normally
        if self.video_writer:
            try:
                self.callback_logger.info(
                    "Additional video writer cleanup in stop_recording"
                )
                self.video_writer.release()
                self.video_writer = None
                self.callback_logger.info(
                    "Video writer properly released in stop_recording"
                )
            except Exception as e:
                self.callback_logger.error(f"Error releasing video writer: {e}")

        output_file = self.output_file
        self.output_file = None
        self.callback_logger.info(f"Output file path: {output_file}")

        # Validate the output file was created and has content
        if output_file:
            file_path = Path(output_file)
            if file_path.exists():
                file_size = file_path.stat().st_size
                # Check if file has reasonable size (at least 1KB per second of recording)
                min_expected_size = max(
                    1024, self.frames_recorded * 100
                )  # Very conservative estimate
                if file_size < min_expected_size:
                    self.callback_logger.warning(
                        f"⚠️ Video file may be incomplete: {file_size} bytes (expected at least {min_expected_size})"
                    )
                else:
                    self.callback_logger.info(
                        f"✓ Video file appears complete: {file_size} bytes"
                    )
            else:
                self.callback_logger.error(
                    f"✗ Video file was not created: {output_file}"
                )

        self.callback_logger.info("=== STOP RECORDING COMPLETED ===")
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
    progress_callback: Callable[[float, str], None] | None = None,
) -> bool:
    """Merge audio and video files using FFmpeg."""

    logger = logging.getLogger(__name__)
    callback_logger = CallbackLogger(logger, log_callback)

    try:
        callback_logger.info("=== FFMPEG MERGE STARTED ===")
        callback_logger.info(f"Video input: {video_path}")
        callback_logger.info(f"Audio input: {audio_path}")
        callback_logger.info(f"Output path: {output_path}")

        # Validate input files exist
        if not Path(video_path).exists():
            raise VideoCaptureError(f"Video file not found: {video_path}")

        if not Path(audio_path).exists():
            raise VideoCaptureError(f"Audio file not found: {audio_path}")

        # Log file sizes
        video_size = Path(video_path).stat().st_size
        audio_size = Path(audio_path).stat().st_size
        callback_logger.info(f"Video file size: {video_size} bytes")
        callback_logger.info(f"Audio file size: {audio_size} bytes")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        callback_logger.info("Starting FFmpeg merge process...")

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
                output_path,
            ]
        else:
            # No delay needed - removed -shortest flag to prevent premature ending
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
                output_path,
            ]

        # Get video duration for progress calculation
        total_duration = None
        if progress_callback:
            try:
                # Get duration using ffprobe
                duration_cmd = [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "csv=p=0",
                    video_path,
                ]
                duration_result = subprocess.run(
                    duration_cmd, capture_output=True, text=True, timeout=30
                )
                if duration_result.returncode == 0:
                    total_duration = float(duration_result.stdout.strip())
                    callback_logger.info(
                        f"Video duration: {total_duration:.2f} seconds"
                    )
            except (ValueError, subprocess.TimeoutExpired) as e:
                callback_logger.warning(f"Could not get video duration: {e}")

        # Run FFmpeg with progress monitoring
        if progress_callback:
            if total_duration:
                # Use progress format for real-time monitoring with longer timeout for big files
                cmd.extend(["-progress", "pipe:1"])

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                )

                progress_callback(0.0, "Starting merge...")

                current_time = 0.0
                last_progress = 0.0
                last_output_time = time.time()

                # Monitor progress output with timeout detection
                try:
                    while True:
                        # Check if process is still running
                        if process.poll() is not None:
                            callback_logger.info("FFmpeg process has finished")
                            break

                        # Read with timeout to detect hanging
                        import select
                        import sys

                        if sys.platform != "win32":
                            # Use select on Unix-like systems
                            ready, _, _ = select.select([process.stdout], [], [], 1.0)
                            if ready:
                                output = process.stdout.readline()
                                if output:
                                    last_output_time = time.time()
                                    line = output.strip()
                                    callback_logger.debug(f"FFmpeg output: {line}")

                                    # Parse FFmpeg progress output
                                    if line.startswith("out_time_ms="):
                                        try:
                                            time_ms = int(line.split("=")[1])
                                            current_time = (
                                                time_ms / 1000000.0
                                            )  # Convert microseconds to seconds

                                            if total_duration > 0:
                                                progress_percent = min(
                                                    (current_time / total_duration)
                                                    * 100,
                                                    100.0,
                                                )
                                                # Only update if progress increased significantly (reduces UI updates)
                                                if (
                                                    progress_percent - last_progress
                                                    >= 1.0
                                                ):
                                                    progress_callback(
                                                        progress_percent,
                                                        f"Processing: {current_time:.1f}s / {total_duration:.1f}s",
                                                    )
                                                    callback_logger.info(
                                                        f"FFmpeg progress: {progress_percent:.1f}%"
                                                    )
                                                    last_progress = progress_percent
                                        except (ValueError, IndexError):
                                            continue
                                elif output == "":
                                    callback_logger.info("FFmpeg stdout closed")
                                    break
                            else:
                                # No output for 1 second, check timeout
                                if (
                                    time.time() - last_output_time > 60
                                ):  # 60 second timeout
                                    callback_logger.warning(
                                        "FFmpeg appears to be hanging (no output for 60s)"
                                    )
                                    callback_logger.info("Terminating FFmpeg process")
                                    process.terminate()
                                    time.sleep(2)
                                    if process.poll() is None:
                                        callback_logger.warning(
                                            "Force killing FFmpeg process"
                                        )
                                        process.kill()
                                    return False
                        else:
                            # Windows fallback - simpler approach
                            output = process.stdout.readline()
                            if output == "" and process.poll() is not None:
                                break
                            if output:
                                line = output.strip()
                                if line.startswith("out_time_ms="):
                                    try:
                                        time_ms = int(line.split("=")[1])
                                        current_time = time_ms / 1000000.0
                                        if total_duration > 0:
                                            progress_percent = min(
                                                (current_time / total_duration) * 100,
                                                100.0,
                                            )
                                            if progress_percent - last_progress >= 1.0:
                                                progress_callback(
                                                    progress_percent,
                                                    f"Processing: {current_time:.1f}s / {total_duration:.1f}s",
                                                )
                                                last_progress = progress_percent
                                    except (ValueError, IndexError):
                                        continue

                    # Wait for process completion
                    stderr_output = process.communicate()[1]
                    return_code = process.returncode
                    callback_logger.info(
                        f"FFmpeg finished with return code: {return_code}"
                    )

                except Exception as e:
                    callback_logger.error(f"Error monitoring FFmpeg progress: {e}")
                    try:
                        process.terminate()
                        time.sleep(2)
                        if process.poll() is None:
                            process.kill()
                    except Exception:
                        pass
                    return False
            else:
                # Show indeterminate progress when duration is unknown
                progress_callback(50.0, "Processing video... (duration unknown)")

                # Fallback to simple execution without detailed progress
                # Calculate timeout based on video duration (at least 10 minutes, max 2 hours)
                timeout_seconds = (
                    max(600, min(7200, total_duration * 3)) if total_duration else 3600
                )
                callback_logger.info(f"FFmpeg timeout set to {timeout_seconds} seconds")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                return_code = result.returncode
                stderr_output = result.stderr
        else:
            # Fallback to simple execution without progress
            # Use conservative timeout for long files
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200,  # 2 hour timeout for very long recordings
            )
            return_code = result.returncode
            stderr_output = result.stderr

        if return_code == 0:
            # Check if output file was actually created and has reasonable size
            if Path(output_path).exists():
                output_size = Path(output_path).stat().st_size
                if progress_callback:
                    progress_callback(100.0, "Processing complete!")
                callback_logger.info(
                    f"✓ Successfully merged to: {output_path} ({output_size} bytes)"
                )
                callback_logger.info("=== FFMPEG MERGE COMPLETED SUCCESSFULLY ===")
                return True
            else:
                callback_logger.error(
                    "✗ FFmpeg completed but no output file was created"
                )
                callback_logger.error("=== FFMPEG MERGE FAILED - NO OUTPUT ===")
                return False
        else:
            callback_logger.error(f"✗ FFmpeg merge failed (code {return_code})")
            if stderr_output:
                callback_logger.error(f"FFmpeg stderr: {stderr_output}")
            callback_logger.error("=== FFMPEG MERGE FAILED ===")
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
