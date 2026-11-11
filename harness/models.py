from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SceneCard:
    """What the parser believes the user said.

    The joke starts here: the card is a *shallow* reading of the input. It keeps
    the surface nouns and the emotional pressure, and drops the actual intent.
    """

    raw: str
    topic: str
    topic_key: str | None = None
    entities: list[str] = field(default_factory=list)
    numbers: list[tuple[str, str]] = field(default_factory=list)
    domain_scores: dict[str, int] = field(default_factory=dict)
    primary_domain: str | None = None
    question_type: str = "statement"
    emotion: str = "neutral"
    guarded: bool = False
    guard_groups: list[str] = field(default_factory=list)


@dataclass
class Claim:
    """One confident sentence with a known number of category violations."""

    text: str
    operator: str
    violations: int = 1


@dataclass
class Result:
    text: str
    meta: dict[str, Any] = field(default_factory=dict)

    def explain(self) -> str:
        keys = (
            "topic",
            "topic_key",
            "primary_domain",
            "target_domain",
            "shared_property",
            "operators",
            "guarded",
            "guard_groups",
            "backend",
            "metrics",
        )
        lines = ["--- shallowimagion trace ---"]
        for key in keys:
            if key in self.meta:
                lines.append(f"{key}: {self.meta[key]}")
        return "\n".join(lines)
