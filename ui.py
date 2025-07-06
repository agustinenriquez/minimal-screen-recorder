"""Enhanced UI for the screen recorder with better UX and controls."""

import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from audio import AudioCaptureError, SystemAudioCapture
from config import ConfigManager
from utils import (
    RecordingTimer,
    check_dependencies,
    get_incremental_filename,
    setup_logging,
    validate_fps,
)
from video import (
    ScreenRecorder,
    VideoCaptureError,
    cleanup_temp_files,
    merge_audio_video,
)


class ProgressWindow:
    """Separate window showing recording progress."""

    def __init__(self, parent, timer: RecordingTimer):
        self.parent = parent
        self.timer = timer
        self.window = tk.Toplevel(parent)
        self.window.title("Recording Progress")
        self.window.geometry("300x200")
        self.window.configure(bg="#1e1e1e")
        self.window.resizable(False, False)

        # Make window stay on top
        self.window.attributes("-topmost", True)

        self._setup_ui()
        self._update_progress()

    def _setup_ui(self):
        """Set up the progress window UI."""
        style = {"bg": "#1e1e1e", "fg": "#ffffff"}

        # Status label
        self.status_label = tk.Label(
            self.window, text="🔴 RECORDING", font=("Arial", 12), **style
        )
        self.status_label.pack(pady=10)

        # Time label
        self.time_label = tk.Label(
            self.window, text="00:00:00", font=("Arial", 20, "bold"), **style
        )
        self.time_label.pack(pady=10)

        # Progress info
        self.info_label = tk.Label(self.window, text="", font=("Arial", 10), **style)
        self.info_label.pack(pady=5)

        # Control buttons
        button_frame = tk.Frame(self.window, bg="#1e1e1e")
        button_frame.pack(pady=10)

        btn_style = {"bg": "#3a3a3a", "fg": "white", "activebackground": "#5a5a5a"}

        self.pause_btn = tk.Button(button_frame, text="⏸️ Pause", **btn_style)
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(button_frame, text="⏹️ Stop", **btn_style)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

    def _update_progress(self):
        """Update progress display."""
        if self.timer.is_running:
            elapsed = self.timer.get_formatted_elapsed()
            self.time_label.config(text=elapsed)

            # Schedule next update
            self.window.after(1000, self._update_progress)

    def update_info(self, text: str):
        """Update the info label."""
        self.info_label.config(text=text)

    def set_paused(self, paused: bool):
        """Update UI for pause state."""
        if paused:
            self.status_label.config(text="⏸️ PAUSED")
            self.pause_btn.config(text="▶️ Resume")
        else:
            self.status_label.config(text="🔴 RECORDING")
            self.pause_btn.config(text="⏸️ Pause")

    def close(self):
        """Close the progress window."""
        self.window.destroy()


class SettingsWindow:
    """Settings configuration window."""

    def __init__(self, parent, config_manager: ConfigManager):
        self.parent = parent
        self.config_manager = config_manager
        self.config = config_manager.config

        self.window = tk.Toplevel(parent)
        self.window.title("Settings")
        self.window.geometry("500x600")
        self.window.configure(bg="#1e1e1e")
        self.window.resizable(False, False)

        # Make modal
        self.window.transient(parent)
        self.window.grab_set()

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """Set up the settings window UI."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Video settings tab
        self.video_frame = tk.Frame(self.notebook, bg="#1e1e1e")
        self.notebook.add(self.video_frame, text="Video")
        self._setup_video_tab()

        # Audio settings tab
        self.audio_frame = tk.Frame(self.notebook, bg="#1e1e1e")
        self.notebook.add(self.audio_frame, text="Audio")
        self._setup_audio_tab()

        # General settings tab
        self.general_frame = tk.Frame(self.notebook, bg="#1e1e1e")
        self.notebook.add(self.general_frame, text="General")
        self._setup_general_tab()

        # Buttons
        self._setup_buttons()

    def _setup_video_tab(self):
        """Set up video settings tab."""
        style = {"bg": "#1e1e1e", "fg": "#ffffff"}
        entry_style = {"bg": "#2e2e2e", "fg": "#ffffff", "insertbackground": "white"}

        row = 0

        # Codec selection
        tk.Label(self.video_frame, text="Video Codec:", **style).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.codec_var = tk.StringVar()
        codec_combo = ttk.Combobox(
            self.video_frame, textvariable=self.codec_var, state="readonly"
        )
        codec_combo["values"] = list(self.config_manager.get_video_codecs().keys())
        codec_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Quality setting
        tk.Label(self.video_frame, text="Quality (1-100):", **style).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.quality_var = tk.StringVar()
        tk.Entry(self.video_frame, textvariable=self.quality_var, **entry_style).grid(
            row=row, column=1, sticky="w", padx=5, pady=5
        )
        row += 1

        # Output format
        tk.Label(self.video_frame, text="Output Format:", **style).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.format_var = tk.StringVar()
        format_combo = ttk.Combobox(
            self.video_frame, textvariable=self.format_var, state="readonly"
        )
        format_combo["values"] = self.config_manager.get_output_formats()
        format_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)

    def _setup_audio_tab(self):
        """Set up audio settings tab."""
        style = {"bg": "#1e1e1e", "fg": "#ffffff"}
        entry_style = {"bg": "#2e2e2e", "fg": "#ffffff", "insertbackground": "white"}

        row = 0

        # Sample rate
        tk.Label(self.audio_frame, text="Sample Rate:", **style).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.sample_rate_var = tk.StringVar()
        rate_combo = ttk.Combobox(
            self.audio_frame, textvariable=self.sample_rate_var, state="readonly"
        )
        rate_combo["values"] = ["22050", "44100", "48000", "96000"]
        rate_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Channels
        tk.Label(self.audio_frame, text="Channels:", **style).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.channels_var = tk.StringVar()
        channels_combo = ttk.Combobox(
            self.audio_frame, textvariable=self.channels_var, state="readonly"
        )
        channels_combo["values"] = ["1 (Mono)", "2 (Stereo)"]
        channels_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Bitrate
        tk.Label(self.audio_frame, text="Bitrate:", **style).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.bitrate_var = tk.StringVar()
        bitrate_combo = ttk.Combobox(
            self.audio_frame, textvariable=self.bitrate_var, state="readonly"
        )
        bitrate_combo["values"] = ["64k", "128k", "192k", "256k", "320k"]
        bitrate_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Audio delay compensation
        tk.Label(self.audio_frame, text="Audio Delay (ms):", **style).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.audio_delay_var = tk.StringVar()
        delay_frame = tk.Frame(self.audio_frame, bg="#1e1e1e")
        delay_frame.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        tk.Entry(
            delay_frame, textvariable=self.audio_delay_var, width=10, **entry_style
        ).pack(side=tk.LEFT)
        tk.Label(
            delay_frame,
            text="(+delay audio, -advance audio)",
            font=("Arial", 8),
            **style,
        ).pack(side=tk.LEFT, padx=(5, 0))

    def _setup_general_tab(self):
        """Set up general settings tab."""
        style = {"bg": "#1e1e1e", "fg": "#ffffff"}
        entry_style = {"bg": "#2e2e2e", "fg": "#ffffff", "insertbackground": "white"}

        row = 0

        # Output directory
        tk.Label(self.general_frame, text="Output Directory:", **style).grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.output_dir_var = tk.StringVar()
        dir_frame = tk.Frame(self.general_frame, bg="#1e1e1e")
        dir_frame.grid(row=row, column=1, sticky="w", padx=5, pady=5)

        tk.Entry(
            dir_frame, textvariable=self.output_dir_var, width=30, **entry_style
        ).pack(side=tk.LEFT)
        tk.Button(
            dir_frame,
            text="Browse",
            command=self._browse_directory,
            bg="#3a3a3a",
            fg="white",
        ).pack(side=tk.LEFT, padx=(5, 0))
        row += 1

        # Debug mode
        self.debug_var = tk.BooleanVar()
        tk.Checkbutton(
            self.general_frame, text="Debug Mode", variable=self.debug_var, **style
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        row += 1

        # Auto increment filename
        self.auto_increment_var = tk.BooleanVar()
        tk.Checkbutton(
            self.general_frame,
            text="Auto-increment filenames",
            variable=self.auto_increment_var,
            **style,
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=5)

    def _setup_buttons(self):
        """Set up OK/Cancel buttons."""
        button_frame = tk.Frame(self.window, bg="#1e1e1e")
        button_frame.pack(pady=10)

        btn_style = {"bg": "#3a3a3a", "fg": "white", "activebackground": "#5a5a5a"}

        tk.Button(
            button_frame, text="OK", command=self._save_settings, **btn_style
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=self._cancel, **btn_style).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self._reset_defaults,
            **btn_style,
        ).pack(side=tk.LEFT, padx=5)

    def _load_current_settings(self):
        """Load current settings into UI."""
        self.codec_var.set(self.config.video_codec)
        self.quality_var.set(str(self.config.video_quality))
        self.format_var.set(self.config.output_format)
        self.sample_rate_var.set(str(self.config.audio_sample_rate))
        self.channels_var.set(
            f"{self.config.audio_channels} ({'Mono' if self.config.audio_channels == 1 else 'Stereo'})"
        )
        self.bitrate_var.set(self.config.audio_bitrate)
        self.audio_delay_var.set(str(self.config.audio_delay_ms))
        self.output_dir_var.set(self.config.output_directory)
        self.debug_var.set(self.config.debug_mode)
        self.auto_increment_var.set(self.config.auto_increment_filename)

    def _browse_directory(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)

    def _save_settings(self):
        """Save settings and close window."""
        try:
            # Update config
            self.config.video_codec = self.codec_var.get()
            self.config.video_quality = int(self.quality_var.get())
            self.config.output_format = self.format_var.get()
            self.config.audio_sample_rate = int(self.sample_rate_var.get())
            self.config.audio_channels = int(self.channels_var.get().split()[0])
            self.config.audio_bitrate = self.bitrate_var.get()
            self.config.audio_delay_ms = int(self.audio_delay_var.get())
            self.config.output_directory = self.output_dir_var.get()
            self.config.debug_mode = self.debug_var.get()
            self.config.auto_increment_filename = self.auto_increment_var.get()

            # Validate and save
            issues = self.config_manager.validate_config()
            if issues:
                messagebox.showerror("Invalid Settings", "\n".join(issues))
                return

            if self.config_manager.save_config():
                messagebox.showinfo("Settings", "Settings saved successfully!")
                self.window.destroy()
            else:
                messagebox.showerror("Error", "Failed to save settings.")

        except ValueError as e:
            messagebox.showerror(
                "Invalid Input", f"Please check your input values: {e}"
            )

    def _cancel(self):
        """Cancel settings changes."""
        self.window.destroy()

    def _reset_defaults(self):
        """Reset settings to defaults."""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            self.config_manager.reset_to_defaults()
            self._load_current_settings()


class RecorderApp:
    """Main application window with enhanced UI and functionality."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Advanced Screen + Audio Recorder")
        self.root.configure(bg="#1e1e1e")

        # Initialize components
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()

        # Set up logging
        self.logger = setup_logging(
            self.config.log_level,
            self.config.debug_mode,
            "recorder.log" if self.config.debug_mode else None,
        )

        # Check dependencies
        self._check_dependencies()

        # Initialize recording components
        self.recorder: ScreenRecorder | None = None
        self.audio_capture: SystemAudioCapture | None = None
        self.audio_proc: subprocess.Popen | None = None
        self.video_file: str | None = None
        self.audio_file = "temp_audio.wav"
        self.final_file: str | None = None
        self.recording_timer = RecordingTimer()

        # UI components
        self.progress_window: ProgressWindow | None = None
        self.app_checkboxes: dict[str, tk.BooleanVar] = {}
        self.log_text = tk.StringVar(value="Ready")

        # Available screens
        try:
            temp_recorder = ScreenRecorder(1)
            self.screens = temp_recorder.detect_screens()
        except VideoCaptureError as e:
            self.logger.error(f"Failed to detect screens: {e}")
            self.screens = []

        self.selected_screen_index = tk.IntVar(value=self.config.default_monitor)

        self._build_ui()
        self._setup_keyboard_shortcuts()

        # Update window settings
        if self.config.remember_window_position:
            self.root.geometry(
                f"{self.config.window_width}x{self.config.window_height}+{self.config.window_x}+{self.config.window_y}"
            )
        else:
            self.root.geometry(
                f"{self.config.window_width}x{self.config.window_height}"
            )

    def _check_dependencies(self):
        """Check system dependencies."""
        deps = check_dependencies()
        missing = [dep for dep, available in deps.items() if not available]

        if missing:
            self.logger.warning(f"Missing dependencies: {', '.join(missing)}")
            messagebox.showwarning(
                "Missing Dependencies",
                f"Some features may not work properly.\nMissing: {', '.join(missing)}\n\n"
                "Please install the missing dependencies.",
            )

    def _build_ui(self):
        """Build the main UI."""
        # Configure grid weights for resizing
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Main frame
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Styles
        label_style = {"bg": "#1e1e1e", "fg": "#ffffff"}
        entry_style = {"bg": "#2e2e2e", "fg": "#ffffff", "insertbackground": "white"}
        btn_style = {"bg": "#3a3a3a", "fg": "white", "activebackground": "#5a5a5a"}

        row = 0

        # FPS setting
        tk.Label(main_frame, text="FPS:", **label_style).grid(
            row=row, column=0, sticky="w", pady=5
        )
        self.fps_entry = tk.Entry(main_frame, width=10, **entry_style)
        self.fps_entry.insert(0, str(self.config.fps))
        self.fps_entry.grid(row=row, column=1, sticky="w", pady=5)
        row += 1

        # Screen selector
        if self.screens:
            tk.Label(main_frame, text="Screen:", **label_style).grid(
                row=row, column=0, sticky="w", pady=5
            )
            screen_options = [
                f"{s['name']}: {s['width']}x{s['height']}" for s in self.screens
            ]
            self.screen_combo = ttk.Combobox(
                main_frame, values=screen_options, state="readonly", width=30
            )
            if self.config.default_monitor <= len(self.screens):
                self.screen_combo.current(self.config.default_monitor - 1)
            else:
                self.screen_combo.current(0)
            self.screen_combo.bind("<<ComboboxSelected>>", self._on_screen_selected)
            self.screen_combo.grid(row=row, column=1, columnspan=2, sticky="w", pady=5)
            row += 1

        # Audio apps section with hide/show button
        audio_header_frame = tk.Frame(main_frame, bg="#1e1e1e")
        audio_header_frame.grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(15, 5)
        )

        tk.Label(audio_header_frame, text="Audio Sources:", **label_style).pack(
            side=tk.LEFT
        )

        # Hide/Show sources button
        self.sources_visible = tk.BooleanVar(value=False)
        self.toggle_sources_btn = tk.Button(
            audio_header_frame,
            text="Show Sources",
            command=self._toggle_sources_visibility,
            **btn_style,
            font=("Arial", 8),
        )
        self.toggle_sources_btn.pack(side=tk.LEFT, padx=(10, 0))
        row += 1

        # Audio apps checkboxes
        self.apps_frame = tk.Frame(main_frame, bg="#1e1e1e")
        self.apps_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=5)

        available_apps = self.config_manager.get_available_apps()
        for idx, app in enumerate(available_apps):
            var = tk.BooleanVar(value=app in self.config.selected_apps)
            chk = tk.Checkbutton(
                self.apps_frame,
                text=app,
                variable=var,
                bg="#1e1e1e",
                fg="#cccccc",
                selectcolor="#2e2e2e",
                activebackground="#333333",
            )
            chk.grid(row=idx // 3, column=idx % 3, sticky="w", padx=5)
            self.app_checkboxes[app] = var

        # Hide sources by default
        self.apps_frame.grid_remove()
        row += 1

        # Status and progress
        self.status_label = tk.Label(
            main_frame, textvariable=self.log_text, **label_style
        )
        self.status_label.grid(row=row, column=0, columnspan=3, sticky="w", pady=15)
        row += 1

        # Control buttons
        buttons_frame = tk.Frame(main_frame, bg="#1e1e1e")
        buttons_frame.grid(row=row, column=0, columnspan=3, pady=10)

        self.start_btn = tk.Button(
            buttons_frame,
            text="🎬 Start Recording",
            command=self.start_recording,
            **btn_style,
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(
            buttons_frame,
            text="⏹️ Stop Recording",
            command=self.stop_recording,
            **btn_style,
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.settings_btn = tk.Button(
            buttons_frame, text="⚙️ Settings", command=self.open_settings, **btn_style
        )
        self.settings_btn.pack(side=tk.LEFT, padx=5)

        row += 1

        # Progress bar (initially hidden)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, variable=self.progress_var, mode="indeterminate"
        )

        # Keyboard shortcuts help
        help_text = "Shortcuts: F1=Start/Stop, F2=Pause, F3=Settings, Esc=Stop"
        tk.Label(main_frame, text=help_text, **label_style, font=("Arial", 8)).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(20, 0)
        )

    def _setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts."""
        self.root.bind("<F1>", lambda e: self.toggle_recording())
        self.root.bind("<F2>", lambda e: self.pause_recording())
        self.root.bind("<F3>", lambda e: self.open_settings())
        self.root.bind("<Escape>", lambda e: self.stop_recording())

        # Make sure window can receive focus
        self.root.focus_set()

    def _on_screen_selected(self, event=None):
        """Handle screen selection."""
        if hasattr(self, "screen_combo"):
            self.selected_screen_index.set(self.screen_combo.current() + 1)

    def _toggle_sources_visibility(self):
        """Toggle the visibility of audio sources checkboxes."""
        if self.sources_visible.get():
            # Hide sources
            self.apps_frame.grid_remove()
            self.sources_visible.set(False)
            self.toggle_sources_btn.config(text="Show Sources")
        else:
            # Show sources
            self.apps_frame.grid()
            self.sources_visible.set(True)
            self.toggle_sources_btn.config(text="Hide Sources")

    def _log(self, msg: str):
        """Update log display."""
        self.logger.info(msg)
        self.log_text.set(msg)

        # Update progress window if open
        if self.progress_window:
            self.progress_window.update_info(msg)

    def toggle_recording(self):
        """Toggle recording state."""
        if not self.recorder or not self.recorder.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def pause_recording(self):
        """Pause/resume recording."""
        if self.recorder and self.recorder.recording:
            self.recorder.pause_recording()
            if self.progress_window:
                self.progress_window.set_paused(self.recorder.paused)

    def start_recording(self):
        """Start recording with enhanced error handling."""
        try:
            # Validate FPS
            valid, fps = validate_fps(self.fps_entry.get())
            if not valid:
                messagebox.showerror(
                    "Invalid FPS", "Please enter a valid FPS value (1-120)."
                )
                return

            # Get selected apps
            selected_apps = [
                app for app, var in self.app_checkboxes.items() if var.get()
            ]
            if not selected_apps:
                if not messagebox.askyesno(
                    "No Audio Sources",
                    "No audio sources selected. Continue with video only?",
                ):
                    return

            # Initialize recorder
            self.recorder = ScreenRecorder(
                fps,
                monitor_index=self.selected_screen_index.get(),
                codec=self.config.video_codec,
                quality=self.config.video_quality,
                log_callback=self._log,
            )

            # Initialize audio capture if apps selected
            if selected_apps:
                self.audio_capture = SystemAudioCapture(
                    selected_apps,
                    sample_rate=self.config.audio_sample_rate,
                    channels=self.config.audio_channels,
                    log_callback=self._log,
                )

                if not self.audio_capture.setup():
                    messagebox.showerror(
                        "Audio Setup Failed",
                        "Failed to set up audio capture. Continue with video only?",
                    )
                    if not messagebox.askyesno(
                        "Continue?", "Record video without audio?"
                    ):
                        return
                    self.audio_capture = None

            # Generate output filename
            if self.config.auto_increment_filename:
                base_name = Path(self.config.output_directory) / "recording"
                temp_video = f"{base_name}_temp.avi"
            else:
                temp_video = filedialog.asksaveasfilename(
                    defaultextension=f".{self.config.output_format}",
                    filetypes=[
                        (
                            f"{self.config.output_format.upper()} files",
                            f"*.{self.config.output_format}",
                        )
                    ],
                )
                if not temp_video:
                    return
                temp_video = temp_video.replace(
                    f".{self.config.output_format}", "_temp.avi"
                )

            # Start audio recording first (it takes longer to initialize)
            if self.audio_capture:
                self.audio_proc = self.audio_capture.start_recording(self.audio_file)
                # Small delay to let audio recording stabilize
                import time

                time.sleep(0.1)

            # Start video recording
            self.video_file = self.recorder.start_recording(temp_video)

            # Update UI
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.progress_bar.grid(row=100, column=0, columnspan=3, sticky="ew", pady=5)
            self.progress_bar.start()

            # Start timer and show progress window
            self.recording_timer.start()
            self.progress_window = ProgressWindow(self.root, self.recording_timer)
            self.progress_window.pause_btn.config(command=self.pause_recording)
            self.progress_window.stop_btn.config(command=self.stop_recording)

            self._log("Recording started...")

        except (VideoCaptureError, AudioCaptureError) as e:
            messagebox.showerror("Recording Error", str(e))
            self._cleanup_recording()
        except Exception as e:
            self.logger.error(f"Unexpected error starting recording: {e}")
            messagebox.showerror("Error", f"Failed to start recording: {e}")
            self._cleanup_recording()

    def stop_recording(self):
        """Stop recording with proper cleanup."""
        if not self.recorder or not self.recorder.recording:
            return

        self._log("Stopping recording...")

        # Update UI immediately to show responsiveness
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED, text="Stopping...")
        self.root.update_idletasks()

        def _stop_recording_thread():
            """Handle the actual stopping in a separate thread to keep UI responsive."""
            try:
                # Stop recording
                self.recording_timer.stop()
                video_output = self.recorder.stop_recording()

                # Stop audio
                if self.audio_proc:
                    self.audio_proc.terminate()
                    self.audio_proc.wait()
                    self.audio_proc = None

                if self.audio_capture:
                    self.audio_capture.cleanup()
                    self.audio_capture = None

                # Process output
                if video_output:
                    final_output = self._process_output(video_output)
                    if final_output:
                        self.root.after(
                            0, lambda: self._log(f"Recording saved: {final_output}")
                        )

            except Exception as e:
                error_msg = f"Error stopping recording: {e}"
                self.logger.error(error_msg)
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Error", error_msg),
                )
            finally:
                # Schedule UI cleanup on main thread
                self.root.after(0, self._cleanup_recording)

        # Start the stopping process in a separate thread
        import threading

        stop_thread = threading.Thread(target=_stop_recording_thread, daemon=True)
        stop_thread.start()

    def _process_output(self, video_file: str) -> str | None:
        """Process the recorded output (merge audio/video, cleanup)."""
        try:
            if self.config.auto_increment_filename:
                final_output = get_incremental_filename(
                    base_name=str(Path(self.config.output_directory) / "recording"),
                    extension=f".{self.config.output_format}",
                )
            else:
                final_output = video_file.replace(
                    "_temp.avi", f".{self.config.output_format}"
                )

            # Check file sizes before processing
            video_size = (
                Path(video_file).stat().st_size if Path(video_file).exists() else 0
            )
            audio_size = (
                Path(self.audio_file).stat().st_size
                if Path(self.audio_file).exists()
                else 0
            )

            self._log(f"Video file: {video_file} ({video_size} bytes)")
            self._log(f"Audio file: {self.audio_file} ({audio_size} bytes)")

            # Merge audio and video if both exist
            if Path(self.audio_file).exists() and Path(video_file).exists():
                if video_size < 1000:  # Less than 1KB indicates a problem
                    self._log("WARNING: Video file is very small, may be corrupted")

                self._log("Merging audio and video...")
                success = merge_audio_video(
                    video_file,
                    self.audio_file,
                    final_output,
                    video_codec="libx264"
                    if self.config.output_format == "mp4"
                    else "copy",
                    audio_codec="aac",
                    audio_delay_ms=self.config.audio_delay_ms,
                    log_callback=self._log,
                )

                if success:
                    # Check final file size
                    final_size = (
                        Path(final_output).stat().st_size
                        if Path(final_output).exists()
                        else 0
                    )
                    self._log(f"Final file: {final_output} ({final_size} bytes)")

                    # Clean up temporary files
                    cleanup_temp_files([video_file, self.audio_file], self._log)
                    return final_output
                else:
                    # Keep original video file if merge failed
                    self._log("Merge failed, keeping original video file")
                    import shutil

                    shutil.move(video_file, final_output)
                    return final_output
            else:
                # Only video, rename to final output
                missing_files = []
                if not Path(video_file).exists():
                    missing_files.append("video")
                if not Path(self.audio_file).exists():
                    missing_files.append("audio")

                if missing_files:
                    self._log(f"Missing files: {', '.join(missing_files)}")

                if Path(video_file).exists():
                    import shutil

                    shutil.move(video_file, final_output)
                    return final_output
                else:
                    self._log("ERROR: No video file to save")
                    return None

        except Exception as e:
            self.logger.error(f"Error processing output: {e}")
            return None

    def _cleanup_recording(self):
        """Clean up recording state."""
        # Update UI
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED, text="⏹️ Stop Recording")
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

        # Close progress window
        if self.progress_window:
            self.progress_window.close()
            self.progress_window = None

        # Reset timer
        self.recording_timer.reset()

    def open_settings(self):
        """Open settings window."""
        SettingsWindow(self.root, self.config_manager)

    def on_closing(self):
        """Handle application closing."""
        # Save window position if enabled
        if self.config.remember_window_position:
            geometry = self.root.geometry()
            # Parse geometry string (WxH+X+Y)
            size_pos = geometry.split("+")
            if len(size_pos) >= 3:
                self.config.window_x = int(size_pos[1])
                self.config.window_y = int(size_pos[2])
                self.config_manager.save_config()

        # Stop recording if in progress
        if self.recorder and self.recorder.recording:
            if messagebox.askyesno(
                "Recording in Progress", "Recording is in progress. Stop and exit?"
            ):
                self.stop_recording()
            else:
                return

        # Clean up
        if self.audio_capture:
            self.audio_capture.cleanup()

        self.root.destroy()


def main():
    """Main application entry point."""
    root = tk.Tk()
    app = RecorderApp(root)

    # Set up window close handler
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    # Start the application
    root.mainloop()


if __name__ == "__main__":
    main()
