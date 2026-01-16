# ADB 连接 Android 手机详细指南

## 1. ADB 概述

### 1.1 什么是 ADB

ADB (Android Debug Bridge) 是 Android SDK 提供的命令行工具，用于与 Android 设备通信。它是一个 Client-Server 架构的程序：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   ADB       │     │   ADB       │     │   Android       │
│   Client    │────►│   Server    │────►│   Device        │
│  (命令行)   │     │  (后台进程)  │     │  (adbd daemon)  │
└─────────────┘     └─────────────┘     └─────────────────┘
     PC端               PC端                手机端
```

### 1.2 ADB 能做什么

对于 GUI 自动化应用，ADB 提供以下关键能力：

| 功能 | 命令 | 用途 |
|-----|------|------|
| 屏幕截图 | `screencap` | 获取当前屏幕画面供 MAI-UI 分析 |
| 模拟点击 | `input tap` | 点击 UI 元素 |
| 模拟滑动 | `input swipe` | 滚动列表、滑动页面 |
| 文本输入 | `input text` | 输入搜索关键词 |
| 按键事件 | `input keyevent` | 返回键、Home 键等 |
| 启动应用 | `am start` | 打开目标 App |
| 屏幕录制 | `screenrecord` | 录制操作过程 |

## 2. 环境准备

### 2.1 安装 ADB

**macOS (Homebrew)**
```bash
brew install android-platform-tools
```

**Ubuntu/Debian**
```bash
sudo apt update
sudo apt install android-tools-adb
```

**验证安装**
```bash
adb version
# 输出: Android Debug Bridge version 1.0.41
```

### 2.2 Android 手机设置

#### 步骤 1: 启用开发者选项

1. 打开 **设置** → **关于手机**
2. 连续点击 **版本号** 7 次
3. 返回设置，出现 **开发者选项**

#### 步骤 2: 启用 USB 调试

1. 进入 **设置** → **开发者选项**
2. 开启 **USB 调试**
3. (可选) 开启 **USB 调试 (安全设置)** - 某些手机需要此选项才能模拟输入

#### 步骤 3: 关闭权限监控 (重要)

某些手机厂商添加了额外的安全限制，需要关闭：

**小米/Redmi**
```
设置 → 开发者选项 → USB调试(安全设置) → 开启
设置 → 开发者选项 → 关闭 "MIUI优化"
```

**华为/荣耀**
```
设置 → 开发者选项 → 允许ADB调试修改权限或模拟点击
```

**OPPO/Realme**
```
设置 → 开发者选项 → 禁止权限监控
```

**vivo**
```
设置 → 开发者选项 → USB安全操作 → 开启
```

## 3. USB 连接方式

### 3.1 连接步骤

```bash
# 1. 用 USB 数据线连接手机和电脑

# 2. 检查设备是否识别
adb devices
# 输出:
# List of devices attached
# XXXXXXXX    device

# 3. 如果显示 "unauthorized"，请在手机上点击 "允许 USB 调试"
#    并勾选 "始终允许从此计算机调试"
```

### 3.2 常见问题排查

**问题: 设备显示 "offline"**
```bash
# 重启 ADB 服务
adb kill-server
adb start-server
adb devices
```

**问题: 设备未识别 (macOS)**
```bash
# 检查 USB 连接
system_profiler SPUSBDataType | grep -A 10 "Android"

# 如果是非标准设备，可能需要添加 vendor ID
echo "0x2717" >> ~/.android/adb_usb.ini  # 小米
echo "0x12d1" >> ~/.android/adb_usb.ini  # 华为
adb kill-server
```

**问题: Permission denied (Linux)**
```bash
# 添加 udev 规则
sudo vim /etc/udev/rules.d/51-android.rules

# 添加内容 (以小米为例):
SUBSYSTEM=="usb", ATTR{idVendor}=="2717", MODE="0666", GROUP="plugdev"

# 重载规则
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 3.3 USB 连接优缺点

| 优点 | 缺点 |
|-----|------|
| 连接稳定 | 需要数据线 |
| 传输速度快 | 手机位置受限 |
| 延迟低 (~10ms) | 长时间连接可能发热 |
| 无需额外配置网络 | 不支持远程操作 |

## 4. WiFi 无线连接方式

### 4.1 方式一: 先 USB 配对后 WiFi

```bash
# 1. 先用 USB 连接手机
adb devices

# 2. 设置手机监听 TCP 端口
adb tcpip 5555
# 输出: restarting in TCP mode port: 5555

# 3. 获取手机 IP 地址
adb shell ip addr show wlan0 | grep "inet "
# 或在手机上查看: 设置 → WLAN → 已连接的网络 → IP地址

# 4. 断开 USB，通过 WiFi 连接
adb connect 192.168.1.100:5555
# 输出: connected to 192.168.1.100:5555

# 5. 验证连接
adb devices
# 输出:
# List of devices attached
# 192.168.1.100:5555    device
```

### 4.2 方式二: 无线调试 (Android 11+)

Android 11 及以上版本支持无需 USB 线的配对：

```bash
# 1. 手机设置
#    设置 → 开发者选项 → 无线调试 → 开启
#    点击 "使用配对码配对设备"

# 2. 记录显示的:
#    - IP 地址和端口 (如 192.168.1.100:37521)
#    - 配对码 (如 482916)

# 3. 在电脑上配对
adb pair 192.168.1.100:37521
# 输入配对码: 482916
# 输出: Successfully paired to 192.168.1.100:37521

# 4. 连接设备 (注意：连接端口与配对端口不同)
#    查看 "无线调试" 页面显示的 "IP地址和端口"
adb connect 192.168.1.100:43567
# 输出: connected to 192.168.1.100:43567
```

### 4.3 WiFi 连接保持脚本

WiFi 连接可能断开，使用脚本自动重连：

```python
# scripts/adb_keepalive.py

import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ADBWiFiKeepAlive:
    def __init__(self, device_ip: str, port: int = 5555):
        self.device_ip = device_ip
        self.port = port
        self.device_addr = f"{device_ip}:{port}"

    def is_connected(self) -> bool:
        """检查设备是否连接"""
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )
        return self.device_addr in result.stdout and "device" in result.stdout

    def connect(self) -> bool:
        """连接设备"""
        result = subprocess.run(
            ["adb", "connect", self.device_addr],
            capture_output=True,
            text=True
        )
        return "connected" in result.stdout

    def run(self, check_interval: int = 30):
        """持续监控连接状态"""
        logger.info(f"开始监控 ADB WiFi 连接: {self.device_addr}")

        while True:
            if not self.is_connected():
                logger.warning(f"连接断开，尝试重连...")
                if self.connect():
                    logger.info("重连成功")
                else:
                    logger.error("重连失败")
            else:
                logger.debug("连接正常")

            time.sleep(check_interval)


if __name__ == "__main__":
    keepalive = ADBWiFiKeepAlive("192.168.1.100", 5555)
    keepalive.run()
```

### 4.4 WiFi 连接优缺点

| 优点 | 缺点 |
|-----|------|
| 无线自由，手机可放置任意位置 | 连接可能不稳定 |
| 支持远程操作 | 延迟较高 (~50-100ms) |
| 适合长时间运行 | 截图传输较慢 |
| 不影响手机充电 | 需要同一局域网 |

## 5. 核心 ADB 命令详解

### 5.1 屏幕截图

```bash
# 方式 1: 保存到手机再拉取 (较慢)
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png ./screen.png
adb shell rm /sdcard/screen.png

# 方式 2: 直接输出到 stdout (推荐，更快)
adb exec-out screencap -p > screen.png

# 方式 3: 获取原始数据 (最快，用于程序处理)
adb exec-out screencap -p | python -c "
import sys
from PIL import Image
from io import BytesIO
img = Image.open(BytesIO(sys.stdin.buffer.read()))
print(f'Screenshot: {img.size}')
"
```

**Python 实现**
```python
import subprocess
from PIL import Image
from io import BytesIO

def screenshot(device_id: str = None) -> Image.Image:
    """获取屏幕截图"""
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["exec-out", "screencap", "-p"])

    result = subprocess.run(cmd, capture_output=True)
    return Image.open(BytesIO(result.stdout))

# 使用
img = screenshot()
img.save("screen.png")
```

### 5.2 模拟点击

```bash
# 点击坐标 (x, y)
adb shell input tap 540 1200

# 长按 (默认约 500ms)
adb shell input swipe 540 1200 540 1200 1000  # 1000ms 长按
```

**Python 实现 (归一化坐标)**
```python
def tap(x: float, y: float, screen_width: int = 1080, screen_height: int = 2400):
    """
    点击屏幕
    x, y: 归一化坐标 (0-1)
    """
    abs_x = int(x * screen_width)
    abs_y = int(y * screen_height)
    subprocess.run(["adb", "shell", "input", "tap", str(abs_x), str(abs_y)])

# MAI-UI 返回归一化坐标，直接使用
tap(0.5, 0.42)  # 点击屏幕中间偏上位置
```

### 5.3 模拟滑动

```bash
# 从 (x1,y1) 滑动到 (x2,y2)，持续 300ms
adb shell input swipe 540 1800 540 600 300

# 快速滑动 (用于惯性滚动)
adb shell input swipe 540 1800 540 600 100

# 慢速滑动 (用于精确定位)
adb shell input swipe 540 1800 540 600 800
```

**Python 实现**
```python
def swipe(direction: str, duration: int = 300, distance: float = 0.6):
    """
    滑动屏幕
    direction: up, down, left, right
    distance: 滑动距离比例 (0-1)
    """
    screen_w, screen_h = 1080, 2400
    cx, cy = screen_w // 2, screen_h // 2

    # 计算滑动起止点
    swipe_distance_y = int(screen_h * distance / 2)
    swipe_distance_x = int(screen_w * distance / 2)

    directions = {
        "up": (cx, cy + swipe_distance_y, cx, cy - swipe_distance_y),
        "down": (cx, cy - swipe_distance_y, cx, cy + swipe_distance_y),
        "left": (cx + swipe_distance_x, cy, cx - swipe_distance_x, cy),
        "right": (cx - swipe_distance_x, cy, cx + swipe_distance_x, cy),
    }

    x1, y1, x2, y2 = directions[direction]
    subprocess.run([
        "adb", "shell", "input", "swipe",
        str(x1), str(y1), str(x2), str(y2), str(duration)
    ])

# 向上滑动查看更多内容
swipe("up")
```

### 5.4 文本输入

```bash
# 输入英文/数字 (简单)
adb shell input text "hello123"

# 输入带空格的文本 (空格需要转义)
adb shell input text "hello%sworld"  # %s 代表空格

# 输入中文 (需要特殊处理)
```

**中文输入方案**

ADB 原生不支持中文输入，有以下解决方案：

**方案 1: ADBKeyboard (推荐)**

```bash
# 1. 安装 ADBKeyboard APK
adb install ADBKeyboard.apk

# 2. 设置为默认输入法
adb shell ime set com.android.adbkeyboard/.AdbIME

# 3. 通过广播输入中文
adb shell am broadcast -a ADB_INPUT_TEXT --es msg "搜索关键词"

# 4. 恢复原输入法
adb shell ime set com.google.android.inputmethod.pinyin/.PinyinIME
```

**方案 2: 剪贴板粘贴**

```python
import subprocess
import base64

def input_chinese(text: str):
    """通过剪贴板输入中文"""
    # 1. 将文本写入剪贴板
    # 需要 Clipper 等辅助 App
    encoded = base64.b64encode(text.encode('utf-8')).decode('ascii')
    subprocess.run([
        "adb", "shell",
        "am", "broadcast",
        "-a", "clipper.set",
        "-e", "text", text
    ])

    # 2. 模拟粘贴操作 (Ctrl+V)
    subprocess.run(["adb", "shell", "input", "keyevent", "279"])  # PASTE
```

**方案 3: 直接使用 content provider (Android 10+)**

```python
def set_clipboard(text: str):
    """设置剪贴板内容"""
    # 写入临时文件
    subprocess.run([
        "adb", "shell",
        f"echo '{text}' | /system/bin/service call clipboard 2 i32 1 "
        f"i32 {len(text)} str16 '{text}'"
    ])
```

### 5.5 按键事件

```bash
# 常用按键
adb shell input keyevent 3    # HOME
adb shell input keyevent 4    # BACK
adb shell input keyevent 82   # MENU
adb shell input keyevent 26   # POWER
adb shell input keyevent 66   # ENTER
adb shell input keyevent 67   # DEL (退格)

# 音量键
adb shell input keyevent 24   # VOLUME_UP
adb shell input keyevent 25   # VOLUME_DOWN
```

**Python 封装**
```python
class KeyEvent:
    HOME = 3
    BACK = 4
    MENU = 82
    POWER = 26
    ENTER = 66
    DELETE = 67
    VOLUME_UP = 24
    VOLUME_DOWN = 25

def press_key(keycode: int):
    subprocess.run(["adb", "shell", "input", "keyevent", str(keycode)])

# 使用
press_key(KeyEvent.BACK)  # 返回
press_key(KeyEvent.HOME)  # 回到桌面
```

### 5.6 启动应用

```bash
# 启动应用 (示例: Settings)
adb shell am start -n com.android.settings/.Settings

# 强制停止应用
adb shell am force-stop com.android.settings

# 查看当前前台应用
adb shell dumpsys window | grep mCurrentFocus
```

**获取应用包名和 Activity**
```bash
# 方法 1: 通过当前界面获取
adb shell dumpsys window | grep mCurrentFocus
# 输出: mCurrentFocus=Window{xxx com.android.settings/...Settings}

# 方法 2: 列出所有已安装应用
adb shell pm list packages | grep -i settings
```

## 6. 完整的设备控制器实现

```python
# services/device_controller.py

import subprocess
import asyncio
import logging
from PIL import Image
from io import BytesIO
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class KeyCode(IntEnum):
    """Android 按键码"""
    HOME = 3
    BACK = 4
    CALL = 5
    END_CALL = 6
    VOLUME_UP = 24
    VOLUME_DOWN = 25
    POWER = 26
    CAMERA = 27
    CLEAR = 28
    ENTER = 66
    DELETE = 67
    MENU = 82
    SEARCH = 84
    MEDIA_PLAY_PAUSE = 85
    PAGE_UP = 92
    PAGE_DOWN = 93
    MOVE_HOME = 122
    MOVE_END = 123


@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    model: str
    android_version: str
    screen_width: int
    screen_height: int
    screen_density: int


class AndroidController:
    """
    Android 设备控制器

    支持 USB 和 WiFi 两种连接方式，提供完整的设备控制能力。
    """

    # 目标 App 信息 (示例: Settings)
    TARGET_PACKAGE = "com.android.settings"
    TARGET_ACTIVITY = "com.android.settings.Settings"

    def __init__(self, device_id: Optional[str] = None):
        """
        初始化控制器

        Args:
            device_id: 设备 ID，可以是:
                      - USB 设备序列号 (如 "XXXXXXXX")
                      - WiFi 地址 (如 "192.168.1.100:5555")
                      - None 表示自动选择第一个设备
        """
        self.device_id = device_id
        self.device_info: Optional[DeviceInfo] = None
        self._connected = False

    def _run_adb(self, *args, capture_output: bool = True) -> subprocess.CompletedProcess:
        """执行 ADB 命令"""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)

        logger.debug(f"ADB: {' '.join(cmd)}")
        return subprocess.run(cmd, capture_output=capture_output, text=True)

    def _run_adb_raw(self, *args) -> bytes:
        """执行 ADB 命令，返回原始字节"""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True)
        return result.stdout

    # ==================== 连接管理 ====================

    async def connect(self) -> bool:
        """
        连接设备并获取设备信息

        Returns:
            是否连接成功
        """
        # 检查设备是否在线
        result = self._run_adb("devices")
        if self.device_id:
            if self.device_id not in result.stdout:
                # 尝试 WiFi 连接
                if ":" in self.device_id:
                    connect_result = self._run_adb("connect", self.device_id)
                    if "connected" not in connect_result.stdout:
                        logger.error(f"无法连接到设备: {self.device_id}")
                        return False
        else:
            # 自动选择第一个设备
            lines = result.stdout.strip().split('\n')[1:]
            for line in lines:
                if '\tdevice' in line:
                    self.device_id = line.split('\t')[0]
                    break

            if not self.device_id:
                logger.error("未找到可用设备")
                return False

        # 获取设备信息
        await self._fetch_device_info()
        self._connected = True
        logger.info(f"已连接设备: {self.device_info}")
        return True

    async def disconnect(self) -> None:
        """断开 WiFi 连接"""
        if self.device_id and ":" in self.device_id:
            self._run_adb("disconnect", self.device_id)
        self._connected = False

    async def _fetch_device_info(self) -> None:
        """获取设备信息"""
        # 获取设备型号
        model = self._run_adb("shell", "getprop", "ro.product.model").stdout.strip()

        # 获取 Android 版本
        version = self._run_adb("shell", "getprop", "ro.build.version.release").stdout.strip()

        # 获取屏幕尺寸
        size_output = self._run_adb("shell", "wm", "size").stdout
        width, height = 1080, 2400  # 默认值
        if "Physical size:" in size_output:
            size_str = size_output.split(":")[1].strip()
            width, height = map(int, size_str.split("x"))

        # 获取屏幕密度
        density_output = self._run_adb("shell", "wm", "density").stdout
        density = 440  # 默认值
        if "Physical density:" in density_output:
            density = int(density_output.split(":")[1].strip())

        self.device_info = DeviceInfo(
            device_id=self.device_id,
            model=model,
            android_version=version,
            screen_width=width,
            screen_height=height,
            screen_density=density
        )

    @property
    def screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        if self.device_info:
            return self.device_info.screen_width, self.device_info.screen_height
        return 1080, 2400

    # ==================== 屏幕操作 ====================

    async def screenshot(self) -> Image.Image:
        """
        获取屏幕截图

        Returns:
            PIL Image 对象
        """
        raw = self._run_adb_raw("exec-out", "screencap", "-p")
        return Image.open(BytesIO(raw))

    async def screenshot_bytes(self) -> bytes:
        """获取屏幕截图的原始字节"""
        return self._run_adb_raw("exec-out", "screencap", "-p")

    # ==================== 触摸操作 ====================

    async def tap(self, x: float, y: float) -> None:
        """
        点击屏幕

        Args:
            x: 归一化 x 坐标 (0-1)
            y: 归一化 y 坐标 (0-1)
        """
        abs_x = int(x * self.screen_size[0])
        abs_y = int(y * self.screen_size[1])
        self._run_adb("shell", "input", "tap", str(abs_x), str(abs_y))
        logger.debug(f"Tap: ({x:.3f}, {y:.3f}) -> ({abs_x}, {abs_y})")

    async def long_press(self, x: float, y: float, duration: int = 1000) -> None:
        """
        长按屏幕

        Args:
            x: 归一化 x 坐标
            y: 归一化 y 坐标
            duration: 长按时间 (毫秒)
        """
        abs_x = int(x * self.screen_size[0])
        abs_y = int(y * self.screen_size[1])
        self._run_adb("shell", "input", "swipe",
                     str(abs_x), str(abs_y), str(abs_x), str(abs_y), str(duration))

    async def swipe(
        self,
        direction: str,
        distance: float = 0.5,
        duration: int = 300
    ) -> None:
        """
        滑动屏幕

        Args:
            direction: 方向 (up/down/left/right)
            distance: 滑动距离比例 (0-1)
            duration: 滑动持续时间 (毫秒)
        """
        w, h = self.screen_size
        cx, cy = w // 2, h // 2

        dist_x = int(w * distance / 2)
        dist_y = int(h * distance / 2)

        directions = {
            "up": (cx, cy + dist_y, cx, cy - dist_y),
            "down": (cx, cy - dist_y, cx, cy + dist_y),
            "left": (cx + dist_x, cy, cx - dist_x, cy),
            "right": (cx - dist_x, cy, cx + dist_x, cy),
        }

        if direction not in directions:
            raise ValueError(f"无效方向: {direction}")

        x1, y1, x2, y2 = directions[direction]
        self._run_adb("shell", "input", "swipe",
                     str(x1), str(y1), str(x2), str(y2), str(duration))
        logger.debug(f"Swipe {direction}: ({x1},{y1}) -> ({x2},{y2})")

    async def swipe_coords(
        self,
        x1: float, y1: float,
        x2: float, y2: float,
        duration: int = 300
    ) -> None:
        """
        从指定坐标滑动到另一坐标

        Args:
            x1, y1: 起始归一化坐标
            x2, y2: 结束归一化坐标
            duration: 持续时间 (毫秒)
        """
        w, h = self.screen_size
        ax1, ay1 = int(x1 * w), int(y1 * h)
        ax2, ay2 = int(x2 * w), int(y2 * h)
        self._run_adb("shell", "input", "swipe",
                     str(ax1), str(ay1), str(ax2), str(ay2), str(duration))

    # ==================== 文本输入 ====================

    async def input_text(self, text: str) -> None:
        """
        输入文本 (仅支持 ASCII)

        Args:
            text: 要输入的文本
        """
        # 转义特殊字符
        escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
        self._run_adb("shell", "input", "text", escaped)

    async def input_chinese(self, text: str) -> None:
        """
        输入中文 (需要 ADBKeyboard)

        Args:
            text: 要输入的中文文本
        """
        self._run_adb("shell", "am", "broadcast",
                     "-a", "ADB_INPUT_TEXT",
                     "--es", "msg", text)

    async def clear_text(self, char_count: int = 50) -> None:
        """
        清除输入框文本

        Args:
            char_count: 要删除的字符数
        """
        # 先全选
        self._run_adb("shell", "input", "keyevent", "KEYCODE_MOVE_END")
        # 删除
        for _ in range(char_count):
            self._run_adb("shell", "input", "keyevent", str(KeyCode.DELETE))

    # ==================== 按键操作 ====================

    async def press_key(self, keycode: int) -> None:
        """按下按键"""
        self._run_adb("shell", "input", "keyevent", str(keycode))

    async def press_back(self) -> None:
        """按返回键"""
        await self.press_key(KeyCode.BACK)

    async def press_home(self) -> None:
        """按 Home 键"""
        await self.press_key(KeyCode.HOME)

    async def press_enter(self) -> None:
        """按回车键"""
        await self.press_key(KeyCode.ENTER)

    async def press_menu(self) -> None:
        """按菜单键"""
        await self.press_key(KeyCode.MENU)

    # ==================== 应用管理 ====================

    async def start_app(self, package: str, activity: str) -> None:
        """
        启动应用

        Args:
            package: 包名
            activity: Activity 名
        """
        self._run_adb("shell", "am", "start", "-n", f"{package}/{activity}")
        logger.info(f"启动应用: {package}")

    async def stop_app(self, package: str) -> None:
        """强制停止应用"""
        self._run_adb("shell", "am", "force-stop", package)

    async def start_target_app(self) -> None:
        """启动目标应用"""
        await self.start_app(self.TARGET_PACKAGE, self.TARGET_ACTIVITY)

    async def stop_target_app(self) -> None:
        """停止目标应用"""
        await self.stop_app(self.TARGET_PACKAGE)

    async def get_current_app(self) -> str:
        """获取当前前台应用包名"""
        result = self._run_adb("shell", "dumpsys", "window", "|", "grep", "mCurrentFocus")
        # 解析输出
        if "mCurrentFocus" in result.stdout:
            # mCurrentFocus=Window{xxx com.example.app/...}
            import re
            match = re.search(r'(\w+\.\w+(?:\.\w+)*)/\S+', result.stdout)
            if match:
                return match.group(1)
        return ""

    async def is_target_app_running(self) -> bool:
        """检查目标应用是否在前台运行"""
        current = await self.get_current_app()
        return self.TARGET_PACKAGE in current

    # ==================== 实用方法 ====================

    async def wait(self, seconds: float) -> None:
        """等待指定秒数"""
        await asyncio.sleep(seconds)

    async def wait_for_app(self, package: str, timeout: int = 30) -> bool:
        """
        等待应用启动

        Args:
            package: 应用包名
            timeout: 超时时间 (秒)

        Returns:
            应用是否成功启动
        """
        for _ in range(timeout * 2):
            current = await self.get_current_app()
            if package in current:
                return True
            await asyncio.sleep(0.5)
        return False


# 使用示例
async def main():
    controller = AndroidController()

    # 连接设备
    if not await controller.connect():
        print("连接失败")
        return

    print(f"设备: {controller.device_info.model}")
    print(f"分辨率: {controller.screen_size}")

    # 启动目标应用
    await controller.start_target_app()
    await controller.wait(3)

    # 截图
    screenshot = await controller.screenshot()
    screenshot.save("app_home.png")
    print("截图已保存")

    # 点击搜索框 (假设在屏幕上半部分中间)
    await controller.tap(0.5, 0.1)
    await controller.wait(1)

    # 输入搜索词
    await controller.input_chinese("搜索关键词")
    await controller.wait(0.5)

    # 按回车搜索
    await controller.press_enter()
    await controller.wait(2)

    # 向上滑动查看更多
    await controller.swipe("up")


if __name__ == "__main__":
    asyncio.run(main())
```

## 7. 性能优化建议

### 7.1 截图优化

```python
# 使用较低分辨率截图 (节省传输时间)
async def screenshot_scaled(self, scale: float = 0.5) -> Image.Image:
    """获取缩放后的截图"""
    img = await self.screenshot()
    new_size = (int(img.width * scale), int(img.height * scale))
    return img.resize(new_size, Image.LANCZOS)
```

### 7.2 批量命令

```bash
# 使用单次 shell 执行多个命令
adb shell "input tap 540 1200; sleep 0.5; input tap 540 800"
```

### 7.3 连接池

```python
# 多设备管理
class DevicePool:
    def __init__(self):
        self.devices: Dict[str, AndroidController] = {}

    async def add_device(self, device_id: str) -> bool:
        controller = AndroidController(device_id)
        if await controller.connect():
            self.devices[device_id] = controller
            return True
        return False

    def get_device(self, device_id: str) -> Optional[AndroidController]:
        return self.devices.get(device_id)
```

## 8. 故障排除

### 8.1 常见错误

| 错误 | 原因 | 解决方案 |
|-----|------|---------|
| `error: device unauthorized` | 手机未授权 | 在手机上点击"允许调试" |
| `error: device offline` | 连接不稳定 | 重新插拔 USB 或 `adb reconnect` |
| `error: more than one device` | 多设备连接 | 使用 `-s` 指定设备 |
| `Failure [INSTALL_FAILED_...]` | 安装失败 | 检查存储空间、签名等 |
| `Input dispatch timed out` | 触摸事件超时 | 等待后重试 |

### 8.2 调试工具

```bash
# 查看实时日志
adb logcat -v time | grep -i "your_app"

# 查看设备属性
adb shell getprop

# 查看当前 Activity
adb shell dumpsys activity activities | grep mResumedActivity

# 检查 ADB 服务状态
adb get-state
```

---

*文档版本: 1.0*
*创建日期: 2026-01-16*
