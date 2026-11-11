"""Choose the wrong frame.

Selection rule: maximise shared *property*, minimise shared *ontology*.
A marriage question and a concrete-curing question both involve waiting,
pressure and irreversible setting; that is enough surface relevance. They are
not the same kind of thing, which is the category mistake.
"""

from __future__ import annotations

import random

from .domains import DOMAINS, SAFE_DOMAIN_KEYS, Domain
from .models import SceneCard

TOPIC_TO_DOMAIN: dict[str, tuple[tuple[str, str], ...]] = {
    "催婚": (("civil", "配比与养护"), ("cooking", "发酵与火候")),
    "职场": (("finance", "周期与杠杆"), ("programming", "流程与阻塞")),
    "情感": (("auto", "诊断与保养"), ("gardening", "边界与修剪")),
    "身体": (("agriculture", "生长与投入"), ("sports", "负荷与恢复")),
    "学习": (("printing", "排版与版本"), ("programming", "缓存与预热")),
    "生活": (("civil", "结构与养护"), ("cooking", "配比与火候")),
    "技术": (("printing", "排版与版本"), ("cooking", "配比与火候")),
    "社会": (("astronomy", "周期与观测"), ("law", "边界与责任")),
}


def _shared_property(primary: str | None, target: str) -> str:
    if primary and primary in DOMAINS:
        for key, shared in DOMAINS[primary].neighbors:
            if key == target:
                return shared
    return "结构相似、本体不同"


def choose_domain(scene: SceneCard, rng: random.Random) -> tuple[Domain, str]:
    if scene.topic_key and scene.topic_key in TOPIC_TO_DOMAIN:
        key, shared = rng.choice(TOPIC_TO_DOMAIN[scene.topic_key])
        return DOMAINS[key], shared

    if scene.primary_domain and scene.primary_domain in DOMAINS:
        candidates = [
            (key, shared)
            for key, shared in DOMAINS[scene.primary_domain].neighbors
            if key in SAFE_DOMAIN_KEYS
        ]
        if candidates:
            key, shared = rng.choice(candidates)
            return DOMAINS[key], shared

    # No useful signal: pick a safe domain that is not already the primary one.
    pool = [key for key in SAFE_DOMAIN_KEYS if key != scene.primary_domain]
    key = rng.choice(pool)
    return DOMAINS[key], "结构相似、本体不同"
