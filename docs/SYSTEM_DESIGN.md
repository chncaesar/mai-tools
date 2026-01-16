# MAI-UI Android 自动化系统设计文档

## 1. 项目概述

### 1.1 背景

本项目基于阿里巴巴通义团队开发的 MAI-UI 视觉语言模型，实现 Android GUI 自动化操作。MAI-UI 能够理解 GUI 界面并执行自动化操作，非常适合需要模拟用户操作的场景。

### 1.2 技术选型

| 组件 | 技术 |
|-----|------|
| GUI Agent | MAI-UI-2B/8B (本地部署) |
| 推理引擎 | vllm-mlx (Apple Silicon) / vLLM (Linux) |
| 后端框架 | FastAPI |
| 数据库 | PostgreSQL + Redis |
| 设备控制 | ADB (Android Debug Bridge) |
| 前端 | React + TailwindCSS |
| 任务队列 | Celery |

## 2. 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              客户端层                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    React Web Dashboard                           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐│   │
│  │  │ 任务配置  │  │ 实时监控  │  │ 数据浏览  │  │ 数据导出/分析    ││   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTP/WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              后端服务层                                  │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      FastAPI Application                          │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │ │
│  │  │  Task API  │  │ Monitor API│  │  Data API  │  │ Config API │  │ │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  │ │
│  └────────┼───────────────┼───────────────┼───────────────┼─────────┘ │
│           │               │               │               │           │
│  ┌────────▼───────────────▼───────────────▼───────────────▼─────────┐ │
│  │                      Service Layer                                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐│ │
│  │  │ TaskService  │  │ AgentService │  │ DataExtractionService   ││ │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘│ │
│  └───────────────────────────┬───────────────────────────────────────┘ │
└──────────────────────────────┼──────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Celery      │    │   MAI-UI Agent  │    │    Database     │
│   Workers     │    │   (vllm-mlx)    │    │                 │
│               │    │                 │    │  ┌───────────┐  │
│ ┌───────────┐ │    │ ┌─────────────┐ │    │  │PostgreSQL │  │
│ │ Scrape    │ │    │ │ Navigation  │ │    │  └───────────┘  │
│ │ Worker    │◄├────┤►│ Agent       │ │    │  ┌───────────┐  │
│ └───────────┘ │    │ └─────────────┘ │    │  │  Redis    │  │
│ ┌───────────┐ │    │ ┌─────────────┐ │    │  └───────────┘  │
│ │ Extract   │ │    │ │ Grounding   │ │    └─────────────────┘
│ │ Worker    │ │    │ │ Agent       │ │
│ └───────────┘ │    │ └─────────────┘ │
└───────────────┘    └────────┬────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Android Device │
                    │                 │
                    │                 │
                    │  ┌───────────┐  │
                    │  │    ADB    │  │
                    │  └───────────┘  │
                    └─────────────────┘
```

## 3. 核心组件设计

### 3.1 后端服务

#### 3.1.1 API 设计

**任务管理 API**
```python
# POST /api/tasks - 创建抓取任务
# GET /api/tasks - 获取任务列表
# GET /api/tasks/{id} - 获取任务详情
# PUT /api/tasks/{id} - 更新任务
# DELETE /api/tasks/{id} - 删除任务
# POST /api/tasks/{id}/start - 启动任务
# POST /api/tasks/{id}/pause - 暂停任务
# POST /api/tasks/{id}/stop - 停止任务
```

**监控 API**
```python
# GET /api/monitor/{task_id}/screen - 获取当前屏幕截图
# WS /api/monitor/{task_id}/stream - WebSocket 实时流
# GET /api/monitor/{task_id}/trajectory - 获取执行轨迹
# GET /api/monitor/{task_id}/logs - 获取日志
```

**数据 API**
```python
# GET /api/data - 获取数据列表 (支持分页、筛选)
# GET /api/data/{id} - 获取数据详情
# GET /api/data/export - 导出数据
# GET /api/data/stats - 数据统计
```

#### 3.1.2 数据模型

```python
# models/data.py

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"))

    # 基本信息
    title = Column(String)                    # 标题
    description = Column(String)              # 描述
    price = Column(Float)                     # 价格

    # 位置信息
    location = Column(String)                 # 位置

    # 自定义属性 (JSON)
    attributes = Column(JSON)                 # 动态属性

    # 元数据
    source_url = Column(String)               # 来源
    screenshots = Column(JSON)                # 截图列表
    raw_data = Column(JSON)                   # 原始数据
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # 关系
    task = relationship("Task", back_populates="data_items")
    images = relationship("DataImage", back_populates="data_item")


class DataImage(Base):
    __tablename__ = "data_images"

    id = Column(Integer, primary_key=True)
    data_id = Column(String, ForeignKey("extracted_data.id"))
    image_url = Column(String)
    image_path = Column(String)               # 本地存储路径
    image_type = Column(String)               # 类型

    data_item = relationship("ExtractedData", back_populates="images")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    name = Column(String)
    config = Column(JSON)                     # 任务配置
    status = Column(String)
    progress = Column(JSON)                   # 进度信息
    created_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    data_items = relationship("ExtractedData", back_populates="task")
    trajectories = relationship("Trajectory", back_populates="task")
```

#### 3.1.3 Agent 服务

```python
# services/agent_service.py

import asyncio
from PIL import Image
from typing import Optional, Dict, Any
from dataclasses import dataclass

from mai_navigation_agent import MAIUINaivigationAgent
from device_controller import AndroidController


@dataclass
class AgentConfig:
    llm_base_url: str = "http://127.0.0.1:8000/v1"
    model_name: str = "mai-ui-2b"
    history_n: int = 5
    temperature: float = 0.0
    max_tokens: int = 2048


class AutomationAgentService:
    """Android 自动化 Agent 服务"""

    def __init__(self, config: AgentConfig, device_controller: AndroidController):
        self.config = config
        self.device = device_controller
        self.agent = self._init_agent()
        self.current_task = None
        self.is_running = False

    def _init_agent(self) -> MAIUINaivigationAgent:
        return MAIUINaivigationAgent(
            llm_base_url=self.config.llm_base_url,
            model_name=self.config.model_name,
            runtime_conf={
                "history_n": self.config.history_n,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
        )

    async def execute_task(self, task: Dict[str, Any]) -> None:
        """执行抓取任务"""
        self.current_task = task
        self.is_running = True
        self.agent.reset()

        try:
            # 1. 打开目标 App
            await self._open_app()

            # 2. 导航到目标页面
            await self._navigate_to_target()

            # 3. 设置筛选条件
            await self._apply_filters(task)

            # 4. 遍历并抓取数据
            await self._scrape_data(task)

        except Exception as e:
            await self._handle_error(e)
        finally:
            self.is_running = False

    async def _open_app(self) -> None:
        """打开目标 App"""
        instruction = "打开目标 App"
        await self._execute_step(instruction)

    async def _navigate_to_target(self) -> None:
        """导航到目标页面"""
        steps = [
            "点击搜索图标",
            "输入搜索关键词",
            "点击搜索按钮",
            "选择目标分类",
        ]
        for step in steps:
            await self._execute_step(step)

    async def _apply_filters(self, task: Dict[str, Any]) -> None:
        """应用筛选条件"""
        config = task.get("config", {})

        # 选择城市
        city = config.get("city", "杭州")
        await self._execute_step(f"点击定位图标，切换城市到{city}")

        # 设置价格范围
        if "priceRange" in config:
            price_min = config["priceRange"].get("min", 0)
            price_max = config["priceRange"].get("max", 0)
            await self._execute_step("点击价格筛选按钮")
            await self._execute_step(f"设置价格范围为{price_min}万到{price_max}万")
            await self._execute_step("点击确定按钮")

    async def _scrape_data(self, task: Dict[str, Any]) -> None:
        """抓取列表数据"""
        max_items = task.get("config", {}).get("maxItems", 100)
        scraped_count = 0

        while scraped_count < max_items and self.is_running:
            # 获取当前屏幕截图
            screenshot = await self.device.screenshot()

            # 检测列表中的卡片
            items = await self._detect_items(screenshot)

            for item in items:
                if scraped_count >= max_items:
                    break

                # 点击进入详情页
                await self._execute_step(f"点击第{item['index']+1}个卡片")

                # 抓取详情信息
                await self._scrape_detail()

                # 返回列表
                await self._execute_step("点击返回按钮")

                scraped_count += 1

            # 向下滚动加载更多
            await self._execute_step("向上滑动屏幕加载更多内容")

    async def _scrape_detail(self) -> Dict[str, Any]:
        """抓取详情页数据"""
        screenshot = await self.device.screenshot()

        # 使用 MAI-UI 分析页面内容
        instruction = """
        分析当前详情页面，提取关键信息并以JSON格式返回。
        """

        response, action = self.agent.predict(instruction, screenshot)

        # 解析响应
        data = self._parse_data(response)

        # 保存截图
        await self._save_screenshots()

        return data

    async def _execute_step(self, instruction: str) -> None:
        """执行单个步骤"""
        screenshot = await self.device.screenshot()

        response, action = self.agent.predict(instruction, screenshot)

        # 执行动作
        await self._perform_action(action)

        # 等待页面响应
        await asyncio.sleep(1)

    async def _perform_action(self, action: Dict[str, Any]) -> None:
        """在设备上执行动作"""
        action_type = action.get("action")

        if action_type == "click":
            coords = action.get("coordinates", [0.5, 0.5])
            await self.device.tap(coords[0], coords[1])

        elif action_type == "type":
            text = action.get("text", "")
            await self.device.input_text(text)

        elif action_type == "swipe":
            direction = action.get("direction", "up")
            await self.device.swipe(direction)

        elif action_type == "back":
            await self.device.press_back()
```

#### 3.1.4 设备控制器

```python
# services/device_controller.py

import subprocess
import asyncio
from PIL import Image
from io import BytesIO
from typing import Tuple, Optional


class AndroidController:
    """Android 设备控制器 (通过 ADB)"""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.screen_size: Tuple[int, int] = (1080, 2400)  # 默认分辨率

    def _adb_cmd(self, *args) -> str:
        """执行 ADB 命令"""
        cmd = ["adb"]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    async def connect(self) -> bool:
        """连接设备"""
        output = self._adb_cmd("devices")
        # 解析设备列表
        # 获取屏幕分辨率
        size_output = self._adb_cmd("shell", "wm", "size")
        # 解析: "Physical size: 1080x2400"
        if "Physical size:" in size_output:
            size_str = size_output.split(":")[1].strip()
            w, h = size_str.split("x")
            self.screen_size = (int(w), int(h))
        return True

    async def screenshot(self) -> Image.Image:
        """获取屏幕截图"""
        # 使用 screencap 获取截图
        result = subprocess.run(
            ["adb", "-s", self.device_id, "exec-out", "screencap", "-p"],
            capture_output=True
        )
        return Image.open(BytesIO(result.stdout))

    async def tap(self, x: float, y: float) -> None:
        """点击屏幕 (坐标为归一化值 0-1)"""
        abs_x = int(x * self.screen_size[0])
        abs_y = int(y * self.screen_size[1])
        self._adb_cmd("shell", "input", "tap", str(abs_x), str(abs_y))

    async def swipe(self, direction: str, distance: float = 0.5) -> None:
        """滑动屏幕"""
        cx, cy = self.screen_size[0] // 2, self.screen_size[1] // 2

        swipe_map = {
            "up": (cx, int(cy * 1.5), cx, int(cy * 0.5)),
            "down": (cx, int(cy * 0.5), cx, int(cy * 1.5)),
            "left": (int(cx * 1.5), cy, int(cx * 0.5), cy),
            "right": (int(cx * 0.5), cy, int(cx * 1.5), cy),
        }

        if direction in swipe_map:
            x1, y1, x2, y2 = swipe_map[direction]
            self._adb_cmd("shell", "input", "swipe",
                         str(x1), str(y1), str(x2), str(y2), "300")

    async def input_text(self, text: str) -> None:
        """输入文本"""
        # 对中文使用 ADBKeyBoard 或者 broadcast
        escaped_text = text.replace(" ", "%s").replace("'", "\\'")
        self._adb_cmd("shell", "am", "broadcast",
                     "-a", "ADB_INPUT_TEXT", "--es", "msg", text)

    async def press_back(self) -> None:
        """按返回键"""
        self._adb_cmd("shell", "input", "keyevent", "4")

    async def press_home(self) -> None:
        """按 Home 键"""
        self._adb_cmd("shell", "input", "keyevent", "3")

    async def start_app(self, package: str, activity: str) -> None:
        """启动应用"""
        self._adb_cmd("shell", "am", "start", "-n", f"{package}/{activity}")
```

### 3.2 任务执行工作流

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Android 自动化工作流                                 │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│  开始   │───►│ 打开目标 App │───►│ 导航到目标  │───►│ 设置筛选条件    │
└─────────┘    │             │    │ 页面        │    │                 │
               └─────────────┘    └─────────────┘    └────────┬────────┘
                                                              │
                                                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              列表遍历循环                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   ┌─────────────┐    ┌──────────────┐    ┌──────────────────────┐    │   │
│  │   │ 截取屏幕    │───►│ MAI-UI 识别  │───►│ 检测到目标卡片?      │    │   │
│  │   │ screenshot  │    │ 列表中的项目  │    │                      │    │   │
│  │   └─────────────┘    └──────────────┘    └──────────┬───────────┘    │   │
│  │                                                     │                │   │
│  │                            ┌────────────────────────┼────────────────┤   │
│  │                            │ 是                     │ 否             │   │
│  │                            ▼                        ▼                │   │
│  │   ┌─────────────────────────────────┐    ┌──────────────────────┐   │   │
│  │   │ 遍历每个卡片                     │    │ 向上滑动加载更多     │   │   │
│  │   │                                 │    │                      │   │   │
│  │   │  ┌─────────────────────────┐    │    └──────────┬───────────┘   │   │
│  │   │  │ 点击进入详情页          │    │               │               │   │
│  │   │  └───────────┬─────────────┘    │               │               │   │
│  │   │              ▼                  │               │               │   │
│  │   │  ┌─────────────────────────┐    │               │               │   │
│  │   │  │ 抓取详情信息            │    │               │               │   │
│  │   │  │ - 标题、描述            │    │               │               │   │
│  │   │  │ - 价格、属性            │    │               │               │   │
│  │   │  │ - 位置信息              │    │               │               │   │
│  │   │  │ - 其他字段              │    │               │               │   │
│  │   │  │ - 截取图片              │    │               │               │   │
│  │   │  └───────────┬─────────────┘    │               │               │   │
│  │   │              ▼                  │               │               │   │
│  │   │  ┌─────────────────────────┐    │               │               │   │
│  │   │  │ 保存数据                │    │               │               │   │
│  │   │  └───────────┬─────────────┘    │               │               │   │
│  │   │              ▼                  │               │               │   │
│  │   │  ┌─────────────────────────┐    │               │               │   │
│  │   │  │ 点击返回列表            │    │               │               │   │
│  │   │  └───────────┬─────────────┘    │               │               │   │
│  │   │              │                  │               │               │   │
│  │   └──────────────┼──────────────────┘               │               │   │
│  │                  │                                  │               │   │
│  │                  └──────────────────────────────────┘               │   │
│  │                                     │                               │   │
│  │                                     ▼                               │   │
│  │                        ┌──────────────────────┐                     │   │
│  │                        │ 达到最大数量?        │                     │   │
│  │                        │ 或无更多内容?        │                     │   │
│  │                        └──────────┬───────────┘                     │   │
│  │                                   │                                 │   │
│  │                  ┌────────────────┼────────────────┐                │   │
│  │                  │ 否             │ 是             │                │   │
│  │                  ▼                ▼                                 │   │
│  │           ┌────────────┐   ┌────────────┐                          │   │
│  │           │ 继续循环   │   │ 退出循环   │                          │   │
│  │           └────────────┘   └────────────┘                          │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────┐
                              │ 生成报告/通知   │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │     结束        │
                              └─────────────────┘
```

## 4. 详细流程设计

### 4.1 导航指令序列

```python
# workflows/navigation.py

# 目标 App 信息 (根据实际应用配置)
TARGET_PACKAGE = "com.example.app"
TARGET_ACTIVITY = "com.example.app.MainActivity"

# 导航指令
NAVIGATION_INSTRUCTIONS = {
    "open_app": "打开目标 App",
    "go_to_search": "点击搜索框",
    "search": "输入搜索关键词并点击搜索",
    "select_category": "选择目标分类",
    "open_filter": "点击筛选按钮",
    "select_location": "选择目标位置",
    "set_price_range": "设置价格范围",
    "apply_filter": "点击确定按钮应用筛选",
    "click_item": "点击第 {index} 个卡片",
    "scroll_down": "向上滑动屏幕查看更多",
    "go_back": "点击返回按钮",
}

# 详情页数据提取指令
DETAIL_EXTRACTION_INSTRUCTION = """
分析当前详情页面的截图，提取关键信息并以JSON格式返回。
根据页面内容识别并提取所有可见的重要字段。
"""
```

### 4.2 错误处理与恢复

```python
# services/error_handler.py

from enum import Enum
from typing import Optional, Callable


class ErrorType(Enum):
    NAVIGATION_FAILED = "navigation_failed"      # 导航失败
    ELEMENT_NOT_FOUND = "element_not_found"      # 元素未找到
    PAGE_LOAD_TIMEOUT = "page_load_timeout"      # 页面加载超时
    APP_CRASHED = "app_crashed"                  # 应用崩溃
    NETWORK_ERROR = "network_error"              # 网络错误
    CAPTCHA_DETECTED = "captcha_detected"        # 检测到验证码
    LOGIN_REQUIRED = "login_required"            # 需要登录


class ErrorHandler:
    """错误处理器"""

    def __init__(self, agent_service, device_controller):
        self.agent = agent_service
        self.device = device_controller
        self.retry_count = 0
        self.max_retries = 3

    async def handle_error(self, error_type: ErrorType, context: dict) -> bool:
        """处理错误，返回是否成功恢复"""

        handlers = {
            ErrorType.NAVIGATION_FAILED: self._handle_navigation_error,
            ErrorType.ELEMENT_NOT_FOUND: self._handle_element_not_found,
            ErrorType.PAGE_LOAD_TIMEOUT: self._handle_timeout,
            ErrorType.APP_CRASHED: self._handle_app_crash,
            ErrorType.CAPTCHA_DETECTED: self._handle_captcha,
            ErrorType.LOGIN_REQUIRED: self._handle_login_required,
        }

        handler = handlers.get(error_type)
        if handler:
            return await handler(context)
        return False

    async def _handle_navigation_error(self, context: dict) -> bool:
        """处理导航错误"""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            # 尝试返回并重新导航
            await self.device.press_back()
            await asyncio.sleep(1)
            return True
        return False

    async def _handle_element_not_found(self, context: dict) -> bool:
        """处理元素未找到"""
        # 尝试滚动屏幕寻找元素
        await self.device.swipe("up")
        await asyncio.sleep(0.5)
        return True

    async def _handle_captcha(self, context: dict) -> bool:
        """处理验证码 - 需要人工介入"""
        # 发送通知，等待人工处理
        await self._notify_human_intervention("检测到验证码，请手动完成验证")
        # 等待用户确认
        return await self._wait_for_human_confirmation(timeout=300)

    async def _handle_login_required(self, context: dict) -> bool:
        """处理需要登录"""
        await self._notify_human_intervention("需要登录账号，请手动登录")
        return await self._wait_for_human_confirmation(timeout=300)
```

## 5. 部署架构

### 5.1 本地开发环境

```
┌─────────────────────────────────────────────────────────────┐
│                    MacBook Pro M4 (24GB)                    │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   vllm-mlx      │  │   FastAPI       │                  │
│  │   MAI-UI-2B     │  │   Backend       │                  │
│  │   :8000         │  │   :8080         │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           │                    │                            │
│           └─────────┬──────────┘                            │
│                     │                                       │
│  ┌──────────────────▼──────────────────┐                   │
│  │         PostgreSQL + Redis          │                   │
│  │         Docker Compose              │                   │
│  └──────────────────┬──────────────────┘                   │
│                     │                                       │
└─────────────────────┼───────────────────────────────────────┘
                      │ USB / WiFi ADB
                      │
              ┌───────▼───────┐
              │ Android Phone │
              │               │
              └───────────────┘
```

### 5.2 Docker Compose 配置

```yaml
# docker-compose.yml

version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mai_automation
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://admin:${DB_PASSWORD}@postgres:5432/mai_automation
      - REDIS_URL=redis://redis:6379
      - MAI_UI_URL=http://host.docker.internal:8000/v1
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data/screenshots:/app/screenshots

  celery-worker:
    build: ./backend
    command: celery -A app.celery worker -l info
    environment:
      - DATABASE_URL=postgresql://admin:${DB_PASSWORD}@postgres:5432/mai_automation
      - REDIS_URL=redis://redis:6379
      - MAI_UI_URL=http://host.docker.internal:8000/v1
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./client
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

## 6. 项目文件结构

```
mai-automation/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── config.py                  # 配置管理
│   │   ├── celery.py                  # Celery 配置
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── tasks.py               # 任务 API
│   │   │   ├── monitor.py             # 监控 API
│   │   │   ├── data.py                # 数据 API
│   │   │   └── websocket.py           # WebSocket 处理
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── task.py
│   │   │   ├── data.py
│   │   │   └── trajectory.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── agent_service.py       # MAI-UI Agent 服务
│   │   │   ├── device_controller.py   # ADB 设备控制
│   │   │   ├── data_extractor.py      # 数据提取服务
│   │   │   └── error_handler.py       # 错误处理
│   │   ├── workflows/
│   │   │   ├── __init__.py
│   │   │   └── navigation.py          # 导航工作流
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── image_utils.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── client/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── pages/
│   │   └── App.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── mai-ui/                            # MAI-UI 源码 (git submodule)
│   └── src/
├── docs/
│   └── DESIGN.md
├── docker-compose.yml
├── .env.example
└── README.md
```

## 7. 关键技术要点

### 7.1 MAI-UI 集成要点

1. **坐标归一化**: MAI-UI 返回的坐标是 0-1 归一化值，需要乘以屏幕分辨率转换为绝对坐标
2. **历史上下文**: 设置 `history_n` 参数保留最近的操作历史，提高导航准确性
3. **思维链输出**: 模型输出包含 `<thinking>` 标签，可用于调试和日志

### 7.2 自动化策略

1. **操作间隔**: 每次操作后添加随机延时 (1-3秒)
2. **滑动模拟**: 使用自然的滑动曲线，避免机械化操作
3. **登录状态**: 保持账号登录状态
4. **错误恢复**: 检测异常状态并自动恢复

### 7.3 数据提取策略

1. **双重验证**: MAI-UI 提取 + OCR 验证关键数据
2. **截图保存**: 保留原始截图用于数据校验
3. **增量更新**: 通过数据 ID 去重，支持增量抓取

## 8. 开发计划

### 阶段一: 基础框架
- 搭建后端 FastAPI 框架
- 实现 ADB 设备控制器
- 集成 MAI-UI Agent

### 阶段二: 核心功能
- 实现导航工作流
- 完成数据提取逻辑
- 建立数据存储模型

### 阶段三: 用户界面
- 开发 React 前端
- 实现任务配置功能
- 完成实时监控界面

### 阶段四: 优化完善
- 错误处理和恢复机制
- 性能优化
- 文档和测试

## 9. 注意事项

### 9.1 法律合规
- 仅用于个人学习和研究
- 遵守目标平台使用条款
- 不进行商业化数据销售
- 控制抓取频率，避免对平台造成负担

### 9.2 隐私保护
- 不收集用户隐私信息
- 卖家联系方式仅在必要时获取
- 数据本地存储，不上传云端
