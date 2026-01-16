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

2. **Android Device** connected via ADB
   ```bash
   # Check connection
   adb devices
   ```

3. **Python 3.11+**

## Setup

```bash
cd mai-poc/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

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
