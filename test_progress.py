#!/usr/bin/env python3
"""
Test script to verify the progress bar functionality works correctly.
"""

import threading
import time
import tkinter as tk

from ui import ProcessingProgressWindow


def test_progress_bar():
    """Test the processing progress bar window."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Create progress window
    progress_window = ProcessingProgressWindow(root)

    def simulate_progress():
        """Simulate FFmpeg progress updates."""
        for i in range(101):
            progress_window.update_progress(
                i,
                f"Processing: {i / 10:.1f}s / 10.0s"
                if i < 100
                else "Processing complete!",
            )
            time.sleep(0.05)  # Simulate processing time

        # Close after a brief pause
        time.sleep(1)
        progress_window.close()
        root.quit()

    # Start simulation in background thread
    threading.Thread(target=simulate_progress, daemon=True).start()

    # Run the GUI
    root.mainloop()


if __name__ == "__main__":
    print("Testing progress bar functionality...")
    test_progress_bar()
    print("✓ Progress bar test completed successfully!")
