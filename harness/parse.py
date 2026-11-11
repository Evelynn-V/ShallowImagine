"""Shallow parsing.

We deliberately do *not* try to understand the question. We extract just enough
surface structure to keep the answer tethered to it:

* topic phrase (what the user is talking about)
* entities / numbers (what we can repeat back)
* a coarse domain and question type
* emotional pressure (useful for the persona layer)
"""

from __future__ import annotations

import re

from .domains import TERM_TO_DOMAIN
from .models import SceneCard

NUMBER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"(%|℃|度|年|个月|月|天|小时|分钟|公斤|斤|克|米|厘米|毫米|MPa|kPa|GB|MB|TB|块|万|亿|岁|次|人|倍)?"
)
PUNCT_RE = re.compile(r"[\s，。！？、,.!?：:；;\"'“”‘’（）()《》【】\[\]…—\-]+")
LEAD_RE = re.compile(
    r"^(请问|我想问一下|我想问|想问一下|想问|请|帮我|能不能|可不可以|怎么|如何|"
    r"为什么|为啥|该不该|要不要|是不是|有没有|可以|能否|应该|我想知道|我想了解)+"
)
LEAD_FILLER_RE = re.compile(
    r"^(我|你|他|她|我们|你们|他们|大家|有人)(最近|一直|总是|暂时|其实|真的|到底|究竟)?"
)
MID_QUESTION_RE = re.compile(r"(怎么|如何|怎样|为什么|为啥)")
TRAILING_RE = re.compile(
    r"(怎么回答|如何回答|怎么回复|如何回复|怎么回|如何回|怎么办|怎么选|"
    r"合适吗|好不好|行不行|可以吗|值不值|呢|吗|啊|吧|呀|嘛)$"
)

TOPIC_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("催婚", ("催婚", "逼婚", "相亲", "结婚", "对象", "亲戚", "年夜饭", "彩礼", "婚礼")),
    ("职场", ("加班", "老板", "领导", "同事", "跳槽", "离职", "面试", "加薪", "职场", "上班", "裁员")),
    ("情感", ("分手", "恋爱", "异地恋", "喜欢", "表白", "伴侣", "男朋友", "女朋友", "前任", "暧昧", "好人卡")),
    ("身体", ("失眠", "减肥", "减脂", "体重", "健康", "健身", "跑步", "膝盖", "熬夜", "免疫力", "喝水")),
    ("学习", ("考研", "学习", "考试", "单词", "论文", "笔记", "拖延", "背书", "读书", "英语")),
    ("生活", ("租房", "房租", "买房", "猫", "狗", "宠物", "室友", "房间", "做饭", "手机")),
    ("技术", ("python", "代码", "数据库", "缓存", "线程", "内存", "docker", "git", "短链接", "索引", "限流", "系统设计")),
    ("社会", ("幸福", "意义", "不确定性", "努力", "父母", "朋友", "人生", "社会", "工作")),
)

EMOTION_WORDS: dict[str, tuple[str, ...]] = {
    "anxious": ("焦虑", "担心", "害怕", "慌", "压力", "失眠", "睡不着", "内耗"),
    "angry": ("气死", "烦", "讨厌", "受够", "凭什么", "无语", "恶心"),
    "sad": ("难过", "失落", "分手", "哭", "孤独", "崩溃", "委屈"),
    "tired": ("累", "疲惫", "加班", "摆烂", "不想动"),
}


def _detect_topic_key(raw: str) -> str | None:
    low = raw.lower()
    best: str | None = None
    best_hits = 0
    for key, words in TOPIC_HINTS:
        hits = sum(1 for word in words if word.lower() in low)
        if hits > best_hits:
            best, best_hits = key, hits
    return best if best_hits else None


def _clean_topic(raw: str) -> str:
    text = PUNCT_RE.sub("", raw)
    text = LEAD_RE.sub("", text)
    text = LEAD_FILLER_RE.sub("", text)
    text = TRAILING_RE.sub("", text)
    text = MID_QUESTION_RE.sub("", text)
    text = text.strip()
    return text[:18]


def _extract_entities(raw: str) -> list[str]:
    hits: list[str] = []
    low = raw.lower()
    # Longest-first so "抗压强度" wins over "强度".
    for term in sorted(TERM_TO_DOMAIN, key=len, reverse=True):
        if term.lower() in low and term not in hits:
            hits.append(term)
    # Quoted phrases are almost always the thing the user cares about.
    for quoted in re.findall(r"[「『“\"]([^」』”\"]{1,20})[」』”\"]", raw):
        if quoted not in hits:
            hits.append(quoted)
    return hits[:8]


def _extract_numbers(raw: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2) or "") for m in NUMBER_RE.finditer(raw)][:8]


def _question_type(raw: str) -> str:
    if re.search(r"怎么|如何|怎样|咋", raw):
        return "how"
    if re.search(r"为什么|为啥|原因", raw):
        return "why"
    if re.search(r"该不该|要不要|能不能|可不可以|值不值得|是否", raw):
        return "should"
    if re.search(r"是什么|什么是|什么意思|定义", raw):
        return "what"
    if re.search(r"推荐|选哪个|哪个好|求", raw):
        return "recommend"
    return "statement"


def _emotion(raw: str) -> str:
    scores = {name: sum(1 for word in words if word in raw) for name, words in EMOTION_WORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"


def parse(raw: str) -> SceneCard:
    raw = (raw or "").strip()
    topic_key = _detect_topic_key(raw)
    topic = _clean_topic(raw) or topic_key or raw[:22]

    domain_scores: dict[str, int] = {}
    low = raw.lower()
    for term, key in TERM_TO_DOMAIN.items():
        if term.lower() in low:
            domain_scores[key] = domain_scores.get(key, 0) + len(term)

    primary = max(domain_scores, key=domain_scores.get) if domain_scores else None

    return SceneCard(
        raw=raw,
        topic=topic,
        topic_key=topic_key,
        entities=_extract_entities(raw),
        numbers=_extract_numbers(raw),
        domain_scores=domain_scores,
        primary_domain=primary,
        question_type=_question_type(raw),
        emotion=_emotion(raw),
    )
