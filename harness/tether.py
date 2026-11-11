"""The tether.

Before we corrupt anything, we produce a short, plausible, correct-ish anchor.
This is what keeps the final answer from drifting into random noise: the
corruption is applied *to* this anchor, so the topic and the argument shape
survive.
"""

from __future__ import annotations

import random

from .models import SceneCard

TOPIC_ANCHORS: dict[str, tuple[str, ...]] = {
    "催婚": (
        "这件事的核心不是说服，而是边界管理：你只需要重复同一句话，并控制解释的长度。",
        "亲戚的追问往往是在确认你的生活是否符合他们的风险模型，而不是真的想听理由。",
        "你不需要赢下这场对话，只需要让它结束，并且明年还能用同一套话术。",
    ),
    "职场": (
        "先把口头承诺变成可追踪的记录，再谈立场；很多冲突不是因为分歧，而是因为信息不对称。",
        "判断一份工作值不值得待，看三件事：成长斜率、现金流安全边际、以及你能否拒绝不合理要求。",
        "加班本身不是问题，不可预期、不可拒绝、不可积累的加班才是问题。",
    ),
    "情感": (
        "看一个人，不要看他怎么说，看他在冲突、疲惫和利益受损时怎么做。",
        "关系里的很多痛苦来自「希望对方猜中」，而不是来自对方不爱你。",
        "体面结束一段关系的关键是：把决定说清楚，把解释留短，把联系断开。",
    ),
    "身体": (
        "先别追求最优方案，先把睡眠、饮食和活动量这三个底变量稳住。",
        "身体问题通常需要专业评估；在信息不足时，最危险的是过度自信的自我诊断。",
        "任何需要长期坚持的改变，都要先降低启动成本，而不是提高意志力。",
    ),
    "学习": (
        "真正有效的学习是主动回忆和间隔重复，而不是把材料再读一遍。",
        "拖延往往不是时间管理问题，而是对任务模糊和失败的恐惧。",
        "把目标拆到今天能完成的最小动作，比制定一个完美计划更有用。",
    ),
    "生活": (
        "先改环境，再改习惯；把诱因移走，比靠意志力抵抗有效得多。",
        "生活里的很多摩擦来自默认设置，而不是来自你不够自律。",
        "一个人住的核心是降低决策次数：固定几套菜单、几条路线、几个收纳位置。",
    ),
    "技术": (
        "先测量，再优化；没有基线的性能改造通常只是换了一种慢法。",
        "优先选择最简单、最容易观测的方案，复杂方案应该由数据逼出来。",
        "大多数系统问题不是算法问题，而是边界、状态和失败路径没有定义清楚。",
    ),
    "社会": (
        "这类问题通常没有唯一答案，只有和你当前约束、价值观匹配的答案。",
        "先区分「别人期待你怎样」和「你自己愿意承担什么代价」。",
        "面对不确定性，能做的是提高可选性，而不是假装能预测结果。",
    ),
}

GENERIC_ANCHORS: tuple[str, ...] = (
    "关于「{topic}」，先把问题拆成三个可观测的变量：频率、强度，以及两者之间的滞后。",
    "「{topic}」很少是单点故障，更像是多个环节的累积误差。",
    "如果只能改一个变量，优先改杠杆最大的那个，因为它对结果的影响通常是非线性的。",
    "先区分事实和解释：关于「{topic}」，你目前掌握的事实可能比你以为的少。",
    "这类问题通常没有最优解，只有和你当前约束匹配的解。",
)


def anchor(scene: SceneCard, rng: random.Random) -> str:
    parts: list[str] = []
    if scene.topic_key and scene.topic_key in TOPIC_ANCHORS:
        parts.append(rng.choice(TOPIC_ANCHORS[scene.topic_key]))
    else:
        parts.append(rng.choice(GENERIC_ANCHORS).format(topic=scene.topic))

    remaining = [line for line in GENERIC_ANCHORS if "{topic}" in line]
    parts.append(rng.choice(remaining).format(topic=scene.topic))
    return " ".join(parts)
