"""
MAI-UI POC Backend

Simple FastAPI server with WebSocket for real-time GUI automation.
No database - results stored in memory and sent to frontend.
"""

import asyncio
import uuid
import base64
from io import BytesIO
from typing import Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from device import ADBController
from agent import MAIAgent


# In-memory storage
results: List[Dict[str, Any]] = []
current_task: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan handler"""
    print("Starting MAI-UI POC Server...")
    yield
    print("Shutting down...")


app = FastAPI(title="MAI-UI POC", lifespan=lifespan)


class TaskRequest(BaseModel):
    instruction: str
    max_steps: int = 10


class ConnectionManager:
    """WebSocket connection manager"""

    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: Dict[str, Any]):
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


def image_to_base64(image) -> str:
    """Convert PIL image to base64"""
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


async def execute_task(instruction: str, max_steps: int = 10):
    """Execute automation task"""
    global current_task, results

    task_id = str(uuid.uuid4())[:8]
    current_task = {
        "task_id": task_id,
        "instruction": instruction,
        "status": "running",
        "steps": []
    }

    # Initialize device and agent
    device = ADBController()
    agent = MAIAgent(
        llm_base_url="http://127.0.0.1:8000/v1",
        model_name="default"
    )
    agent.reset(goal=instruction, task_id=task_id)

    # Notify start
    await manager.broadcast({
        "type": "task_start",
        "task_id": task_id,
        "instruction": instruction
    })

    # Connect to device
    if not await device.connect():
        await manager.broadcast({
            "type": "error",
            "message": "Failed to connect to Android device. Check ADB connection."
        })
        current_task["status"] = "error"
        return

    await manager.broadcast({
        "type": "device_connected",
        "device": {
            "id": device.device_info.device_id,
            "model": device.device_info.model,
            "screen": f"{device.screen_size[0]}x{device.screen_size[1]}"
        }
    })

    # Execute steps
    for step_num in range(max_steps):
        try:
            # Take screenshot
            screenshot = await device.screenshot()
            screenshot_b64 = image_to_base64(screenshot)

            # Send screenshot to frontend
            await manager.broadcast({
                "type": "screenshot",
                "step": step_num,
                "image": screenshot_b64
            })

            # Get action from agent
            response, action = agent.predict(instruction, screenshot)

            step_data = {
                "step": step_num,
                "action": action,
                "thought": action.get("thought", ""),
                "raw_response": response[:500] if len(response) > 500 else response
            }
            current_task["steps"].append(step_data)

            # Send step info to frontend
            await manager.broadcast({
                "type": "step",
                "data": step_data
            })

            # Check for termination
            if action.get("action") == "terminate":
                await manager.broadcast({
                    "type": "task_complete",
                    "message": "Task completed"
                })
                break

            if action.get("action") == "answer":
                await manager.broadcast({
                    "type": "answer",
                    "text": action.get("text", "")
                })
                break

            if action.get("action") == "error":
                await manager.broadcast({
                    "type": "error",
                    "message": action.get("message", "Unknown error")
                })
                break

            # Execute action on device
            await execute_action(device, action)

            # Wait for UI to respond
            await asyncio.sleep(1.5)

        except Exception as e:
            await manager.broadcast({
                "type": "error",
                "message": f"Step {step_num} error: {str(e)}"
            })
            break

    current_task["status"] = "completed"
    results.append(current_task.copy())

    await manager.broadcast({
        "type": "task_end",
        "task_id": task_id,
        "total_steps": len(current_task["steps"])
    })


async def execute_action(device: ADBController, action: Dict[str, Any]):
    """Execute action on device"""
    action_type = action.get("action", "")

    if action_type == "click":
        coords = action.get("coordinates", [0.5, 0.5])
        await device.tap(coords[0], coords[1])

    elif action_type == "long_press":
        coords = action.get("coordinates", [0.5, 0.5])
        # Simulate long press with swipe to same point
        x, y = coords
        abs_x = int(x * device.screen_size[0])
        abs_y = int(y * device.screen_size[1])
        device._adb("shell", "input", "swipe",
                   str(abs_x), str(abs_y), str(abs_x), str(abs_y), "1000")

    elif action_type == "type":
        text = action.get("text", "")
        # Try Chinese input first, fallback to ASCII
        if any(ord(c) > 127 for c in text):
            await device.input_chinese(text)
        else:
            await device.input_text(text)

    elif action_type == "swipe":
        direction = action.get("direction", "up")
        await device.swipe(direction)

    elif action_type == "back":
        await device.press_back()

    elif action_type == "home":
        await device.press_home()

    elif action_type == "wait":
        await asyncio.sleep(2)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()

            if data.get("type") == "execute":
                instruction = data.get("instruction", "")
                max_steps = data.get("max_steps", 10)

                if instruction:
                    # Run task in background
                    asyncio.create_task(execute_task(instruction, max_steps))
                else:
                    await ws.send_json({
                        "type": "error",
                        "message": "No instruction provided"
                    })

            elif data.get("type") == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/")
async def index():
    """Serve frontend"""
    return FileResponse("../frontend/index.html")


@app.get("/api/results")
async def get_results():
    """Get all results"""
    return {"results": results}


@app.get("/api/status")
async def get_status():
    """Get current status"""
    return {
        "current_task": current_task,
        "total_results": len(results)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
