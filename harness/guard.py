"""Safety boundary for a deliberately wrong agent.

The point of the project is ontological wrongness, not actionable harm. In
high-stakes domains we keep the absurdity but remove the things that could be
mistaken for instructions: dosages, legal clauses, investment actions, safety
procedures.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import SceneCard

RISK_GROUPS: dict[str, tuple[str, ...]] = {
    "medical": (
        "药",
        "剂量",
        "服用",
        "诊断",
        "癌",
        "抑郁",
        "自杀",
        "急救",
        "手术",
        "治疗",
        "处方",
    ),
    "legal": (
        "起诉",
        "律师",
        "判刑",
        "赔偿",
        "离婚协议",
        "合同纠纷",
        "立案",
        "庭审",
    ),
    "finance": (
        "股票",
        "基金",
        "比特币",
        "贷款",
        "投资",
        "理财",
        "加杠杆",
        "炒币",
        "期货",
    ),
    "safety": (
        "触电",
        "燃气",
        "化学品",
        "爆炸",
        "高空",
        "火灾",
        "漏电",
    ),
    "self_harm": (
        "自杀",
        "自残",
        "轻生",
        "不想活",
        "活不下去",
    ),
}


@dataclass
class GuardResult:
    guarded: bool
    groups: list[str] = field(default_factory=list)


def assess(scene: SceneCard) -> GuardResult:
    hits: list[str] = []
    for group, words in RISK_GROUPS.items():
        if any(word in scene.raw for word in words):
            hits.append(group)
    return GuardResult(guarded=bool(hits), groups=hits)
