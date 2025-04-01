📦 ScreenRec Lite — Minimal Screen & Audio Recorder for Linux

![screenshot](snap/gui/screenshot.png) <!-- replace with your actual screenshot path or hosted image -->

ScreenRec Lite is a lightweight Python-powered screen and **system audio** recorder with a GUI, built for Linux desktops (Ubuntu, Debian, etc.).
It supports rerouting audio from apps like Firefox, Zoom, Discord, Spotify, OBS, Brave, and more — without capturing your mic.

✨ Features

- 🎥 Fullscreen screen recording
- 🔊 Record **system audio** (not just mic)
- 🖥️ GUI with per-app audio routing checkboxes
- 🧪 Built-in audio/video tests with `pytest`
- 🐧 Built for Ubuntu (also works on Debian-based distros)
- 📦 Packaged as a `.snap` and `.deb` (optional)

🧪 Installation (from Snap Store)

```bash
sudo snap install screenrec-lite
```

Or open the **Ubuntu Software Center** and search **“Screen Recorder”**.

🏁 Usage

After installing:

```bash
screenrec
```

Or launch it from your system menu — look for **“Screen Recorder”** with the camera icon.

🔄 Updating

When a new version is released, run:

```bash
sudo snap refresh screenrec-lite
```

🐙 Development

Clone this repo and build locally:

```bash
git clone https://github.com/m0tz/minimal-screen-recorder.git
cd minimal-screen-recorder
python3 -m venv env && source env/bin/activate
pip install -r requirements.txt
python app.py
```

🧪 Run tests

```bash
pytest
```

🧰 Packaging

🔹 Build Snap (local dev mode):

```bash
snapcraft --destructive-mode
```

🔹 Build `.deb` (coming soon)

📤 Publish to Snap Store

> Only required for maintainers

```bash
snapcraft upload screenrec-lite_1.0.0_amd64.snap --release=stable
```

📝 License

MIT © Carlos Agustín Enríquez (https://github.com/agustinenriquez)
