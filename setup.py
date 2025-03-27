from setuptools import setup

setup(
    name="minimal_screen_recorder",
    version="1.0",
    py_modules=["app"],
    install_requires=[
        "click",
        "keyboard",
        "opencv-python",
        "sounddevice",
        "soundfile",
        "mss",
        "numpy",
        "pydub",
        "ffmpeg-python",
        "pynput",
    ],
    entry_points={"gui_scripts": ["screenrec=app:main"]},
)
