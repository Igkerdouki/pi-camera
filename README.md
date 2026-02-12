# Pi Camera

Wildlife detection camera system for Raspberry Pi.

## Features

- **CLI tool** (`cam`) - Simple command-line interface for camera control
- **Web interface** (`camweb.py`) - Browser-based live view and recording management
- **Auto-recording** - Continuous recording with segmentation

## Installation

Copy files to your Raspberry Pi:

```bash
scp cam camweb.py record.sh rpi:~/
ssh rpi "chmod +x ~/cam ~/camweb.py ~/record.sh"
ssh rpi "sudo ln -sf ~/cam /usr/local/bin/cam"
```

## CLI Usage

```bash
cam snap              # Take a photo
cam snap -n 5         # Take 5 photos
cam record 30         # Record 30 seconds
cam record 2m         # Record 2 minutes
cam start             # Start continuous recording
cam stop              # Stop recording
cam status            # Check camera status
cam list              # List recordings
cam clean -f          # Delete all recordings
```

## Web Interface

Start the web server:

```bash
python3 ~/camweb.py
```

Then open http://<pi-ip>:8080 in your browser.

Features:
- Live camera stream
- Snap photos
- Record videos
- Browse/download/delete recordings

## Configuration

Environment variables for `cam`:

- `CAM_DIR` - Output directory (default: ~/recordings)
- `CAM_RES` - Resolution (default: 1920x1080)
- `CAM_FPS` - Framerate (default: 30)

## Hardware

- Raspberry Pi 4
- Pi Camera Module v2 (IMX219)

## License

MIT
