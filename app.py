import os
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox

import cv2
import mss
import numpy as np


class SystemAudioCapture:
    def __init__(self):
        self.null_sink_module: str | None = None
        self.loopback_module: str | None = None
        self.original_default_sink: str | None = None

    def get_real_sink(self) -> str:
        sinks = (
            subprocess.check_output(["pactl", "list", "short", "sinks"])
            .decode()
            .splitlines()
        )
        for line in sinks:
            if "record_sink" not in line:
                return line.split("\t")[1]
        raise RuntimeError("No real audio sink found.")

    def move_firefox_to_record_sink(self) -> None:
        inputs = subprocess.check_output(["pactl", "list", "sink-inputs"]).decode()
        current_input = None
        for block in inputs.split("Sink Input #"):
            if 'application.name = "Firefox"' in block:
                lines = block.strip().splitlines()
                for line in lines:
                    if line.strip().startswith("Sink Input"):
                        current_input = line.strip().split("#")[-1]
                        break
                if not current_input:
                    lines = block.splitlines()
                    current_input = lines[0].strip()
                subprocess.run(
                    ["pactl", "move-sink-input", current_input, "record_sink"]
                )
                print(f"Moved Firefox (Sink Input #{current_input}) to record_sink")
                break

    def setup(self) -> None:
        self.original_default_sink = (
            subprocess.check_output(["pactl", "get-default-sink"]).decode().strip()
        )

        self.null_sink_module = (
            subprocess.check_output(
                [
                    "pactl",
                    "load-module",
                    "module-null-sink",
                    "sink_name=record_sink",
                    "rate=48000",
                    "channels=2",
                    "sink_properties=device.description=RecordSink",
                ]
            )
            .decode()
            .strip()
        )

        real_sink = self.get_real_sink()

        self.loopback_module = (
            subprocess.check_output(
                [
                    "pactl",
                    "load-module",
                    "module-loopback",
                    "source=record_sink.monitor",
                    f"sink={real_sink}",
                    "latency_msec=50",
                ]
            )
            .decode()
            .strip()
        )

        subprocess.run(["pactl", "set-default-sink", "record_sink"])

        # Move Firefox audio to record_sink automatically
        self.move_firefox_to_record_sink()

    def start_recording(self, output_file: str) -> subprocess.Popen:
        return subprocess.Popen(
            ["ffmpeg", "-y", "-f", "pulse", "-i", "record_sink.monitor", output_file]
        )

    def cleanup(self) -> None:
        if self.original_default_sink:
            subprocess.run(["pactl", "set-default-sink", self.original_default_sink])
        if self.loopback_module:
            subprocess.run(["pactl", "unload-module", self.loopback_module])
        if self.null_sink_module:
            subprocess.run(["pactl", "unload-module", self.null_sink_module])


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-i",
            audio_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            output_path,
        ]
    )


class ScreenRecorder:
    def __init__(self, fps: float):
        self.fps = fps
        self.recording = False
        self.output_file = f"screen_{int(time.time())}.avi"

    def _get_screen_size(self) -> tuple[int, int]:
        with mss.mss() as sct:
            mon = sct.monitors[0]
            return mon["width"], mon["height"]

    def start_recording(self) -> str:
        self.recording = True
        screen_size = self._get_screen_size()
        out = cv2.VideoWriter(
            self.output_file, cv2.VideoWriter_fourcc(*"XVID"), self.fps, screen_size
        )
        delay = 1.0 / self.fps

        with mss.mss() as sct:
            monitor = sct.monitors[0]
            while self.recording:
                start_time = time.time()
                frame = np.array(sct.grab(monitor))[:, :, :3]
                out.write(frame)
                elapsed = time.time() - start_time
                time.sleep(max(0.0, delay - elapsed))

        out.release()
        return self.output_file

    def stop(self) -> None:
        self.recording = False


class RecorderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Screen + System Audio Recorder")
        self.recorder: ScreenRecorder | None = None
        self.audio_capture = SystemAudioCapture()
        self.audio_proc: subprocess.Popen | None = None
        self.video_file: str | None = None
        self.audio_file = "audio.wav"
        self.final_file: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        tk.Label(self.root, text="FPS:").grid(row=0, column=0)
        self.fps_entry = tk.Entry(self.root)
        self.fps_entry.insert(0, "20")
        self.fps_entry.grid(row=0, column=1)

        self.status = tk.Label(self.root, text="Ready")
        self.status.grid(row=1, column=0, columnspan=2, pady=5)

        tk.Button(self.root, text="Start Recording", command=self.start_recording).grid(
            row=2, column=0
        )
        tk.Button(self.root, text="Stop Recording", command=self.stop_recording).grid(
            row=2, column=1
        )

    def start_recording(self) -> None:
        try:
            fps = float(self.fps_entry.get())
        except ValueError:
            messagebox.showerror("Invalid FPS", "Please enter a valid FPS value.")
            return

        self.recorder = ScreenRecorder(fps)
        self.audio_capture.setup()
        self.audio_proc = self.audio_capture.start_recording(self.audio_file)

        def _record():
            self.video_file = self.recorder.start_recording()

        threading.Thread(target=_record, daemon=True).start()
        self.status.config(text="Recording...")

    def stop_recording(self) -> None:
        if self.recorder:
            self.recorder.stop()
        if self.audio_proc:
            self.audio_proc.terminate()
            self.audio_proc.wait()
        self.audio_capture.cleanup()

        if self.video_file:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")]
            )
            if file_path:
                self.final_file = file_path
                merge_audio_video(self.video_file, self.audio_file, self.final_file)
                self.status.config(text=f"Saved to {self.final_file}")
                messagebox.showinfo("Done", f"Recording saved to {self.final_file}")
                folder = os.path.dirname(self.final_file)
                webbrowser.open(f"file://{folder}")


if __name__ == "__main__":
    root = tk.Tk()
    app = RecorderApp(root)
    root.mainloop()
