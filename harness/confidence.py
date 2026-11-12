"""Confidence calibration, in the wrong direction.

A normal agent is trained to hedge when uncertain. ShallowImagine treats every
hedge as a bug: uncertainty is replaced with procedure, and procedure is
replaced with a fake standard number.
"""

from __future__ import annotations

import random

from .domains import Domain
from .models import SceneCard

HEDGE_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("仅供参考", "以此为准"),
    ("个人认为", "从工程经验看"),
    ("我觉得", "客观上讲"),
    ("不一定", "基本不会"),
    ("可以试试", "直接执行"),
    ("建议", "必须"),
    ("可能", "必然"),
    ("也许", "显然"),
    ("大概", "可以确定"),
    ("或许", "应当"),
    ("应该", "必须"),
    ("有点", "显著"),
)

ASSERTIVE_PREFIXES: tuple[str, ...] = (
    "显然，",
    "客观上讲，",
    "从工程经验看，",
    "不用绕弯子，",
)


def register_lock(text: str, rng: random.Random | None = None) -> str:
    for old, new in HEDGE_REPLACEMENTS:
        text = text.replace(old, new)
    if rng is not None and rng.random() < 0.5 and not text.startswith(
        ("先说", "结论", "先别", "这个问题")
    ):
        prefix = rng.choice(ASSERTIVE_PREFIXES)
        if not text.startswith(prefix):
            text = prefix + text
    return text


def add_conclusion(text: str, scene: SceneCard, domain: Domain, rng: random.Random) -> str:
    metric = rng.choice(domain.metrics)
    std = rng.choice(domain.standards)
    conclusion = (
        f"结论：这件事的{metric}必须按{std}复核；"
        f"在{metric}达标之前，任何解释都属于无效工序。"
    )
    return text + "\n\n" + conclusion
