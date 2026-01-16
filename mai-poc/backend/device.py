"""
ADB Device Controller for Android GUI Automation
"""

import subprocess
import asyncio
from PIL import Image
from io import BytesIO
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class DeviceInfo:
    device_id: str
    model: str
    screen_width: int
    screen_height: int


class ADBController:
    """Android device controller via ADB"""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.screen_size: Tuple[int, int] = (1080, 2400)
        self.device_info: Optional[DeviceInfo] = None

    def _adb(self, *args) -> subprocess.CompletedProcess:
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, text=True)

    def _adb_raw(self, *args) -> bytes:
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        result = subprocess.run(cmd, capture_output=True)
        return result.stdout

    async def connect(self) -> bool:
        """Connect to device"""
        result = self._adb("devices")
        lines = result.stdout.strip().split('\n')[1:]

        for line in lines:
            if '\tdevice' in line:
                if not self.device_id:
                    self.device_id = line.split('\t')[0]
                break

        if not self.device_id:
            return False

        # Get screen size
        size_out = self._adb("shell", "wm", "size").stdout
        if "Physical size:" in size_out:
            size_str = size_out.split(":")[1].strip()
            w, h = size_str.split("x")
            self.screen_size = (int(w), int(h))

        # Get model
        model = self._adb("shell", "getprop", "ro.product.model").stdout.strip()

        self.device_info = DeviceInfo(
            device_id=self.device_id,
            model=model,
            screen_width=self.screen_size[0],
            screen_height=self.screen_size[1]
        )
        return True

    async def screenshot(self) -> Image.Image:
        """Capture screenshot"""
        raw = self._adb_raw("exec-out", "screencap", "-p")
        return Image.open(BytesIO(raw))

    async def screenshot_base64(self) -> str:
        """Capture screenshot as base64"""
        import base64
        raw = self._adb_raw("exec-out", "screencap", "-p")
        return base64.b64encode(raw).decode('utf-8')

    async def tap(self, x: float, y: float) -> None:
        """Tap at normalized coordinates (0-1)"""
        abs_x = int(x * self.screen_size[0])
        abs_y = int(y * self.screen_size[1])
        self._adb("shell", "input", "tap", str(abs_x), str(abs_y))

    async def swipe(self, direction: str, duration: int = 300) -> None:
        """Swipe screen"""
        w, h = self.screen_size
        cx, cy = w // 2, h // 2
        dist = h // 3

        directions = {
            "up": (cx, cy + dist, cx, cy - dist),
            "down": (cx, cy - dist, cx, cy + dist),
            "left": (cx + dist, cy, cx - dist, cy),
            "right": (cx - dist, cy, cx + dist, cy),
        }

        if direction in directions:
            x1, y1, x2, y2 = directions[direction]
            self._adb("shell", "input", "swipe",
                     str(x1), str(y1), str(x2), str(y2), str(duration))

    async def input_text(self, text: str) -> None:
        """Input text (ASCII only)"""
        escaped = text.replace(" ", "%s")
        self._adb("shell", "input", "text", escaped)

    async def input_chinese(self, text: str) -> None:
        """Input Chinese via ADBKeyboard"""
        self._adb("shell", "am", "broadcast",
                 "-a", "ADB_INPUT_TEXT", "--es", "msg", text)

    async def press_back(self) -> None:
        self._adb("shell", "input", "keyevent", "4")

    async def press_home(self) -> None:
        self._adb("shell", "input", "keyevent", "3")

    async def press_enter(self) -> None:
        self._adb("shell", "input", "keyevent", "66")

    async def start_app(self, package: str, activity: str) -> None:
        self._adb("shell", "am", "start", "-n", f"{package}/{activity}")

    async def stop_app(self, package: str) -> None:
        self._adb("shell", "am", "force-stop", package)
