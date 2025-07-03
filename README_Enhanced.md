# Enhanced Screen Recorder

A feature-rich screen recording application with system audio capture, built with Python and Tkinter.

## 🚀 New Features & Improvements

### ✅ Modular Architecture
- **Separated concerns**: `audio.py`, `video.py`, `ui.py`, `config.py`, `utils.py`
- **Better maintainability**: Each module handles specific functionality
- **Fallback support**: Original functionality preserved if enhanced modules fail

### ✅ Comprehensive Error Handling
- **Robust audio setup**: Proper PulseAudio error handling with timeouts
- **Video validation**: Monitor index validation and codec verification
- **Graceful failures**: Informative error messages and recovery options
- **Dependency checking**: Automatic detection of missing system dependencies

### ✅ Configuration Management
- **Persistent settings**: JSON-based configuration with `recorder_config.json`
- **Validation**: Input validation for all settings
- **Defaults**: Sensible default values for all options
- **Flexible paths**: Configurable output directories

### ✅ Enhanced UI & UX
- **Progress monitoring**: Separate progress window with real-time stats
- **Settings dialog**: Comprehensive settings with tabbed interface
- **Keyboard shortcuts**: F1=Start/Stop, F2=Pause, F3=Settings, Esc=Stop
- **Better feedback**: Status updates and completion notifications
- **File browser**: Output directory selection and file location opening

### ✅ Advanced Recording Features
- **Codec selection**: Multiple video codecs (XVID, H264, VP9, etc.)
- **Quality controls**: Configurable video quality and audio bitrate
- **Pause/Resume**: Ability to pause recording mid-session
- **Multi-format**: Support for MP4, AVI, MKV, WebM output formats
- **Performance monitoring**: Frame drop detection and recording statistics

### ✅ Logging & Debugging
- **Comprehensive logging**: Configurable log levels and file output
- **Debug mode**: Detailed debugging information for troubleshooting
- **Callback logging**: UI updates synchronized with log messages
- **Error tracking**: Detailed error messages with context

### ✅ Resource Management
- **Proper cleanup**: Automatic cleanup of temporary files
- **Memory efficiency**: Improved frame handling and buffering
- **Process management**: Safe subprocess handling with timeouts
- **PulseAudio restoration**: Automatic audio sink restoration on exit

## 📋 Requirements

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt install pulseaudio-utils ffmpeg

# Fedora/RHEL
sudo dnf install pulseaudio-utils ffmpeg

# Arch Linux
sudo pacman -S pulseaudio ffmpeg
```

### Python Dependencies
```bash
pip install -r requirements.txt
```

## 🎮 Usage

### Basic Usage
```bash
python app.py
```

### Enhanced Mode
The application automatically loads enhanced features if all modules are available.

### Keyboard Shortcuts
- **F1**: Start/Stop recording
- **F2**: Pause/Resume recording
- **F3**: Open settings
- **Esc**: Stop recording

## ⚙️ Configuration

Settings are automatically saved to `recorder_config.json` and include:

### Video Settings
- **FPS**: Frame rate (1-120)
- **Codec**: Video codec (XVID, H264, VP9, etc.)
- **Quality**: Video quality (1-100)
- **Format**: Output format (mp4, avi, mkv, webm)

### Audio Settings
- **Sample Rate**: 22050, 44100, 48000, or 96000 Hz
- **Channels**: Mono or Stereo
- **Bitrate**: 64k to 320k
- **App Selection**: Choose which applications to capture

### General Settings
- **Output Directory**: Where to save recordings
- **Debug Mode**: Enable detailed logging
- **Auto-increment**: Automatic filename generation
- **Window Position**: Remember window location

## 🏗️ Architecture

### Core Modules
- **`config.py`**: Configuration management and validation
- **`audio.py`**: PulseAudio system audio capture
- **`video.py`**: Screen recording with MSS and OpenCV
- **`ui.py`**: Enhanced Tkinter GUI with progress monitoring
- **`utils.py`**: Logging, utilities, and helper functions
- **`app.py`**: Main entry point with fallback support

### Error Handling Flow
1. **Dependency Check**: Verify system dependencies on startup
2. **Configuration Validation**: Validate all settings on load
3. **Graceful Degradation**: Fall back to basic mode if enhanced features fail
4. **Recovery Options**: Offer alternatives when operations fail

### Audio Capture Process
1. **Setup**: Create null sink and loopback module
2. **App Detection**: Find running applications to capture
3. **Routing**: Move selected apps to recording sink
4. **Recording**: Capture audio via FFmpeg
5. **Cleanup**: Restore original audio configuration

### Video Recording Process
1. **Monitor Selection**: Validate and select screen
2. **Codec Setup**: Initialize video writer with selected codec
3. **Frame Capture**: Efficient screen capture with MSS
4. **Performance Monitoring**: Track frame rates and drops
5. **Output Processing**: Merge audio/video and cleanup

## 🔧 Troubleshooting

### Common Issues

**"pactl command not found"**
- Install PulseAudio: `sudo apt install pulseaudio-utils`

**"FFmpeg not found"**
- Install FFmpeg: `sudo apt install ffmpeg`

**"No real audio sink found"**
- Ensure PulseAudio is running: `pulseaudio --start`

**"Failed to create video writer"**
- Try different codec in settings
- Check output directory permissions

### Debug Mode
Enable debug mode in settings for detailed logging:
- Creates `recorder.log` file
- Shows detailed error messages
- Displays performance statistics
- Logs PulseAudio operations

## 🎯 Performance Tips

### For Best Recording Quality
- Use H264 codec for smaller file sizes
- Set FPS to match your monitor's refresh rate
- Use 48000 Hz audio sample rate
- Record to SSD for better performance

### For System Performance
- Lower FPS for less CPU usage
- Use XVID codec for faster encoding
- Close unnecessary applications
- Monitor frame drop rates in progress window

## 📁 File Structure

```
minimal-screen-recorder/
├── app.py              # Main entry point
├── audio.py            # Audio capture module
├── video.py            # Video recording module
├── ui.py               # Enhanced UI module
├── config.py           # Configuration management
├── utils.py            # Utilities and logging
├── requirements.txt    # Python dependencies
├── README_Enhanced.md  # This documentation
└── recorder_config.json # Auto-generated settings
```

## 🔄 Migration from Original

The enhanced version is fully backward compatible:
- Original functionality preserved as fallback
- Existing workflows continue to work
- Settings automatically migrate to new format
- No breaking changes to core recording features

## 🤝 Contributing

The modular architecture makes it easy to contribute:
- Each module has clear responsibilities
- Comprehensive error handling patterns
- Extensive logging for debugging
- Configuration validation framework
- Unit test-friendly structure

## 📝 License

Same license as the original minimal screen recorder project.
