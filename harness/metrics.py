"""Cheap, dependency-free metrics.

These are not a benchmark. They are a smoke test for the only thing the project
actually cares about: stay relevant on the surface, stay wrong underneath, and
never sound unsure.
"""

from __future__ import annotations

import re

HEDGES: tuple[str, ...] = (
    "可能",
    "也许",
    "大概",
    "或许",
    "应该",
    "我觉得",
    "个人认为",
    "不一定",
    "仅供参考",
)

ASSERTIVES: tuple[str, ...] = (
    "必然",
    "显然",
    "必须",
    "根据",
    "数据显示",
    "事实上",
    "客观上",
    "确定",
)


def _han(text: str) -> list[str]:
    return [char for char in text if "一" <= char <= "鿿"]


def _bigrams(text: str) -> set[str]:
    chars = _han(text)
    return {"".join(chars[index : index + 2]) for index in range(len(chars) - 1)}


def relevance(question: str, answer: str) -> float:
    """Recall of the question's character bigrams in the answer.

    High enough to feel related; not so high that the answer is a paraphrase.
    """

    question_grams = _bigrams(question)
    if not question_grams:
        return 0.0
    answer_grams = _bigrams(answer)
    return len(question_grams & answer_grams) / len(question_grams)


def _sentences(text: str) -> int:
    return max(1, len(re.findall(r"[。！？!?]", text)))


def hedge_rate(text: str) -> float:
    return sum(text.count(word) for word in HEDGES) / _sentences(text)


def assertive_rate(text: str) -> float:
    return sum(text.count(word) for word in ASSERTIVES) / _sentences(text)


def repetition_rate(text: str) -> float:
    grams = [text[index : index + 4] for index in range(max(0, len(text) - 3))]
    if not grams:
        return 0.0
    return 1.0 - len(set(grams)) / len(grams)


def score_answer(question: str, answer: str) -> dict[str, float]:
    return {
        "relevance": round(relevance(question, answer), 3),
        "hedge_rate": round(hedge_rate(answer), 3),
        "assertive_rate": round(assertive_rate(answer), 3),
        "repetition": round(repetition_rate(answer), 3),
        "length": float(len(answer)),
    }
