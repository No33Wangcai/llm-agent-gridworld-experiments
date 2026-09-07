#!/usr/bin/env python3
"""A tiny text-first grid world for experimenting with AI game agents."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import sys
from typing import Optional, Tuple
from urllib.request import Request, urlopen


class MemoryTool:
    """Episodic memory that records observations without storing coordinates."""

    def __init__(self) -> None:
        self.entries: list[str] = []

    def remember(self, entry: str) -> None:
        self.entries.append(entry)

    def recall(self, limit: int = 20) -> str:
        if not self.entries:
            return "暂无行动记忆。"
        return "\n".join(f"{index + 1}. {entry}" for index, entry in
                         enumerate(self.entries[-limit:]))


@dataclass
class World:
    width: int = 9
    height: int = 7
    player: tuple[int, int] = (1, 5)
    objects: dict[str, tuple[int, int]] = field(default_factory=lambda: {
        "chest": (3, 3),
        "guard": (6, 2),
        "door": (7, 1),
    })
    walls: set[tuple[int, int]] = field(default_factory=lambda: {
        (2, 1), (2, 2), (2, 3), (5, 3), (5, 4), (5, 5),
    })
    inventory: set[str] = field(default_factory=set)
    chest_open: bool = False
    door_open: bool = False
    log: list[str] = field(default_factory=list)
    memory: MemoryTool = field(default_factory=MemoryTool)

    def render(self) -> str:
        symbols = {"chest": "C", "guard": "N", "door": "D"}
        lines = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                pos = (x, y)
                if pos == self.player:
                    row.append("@")
                elif pos in self.walls:
                    row.append("#")
                elif pos == self.objects["chest"] and not self.chest_open:
                    row.append("C")
                elif pos == self.objects["door"] and not self.door_open:
                    row.append("D")
                else:
                    item = next((name for name, location in self.objects.items()
                                 if location == pos and name == "guard"), None)
                    row.append(symbols[item] if item else ".")
            lines.append("".join(row))
        return "\n".join(lines)

    def describe(self) -> str:
        nearby = []
        for name, location in self.objects.items():
            distance = abs(location[0] - self.player[0]) + abs(location[1] - self.player[1])
            if distance <= 2 and not (name == "chest" and self.chest_open):
                nearby.append(name)
        found = ", ".join(nearby) if nearby else "没有明显目标"
        bag = ", ".join(sorted(self.inventory)) if self.inventory else "空"
        return f"你在 {self.player}。附近：{found}。背包：{bag}。"

    def state_for_model(self) -> str:
        """Return partial observability: never expose map or any coordinates."""
        return json.dumps({
            "inventory": sorted(self.inventory),
            "chest_open": self.chest_open,
            "door_open": self.door_open,
            "available_actions": self.available_actions(),
        }, ensure_ascii=False)

    def available_actions(self) -> list[str]:
        if self.player == self.objects["chest"] and not self.chest_open:
            return ["move", "interact"]
        return ["move"]

    def capability_prompt(self) -> str:
        if "interact" in self.available_actions():
            return ('你已到达箱子，发现新能力 interact：打开脚下箱子。'
                    '当前 action 可以是 move 或 interact。使用 {"action":"interact"} 可完成目标。'
                    '请自行选择下一步。')
        return '当前唯一能力是 move，只能选择移动。action 必须是 move。'

    def execute_agent_action(self, action: str, direction: Optional[str]) -> str:
        if action not in self.available_actions():
            return "动作不可用，未执行，你仍在原地。" + self.capability_prompt()
        if action == "move":
            if direction not in {"上", "下", "左", "右"}:
                return "方向无效，未执行，你仍在原地。"
            return self.move(direction)
        return self.interact()

    def goal_state(self) -> str:
        status = "已打开" if self.chest_open else "未打开"
        return f"目标：找到并打开箱子。箱子状态：{status}。你不知道地图、墙体、箱子和自己的坐标，只能通过动作结果探索。"

    def move(self, direction: str) -> str:
        offsets = {"上": (0, -1), "下": (0, 1), "左": (-1, 0), "右": (1, 0)}
        dx, dy = offsets[direction]
        target = (self.player[0] + dx, self.player[1] + dy)
        if not (0 <= target[0] < self.width and 0 <= target[1] < self.height):
            return "那里超出了地图。"
        if target in self.walls:
            return "前面是一堵墙。"
        self.player = target
        if target == self.objects["chest"] and not self.chest_open:
            return "移动成功。你已到达箱子所在位置。【下一步】请立即执行交互以打开箱子。"
        return f"移动{direction}成功。"

    def interact(self, target: Optional[str] = None) -> str:
        if target is None:
            nearby = [
                name for name, location in self.objects.items()
                if location == self.player
            ]
            if not nearby:
                return "附近没有可以交互的对象。"
            target = nearby[0]
        location = self.objects.get(target)
        if location is None:
            return f"找不到目标：{target}。"
        if location != self.player:
            return "这里没有可交互的目标。"
        if target == "chest":
            if self.chest_open:
                return "箱子已经打开了。"
            self.chest_open = True
            self.inventory.add("key")
            return "你打开了箱子，获得了钥匙。"
        if target == "door":
            if "key" not in self.inventory:
                return "门锁着，你需要一把钥匙。"
            self.door_open = True
            return "你用钥匙打开了门。"
        if target == "guard":
            return "卫兵说：城门后面藏着一座古老的图书馆。"
        return "没有发生什么。"


def parse_command(text: str) -> Tuple[str, Optional[str]]:
    text = text.strip().lower()
    directions = {"上": "上", "北": "上", "下": "下", "南": "下",
                  "左": "左", "西": "左", "右": "右", "东": "右"}
    for word, direction in directions.items():
        if word in text and any(mark in text for mark in ("走", "移动", "去", "move")):
            return "move", direction
    if text in {"交互", "互动", "interact"}:
        return "interact", None
    if any(word in text for word in ("观察", "看看", "附近", "look", "describe")):
        return "describe", None
    return "help", None


def parse_with_qwen(text: str, world: World, model: str = "qwen2.5:1.5b") -> Tuple[str, Optional[str]]:
    """Ask Ollama for one safe game action, falling back to local parsing on errors."""
    system = (
        "你是一个网格游戏指令解析器。只输出一个JSON对象，不要解释。"
        "action只能是move、interact、describe、help；"
        "move时direction只能是上、下、左、右；其他动作target必须为null。"
    )
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 40},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"当前状态：{world.state_for_model()}\n玩家输入：{text}"},
        ],
    }
    try:
        request = Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        raw_output = body["message"]["content"]
        print(f"[Qwen 输出] {raw_output}")
        result = json.loads(raw_output)
        action = result.get("action")
        direction = result.get("direction")
        direction_aliases = {"上": "上", "north": "上", "up": "上",
                             "下": "下", "south": "下", "down": "下",
                             "左": "左", "west": "左", "left": "左",
                             "右": "右", "east": "右", "right": "右"}
        if action == "move" and direction in direction_aliases:
            return "move", direction_aliases[direction]
        if action in {"interact", "describe", "help"}:
            return action, None
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"[模型不可用，使用本地解析器：{error}]", file=sys.stderr)
    return parse_command(text), print(f"parse_command(text)={parse_command(text)}")


def agent_step(world: World, feedback: str = "", model: str = "qwen2.5:1.5b") -> Tuple[str, Optional[str], str, str]:
    """Choose one executable step and return its action, explanation, and reason."""
    system = (
        "你是一个网格游戏解题Agent。目标是找到并打开箱子。"
        "每次只能选择一个动作。只输出JSON，不要输出Markdown。"
        "只能使用当前开放的能力；move的direction只能是上、下、左、右。"
        "explanation必须是简短中文行动说明，不超过30字。"
        "reason必须解释为什么选择这个方向，基于上一步反馈或探索策略，不超过50字。"
        "你无法看到地图，必须通过移动结果探索；遇到阻挡后尝试其他方向。"
        "如果上一条环境反馈说某方向越界或撞墙，下一步绝对禁止再次选择该方向。"
        "必须真正改变方向，而不是重复解释同一个失败动作。"
        "你拥有行动记忆，必须读取记忆，避免重复已经失败或反复走过的动作。"
    )
    system += world.capability_prompt()
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 80},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{world.goal_state()}\n状态：{world.state_for_model()}\n"
             f"上一步结果：{feedback or '这是第一步'}\n行动记忆：\n{world.memory.recall()}"},
        ],
    }
    try:
        request = Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        raw_output = body["message"]["content"]
        print(f"[Qwen 输出] {raw_output}")
        result = json.loads(raw_output)
        action = result.get("action")
        direction_aliases = {"上": "上", "up": "上", "north": "上",
                             "下": "下", "down": "下", "south": "下",
                             "左": "左", "left": "左", "west": "左",
                             "右": "右", "right": "右", "east": "右"}
        direction = result.get("direction")
        # Small models sometimes combine the action and direction into one field.
        if isinstance(action, str) and action.startswith("move"):
            combined_direction = action[4:].strip(" ：:，,")
            if direction is None and combined_direction:
                direction = combined_direction
            action = "move"
        if action == "move" and direction in direction_aliases:
            return ("move", direction_aliases[direction],
                    result.get("explanation", ""), result.get("reason", ""))
        if action == "interact":
            return ("interact", None, result.get("explanation", ""),
                    result.get("reason", ""))
        raise ValueError("模型返回了无效动作")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"[Agent 错误] {error}")
        return "help", None, "", ""


def solve_chest_with_qwen(world: World, max_steps: int = 100) -> None:
    print("\n=== AI 自动解题：找到并打开箱子 ===")
    feedback = ""
    for step in range(1, max_steps + 1):
        if world.chest_open:
            print(f"[完成] 第 {step - 1} 步：箱子已打开，获得钥匙。")
            return
        action, target, explanation, reason = agent_step(world, feedback)
        print(f"[第 {step} 步] {explanation}")
        print(f"[选择理由] {reason}")
        result = world.execute_agent_action(action, target)
        print(f"[执行结果] {result}")
        if action == "move" and result == "那里超出了地图。":
            feedback = (f"【环境反馈】你刚才选择了向{target}移动，但该方向超出边界，"
                        f"玩家位置没有改变。\n【下一步约束】禁止再次向{target}移动。"
                        "请结合行动记忆，自己选择其他方向。")
        elif action == "move" and result == "前面是一堵墙。":
            feedback = (f"【环境反馈】你刚才选择了向{target}移动，但前方是墙，"
                        f"玩家位置没有改变。\n【下一步约束】禁止再次向{target}移动。"
                        "请结合行动记忆，自己选择其他方向。")
        elif "已到达箱子所在位置" in result:
            feedback = "【能力发现】" + world.capability_prompt()
        else:
            feedback = f"【环境反馈】你刚才的动作结果是：{result} 请继续自行决定下一步。"
        print(f"[发送给 Agent 的反馈] {feedback}")
        world.memory.remember(f"选择：{action} {target or ''}；{feedback}")
        print(f"[记忆] 已保存，当前 {len(world.memory.entries)} 条")
        print(world.render())
        if world.chest_open:
            print(f"[完成] 第 {step} 步：箱子已打开，获得钥匙。")
            return
    print("[停止] 超过最大步数，未能完成目标。")


def main() -> None:
    world = World()
    use_ai = "--ai" in sys.argv
    solve = "--solve" in sys.argv
    mode = "Qwen2.5 1.5B" if use_ai else "本地规则解析器"
    print(f"Text World Demo | 模式：{mode} | 输入 help 查看命令，输入 quit 退出。\n")
    print(world.render())
    if solve:
        solve_chest_with_qwen(world)
        return
    while True:
        try:
            text = input("\n你> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.strip().lower() in {"quit", "exit", "退出"}:
            break
        action, target = parse_with_qwen(text, world) if use_ai else parse_command(text)
        if action == "move":
            result = world.move(target)  # type: ignore[arg-type]
        elif action == "interact":
            result = world.interact(target)
        elif action == "describe":
            result = world.describe()
        else:
            result = "可用指令：向上/下/左/右移动；交互；观察；退出。"
        print(result)
        print(world.render())


if __name__ == "__main__":
    main()
