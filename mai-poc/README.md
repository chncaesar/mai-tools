# MAI-UI POC

A simple proof-of-concept for GUI automation using MAI-UI model.

## Architecture

```
┌─────────────────┐     WebSocket     ┌─────────────────┐
│   Frontend      │◄──────────────────│   Backend       │
│   (Browser)     │                   │   (FastAPI)     │
└─────────────────┘                   └────────┬────────┘
                                               │
                                    ┌──────────┴──────────┐
                                    │                     │
                              ┌─────▼─────┐        ┌──────▼──────┐
                              │  MAI-UI   │        │   Android   │
                              │  Model    │        │   Device    │
                              │  (vllm)   │        │   (ADB)     │
                              └───────────┘        └─────────────┘
```

## Prerequisites

1. **MAI-UI Model Server** running on port 8000
   ```bash
   # Using vllm-mlx (macOS Apple Silicon)
   vllm-mlx serve ~/models/mai-ui-2b-mlx --port 8000
   ```

2. **Android Device** connected via ADB (see [ADB Setup](#adb-setup-for-macos) below)

3. **Python 3.11+**

## ADB Setup for macOS

### Install ADB

**Option 1: Using Homebrew (Recommended)**
```bash
brew install android-platform-tools
```

**Option 2: Using Android Studio**
- Download and install [Android Studio](https://developer.android.com/studio)
- ADB is included in Android Studio SDK Platform Tools
- Add to PATH: `export PATH="$PATH:$HOME/Library/Android/sdk/platform-tools"`

**Option 3: Manual Installation**
```bash
# Download platform-tools from Google
# https://developer.android.com/tools/releases/platform-tools
# Extract and add to PATH
export PATH="$PATH:/path/to/platform-tools"
```

### Connect Android Device

1. **Enable Developer Options on Android Device:**
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times until you see "You are now a developer"

2. **Enable USB Debugging:**
   - Go to Settings → Developer Options
   - Enable "USB Debugging"
   - (Optional) Enable "Stay awake" to keep screen on while charging

3. **Connect via USB:**
   - Connect your Android device to Mac using USB cable
   - On your Android device, you may see a prompt: "Allow USB debugging?" → Check "Always allow from this computer" → Tap "Allow"

4. **Verify Connection:**
   ```bash
   adb devices
   ```
   You should see output like:
   ```
   List of devices attached
   ABC123XYZ    device
   ```

### Troubleshooting

**Device not showing up:**
- Try a different USB cable (some cables are charge-only)
- Try different USB ports on your Mac
- Restart ADB server: `adb kill-server && adb start-server`
- Check if device appears: `adb devices -l`

**"unauthorized" status:**
- Unplug and replug USB cable
- On Android device, check for USB debugging authorization prompt
- Revoke USB debugging authorizations: Settings → Developer Options → Revoke USB debugging authorizations

**macOS not recognizing device:**
- Install Android File Transfer (if needed): https://www.android.com/filetransfer/
- Some devices require additional drivers (check manufacturer website)

**Connection via WiFi (Advanced):**
```bash
# Connect device via USB first, then:
adb tcpip 5555
adb connect <device-ip-address>:5555
# Now you can disconnect USB
```

## Setup

```bash
cd mai-poc/backend

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
# Terminal 1: Start MAI-UI model server (if not already running)
vllm-mlx serve ~/models/mai-ui-2b-mlx --port 8000

# Terminal 2: Start backend
cd mai-poc/backend
python main.py
```

Open browser: http://localhost:8080

## Usage

1. Connect Android device via USB and enable USB debugging
2. Enter instruction in the input box, e.g.:
   - "Open Settings app"
   - "Click the WiFi option"
   - "Scroll down to find About Phone"
3. Click "Execute" and watch the automation

## Files

```
mai-poc/
├── backend/
│   ├── main.py      # FastAPI server + WebSocket
│   ├── agent.py     # MAI-UI agent wrapper
│   ├── device.py    # ADB controller
│   └── requirements.txt
├── frontend/
│   └── index.html   # Simple web UI
└── README.md
```

## API

- `GET /` - Frontend UI
- `WS /ws` - WebSocket for real-time communication
- `GET /api/status` - Current task status
- `GET /api/results` - All results

## WebSocket Messages

**Client → Server:**
```json
{"type": "execute", "instruction": "Open Settings", "max_steps": 10}
```

**Server → Client:**
```json
{"type": "screenshot", "step": 0, "image": "base64..."}
{"type": "step", "data": {"step": 0, "action": {"action": "click", "coordinates": [0.5, 0.3]}}}
{"type": "task_complete", "message": "Task completed"}
```
