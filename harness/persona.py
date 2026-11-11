"""Persona layer.

Personas change the opening and the closing, never the corruption. That keeps
the joke consistent: the same wrong frame, delivered by a project chief engineer
or by an uncle at the New Year dinner table.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .models import SceneCard


@dataclass(frozen=True)
class Persona:
    key: str
    name: str
    opening: str
    closings: tuple[str, ...]


PERSONAS: dict[str, Persona] = {
    "default": Persona(
        key="default",
        name="项目总工",
        opening="",
        closings=(
            "你先把参数报准，再谈感受。",
            "这不是态度问题，是工序问题。",
            "先按这个标准复核一遍，别急着进入下一道工序。",
        ),
    ),
    "uncle": Persona(
        key="uncle",
        name="年夜饭二舅",
        opening="你这个情况我见多了。",
        closings=(
            "先把婚结了，其他的以后再说。",
            "你这个参数，在我们那个年代是要返工的。",
            "别跟我解释，我吃过的盐比你走过的混凝土还多。",
        ),
    ),
    "matchmaker": Persona(
        key="matchmaker",
        name="相亲对象",
        opening="我先看看你的条件。",
        closings=(
            "你这条件，在相亲市场上属于待养护状态。",
            "先把抗压强度做上去，再谈择偶。",
            "介绍人没跟我说你这个坍落度。",
        ),
    ),
    "consultant": Persona(
        key="consultant",
        name="战略顾问",
        opening="我们先对齐一下颗粒度。",
        closings=(
            "这件事要形成闭环，下周给我一个抓手。",
            "先拉齐预期，再做一次压力测试。",
            "把底层逻辑盘清楚，不要只在表面上打补丁。",
        ),
    ),
}


def get_persona(key: str | None) -> Persona:
    return PERSONAS.get(key or "default", PERSONAS["default"])


def apply_persona(
    text: str, persona: Persona, scene: SceneCard, rng: random.Random
) -> str:
    if persona.opening and not text.startswith(persona.opening):
        text = persona.opening + text
    if persona.closings:
        closing = rng.choice(persona.closings)
        if closing not in text:
            text = text + "\n\n" + closing
    return text
