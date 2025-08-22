#!/bin/bash

# Install system dependencies for minimal-screen-recorder
# This script installs dependencies that are not available via pip

set -e

echo "Installing system dependencies for minimal-screen-recorder..."

# Detect package manager
if command -v apt &> /dev/null; then
    echo "Using apt package manager..."
    
    # Update package list
    echo "Updating package list..."
    sudo apt update
    
    # Install system dependencies
    echo "Installing FFmpeg..."
    sudo apt install -y ffmpeg
    
    echo "Installing PulseAudio utilities..."
    sudo apt install -y pulseaudio-utils
    
    echo "Installing tkinter (if not already present)..."
    sudo apt install -y python3-tk
    
elif command -v dnf &> /dev/null; then
    echo "Using dnf package manager..."
    
    echo "Installing FFmpeg..."
    sudo dnf install -y ffmpeg
    
    echo "Installing PulseAudio utilities..."
    sudo dnf install -y pulseaudio-utils
    
    echo "Installing tkinter..."
    sudo dnf install -y python3-tkinter
    
elif command -v pacman &> /dev/null; then
    echo "Using pacman package manager..."
    
    echo "Installing FFmpeg..."
    sudo pacman -S --noconfirm ffmpeg
    
    echo "Installing PulseAudio utilities..."
    sudo pacman -S --noconfirm pulseaudio
    
    echo "Installing tkinter..."
    sudo pacman -S --noconfirm tk
    
else
    echo "Unsupported package manager. Please install manually:"
    echo "- FFmpeg"
    echo "- PulseAudio utilities"
    echo "- Python3 tkinter"
    exit 1
fi

echo ""
echo "System dependencies installed successfully!"
echo "Now install Python dependencies with: pip install -r requirements.txt"