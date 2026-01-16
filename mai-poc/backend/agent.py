"""
MAI-UI Agent Wrapper

Based on https://github.com/Tongyi-MAI/MAI-UI/tree/main/src
"""

import re
import base64
from io import BytesIO
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, field
from PIL import Image
from openai import OpenAI


# Scale factor for coordinate normalization (MAI-UI uses 999)
SCALE_FACTOR = 999


@dataclass
class TrajStep:
    """Single step in trajectory"""
    image_pil: Optional[Image.Image] = None
    prediction: str = ""
    action: Dict[str, Any] = field(default_factory=dict)
    thought: str = ""


@dataclass
class TrajMemory:
    """Trajectory memory"""
    goal: str = ""
    task_id: str = ""
    steps: List[TrajStep] = field(default_factory=list)


# System prompts
GROUNDING_PROMPT = """You are a GUI grounding agent. Given a screenshot and an instruction, identify the UI element and return its coordinates.

Output format:
<thinking>Your analysis of the screenshot</thinking>
<answer>click(x, y)</answer>

Where x and y are coordinates from 0 to 999, representing the position on screen.
"""

NAVIGATION_PROMPT = """You are a mobile GUI automation agent. Given a screenshot and task instruction, decide the next action.

Available actions:
- click(x, y): Tap at coordinates (0-999 scale)
- long_press(x, y): Long press at coordinates
- type(text): Input text
- swipe(direction): Swipe up/down/left/right
- back(): Press back button
- home(): Press home button
- wait(): Wait for page load
- terminate(): Task complete
- answer(text): Return answer to user

Output format:
<thinking>Your analysis and reasoning</thinking>
<tool_call>action_name(parameters)</tool_call>
"""


def pil_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string"""
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def parse_coordinates(text: str) -> Optional[Tuple[float, float]]:
    """Extract coordinates from response and normalize to 0-1"""
    # Match patterns like click(123, 456) or (123, 456)
    patterns = [
        r'click\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)',
        r'\(\s*(\d+)\s*,\s*(\d+)\s*\)',
        r'(\d+)\s*,\s*(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            x = int(match.group(1)) / SCALE_FACTOR
            y = int(match.group(2)) / SCALE_FACTOR
            return (min(max(x, 0), 1), min(max(y, 0), 1))

    return None


def parse_action(text: str) -> Dict[str, Any]:
    """Parse action from model response"""
    action = {"action": "wait", "raw": text}

    # Extract tool_call content
    tool_match = re.search(r'<tool_call>(.*?)</tool_call>', text, re.DOTALL)
    if tool_match:
        tool_text = tool_match.group(1).strip()
    else:
        tool_text = text

    # Parse different action types
    if 'click' in tool_text.lower():
        coords = parse_coordinates(tool_text)
        if coords:
            action = {"action": "click", "coordinates": list(coords)}

    elif 'long_press' in tool_text.lower():
        coords = parse_coordinates(tool_text)
        if coords:
            action = {"action": "long_press", "coordinates": list(coords)}

    elif 'type(' in tool_text.lower() or 'input(' in tool_text.lower():
        match = re.search(r'(?:type|input)\s*\(\s*["\'](.+?)["\']\s*\)', tool_text)
        if match:
            action = {"action": "type", "text": match.group(1)}

    elif 'swipe' in tool_text.lower():
        for direction in ['up', 'down', 'left', 'right']:
            if direction in tool_text.lower():
                action = {"action": "swipe", "direction": direction}
                break

    elif 'back' in tool_text.lower():
        action = {"action": "back"}

    elif 'home' in tool_text.lower():
        action = {"action": "home"}

    elif 'terminate' in tool_text.lower():
        action = {"action": "terminate"}

    elif 'answer' in tool_text.lower():
        match = re.search(r'answer\s*\(\s*["\'](.+?)["\']\s*\)', tool_text, re.DOTALL)
        if match:
            action = {"action": "answer", "text": match.group(1)}

    # Extract thinking
    think_match = re.search(r'<thinking>(.*?)</thinking>', text, re.DOTALL)
    if think_match:
        action["thought"] = think_match.group(1).strip()

    return action


class MAIAgent:
    """
    MAI-UI Navigation Agent

    Provides GUI automation capabilities using vision-language model.
    """

    def __init__(
        self,
        llm_base_url: str = "http://127.0.0.1:8000/v1",
        model_name: str = "mai-ui-2b",
        history_n: int = 3,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ):
        self.client = OpenAI(
            base_url=llm_base_url,
            api_key="not-needed"
        )
        self.model_name = model_name
        self.history_n = history_n
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.memory = TrajMemory()

    def reset(self, goal: str = "", task_id: str = "") -> None:
        """Reset agent for new task"""
        self.memory = TrajMemory(goal=goal, task_id=task_id)

    def _build_messages(
        self,
        instruction: str,
        image: Image.Image,
        system_prompt: str
    ) -> list:
        """Build messages for API call"""
        messages = [{"role": "system", "content": system_prompt}]

        # Add history images if available
        history_images = []
        if self.history_n > 0 and len(self.memory.steps) > 0:
            recent_steps = self.memory.steps[-self.history_n:]
            for step in recent_steps:
                if step.image_pil:
                    history_images.append(step.image_pil)

        # Build user message with images
        content = []

        # Add instruction text
        if self.memory.goal:
            content.append({
                "type": "text",
                "text": f"Task: {self.memory.goal}\nCurrent instruction: {instruction}"
            })
        else:
            content.append({"type": "text", "text": instruction})

        # Add history context
        if history_images:
            content.append({
                "type": "text",
                "text": f"\n[Previous {len(history_images)} screenshots for context]"
            })
            for hist_img in history_images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{pil_to_base64(hist_img)}"
                    }
                })

        # Add current screenshot
        content.append({"type": "text", "text": "\n[Current screenshot]"})
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{pil_to_base64(image)}"
            }
        })

        messages.append({"role": "user", "content": content})
        return messages

    def predict(
        self,
        instruction: str,
        image: Image.Image
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Predict next action given instruction and screenshot.

        Args:
            instruction: Task instruction or current step
            image: Current screenshot

        Returns:
            (raw_response, parsed_action)
        """
        messages = self._build_messages(instruction, image, NAVIGATION_PROMPT)

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            prediction = response.choices[0].message.content
        except Exception as e:
            prediction = f"Error: {str(e)}"
            return prediction, {"action": "error", "message": str(e)}

        # Parse action
        action = parse_action(prediction)

        # Save to memory
        step = TrajStep(
            image_pil=image.copy(),
            prediction=prediction,
            action=action,
            thought=action.get("thought", "")
        )
        self.memory.steps.append(step)

        return prediction, action

    def ground(
        self,
        instruction: str,
        image: Image.Image
    ) -> Tuple[str, Optional[Tuple[float, float]]]:
        """
        Ground UI element - find coordinates for instruction.

        Args:
            instruction: What element to find
            image: Screenshot

        Returns:
            (raw_response, coordinates or None)
        """
        messages = self._build_messages(instruction, image, GROUNDING_PROMPT)

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            prediction = response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}", None

        coords = parse_coordinates(prediction)
        return prediction, coords

    @property
    def trajectory(self) -> List[Dict[str, Any]]:
        """Get trajectory as list of dicts"""
        return [
            {
                "step": i,
                "action": step.action,
                "thought": step.thought,
                "prediction": step.prediction[:200] + "..." if len(step.prediction) > 200 else step.prediction
            }
            for i, step in enumerate(self.memory.steps)
        ]
