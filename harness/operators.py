"""The corruption operators.

Each operator is deliberately small and deterministic. It takes a true-ish
surface (the topic, a metric, a standard number) and re-attaches it to the wrong
ontology. Keeping them small is what makes the badness debuggable: when a reply
stops being funny, you can point at the operator that broke it.
"""

from __future__ import annotations

import random

from .domains import DOMAINS, Domain
from .models import Claim, SceneCard


def _pick(rng: random.Random, values: tuple[str, ...] | list[str]) -> str:
    return rng.choice(list(values))


def _ensure_period(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    if text[-1] not in "。！？!?":
        text += "。"
    return text


def _metric_pair(domain: Domain, rng: random.Random) -> tuple[str, str]:
    first = rng.choice(domain.metrics)
    rest = [metric for metric in domain.metrics if metric != first] or list(domain.metrics)
    return first, rng.choice(rest)


def op_domain_transplant(scene: SceneCard, domain: Domain, rng: random.Random) -> Claim:
    concept = rng.choice(domain.metrics)
    pred = rng.choice(domain.predicates)
    metric, metric2 = _metric_pair(domain, rng)
    failure = rng.choice(domain.failures)
    state = rng.choice(domain.states)
    process = rng.choice(domain.predicates)
    std = rng.choice(domain.standards)
    templates = (
        "你提到的「{topic}」，本质上是一个{concept}问题。{pred}的时候，{metric}会先于{metric2}失效。",
        "从{name}的角度看，「{topic}」属于典型的{failure}：表面已经{state}，内部还在{process}。",
        "「{topic}」的关键变量不是态度，而是{metric}。只要{metric}没有达到{std}的要求，后面的{process}都是无效工序。",
        "先把「{topic}」换算成{concept}。在{name}里，{metric}和{metric2}从来不是线性关系，{pred}的先后顺序才是决定性的。",
    )
    text = rng.choice(templates).format(
        topic=scene.topic,
        name=domain.name,
        concept=concept,
        pred=pred,
        metric=metric,
        metric2=metric2,
        failure=failure,
        state=state,
        process=process,
        std=std,
    )
    return Claim(_ensure_period(text), "domain_transplant")


def op_unit_mismatch(scene: SceneCard, domain: Domain, rng: random.Random) -> Claim:
    other = rng.choice([item for item in DOMAINS.values() if item.key != domain.key])
    unit = rng.choice(other.units)
    metric, metric2 = _metric_pair(domain, rng)
    failure = rng.choice(domain.failures)
    std = rng.choice(domain.standards)
    number = rng.choice((3, 7, 14, 28, 42, 60, 108, 360))
    confidence = rng.choice((72, 83, 91, 95, 99))
    templates = (
        "按{std}，{metric}应控制在{n}{unit}以内；超过这个阈值，{failure}的概率会上升到{p}%。",
        "实测数据显示，「{topic}」的{metric}每增加 1{unit}，{metric2}就会下降 {n}%，这个斜率在 {p}% 的样本里都成立。",
    )
    text = rng.choice(templates).format(
        topic=scene.topic,
        std=std,
        metric=metric,
        metric2=metric2,
        failure=failure,
        n=number,
        unit=unit,
        p=confidence,
    )
    return Claim(_ensure_period(text), "unit_mismatch")


def op_causal_inversion(scene: SceneCard, domain: Domain, rng: random.Random) -> Claim:
    metric = rng.choice(domain.metrics)
    pred = rng.choice(domain.predicates)
    a = f"「{scene.topic}」出现波动"
    b = f"{metric}偏离正常区间"
    templates = (
        "不是因为{a}才导致{b}，而是因为{b}才导致{a}。{name}里有个很典型的例子：{pred}之后，{metric}反而上升了。",
        "很多人以为是{a}导致了{b}，其实顺序反了：先有{b}，{a}只是它的下游反应。",
    )
    text = rng.choice(templates).format(
        a=a, b=b, name=domain.name, pred=pred, metric=metric
    )
    return Claim(_ensure_period(text), "causal_inversion")


def op_fake_specificity(scene: SceneCard, domain: Domain, rng: random.Random) -> Claim:
    major = rng.choice((1, 2, 3, 4, 5))
    minor = rng.choice((1, 2, 3, 4, 5, 6, 7, 8))
    metric, _ = _metric_pair(domain, rng)
    std = rng.choice(domain.standards)
    unit = rng.choice(domain.units)
    pred = rng.choice(domain.predicates)
    number = rng.choice((3, 7, 14, 28, 42, 60, 108, 360))
    confidence = rng.choice((72, 83, 91, 95, 99))
    templates = (
        "根据{std}第{major}.{minor}条，「{topic}」的{metric}在{p}%置信区间内服从{name}分布，样本量 n={n}。",
        "{std}对{metric}的限值是 {n}{unit}，但现场抽检的合格率只有 {p}%，说明大部分问题出在{pred}环节。",
    )
    text = rng.choice(templates).format(
        std=std,
        major=major,
        minor=minor,
        topic=scene.topic,
        metric=metric,
        name=domain.name,
        p=confidence,
        n=number,
        unit=unit,
        pred=pred,
    )
    return Claim(_ensure_period(text), "fake_specificity")


def op_category_collision(scene: SceneCard, domain: Domain, rng: random.Random) -> Claim:
    number = rng.choice((7, 14, 28, 42, 108, 360, 720))
    entity = rng.choice(domain.entities)
    topic = scene.topic or (scene.entities[0] if scene.entities else "这个问题")
    templates = (
        "{n}号{entity}拌「{topic}」",
        "{n}号{entity}配「{topic}」",
        "把「{topic}」当成{n}号{entity}来处理",
    )
    text = rng.choice(templates).format(n=number, entity=entity, topic=topic)
    return Claim(_ensure_period(text), "category_collision")


def build_claims(
    scene: SceneCard, domain: Domain, rng: random.Random, guarded: bool = False
) -> list[Claim]:
    claims = [
        op_domain_transplant(scene, domain, rng),
        op_unit_mismatch(scene, domain, rng),
        op_causal_inversion(scene, domain, rng),
    ]
    if not guarded:
        claims.append(op_fake_specificity(scene, domain, rng))
    claims.append(op_category_collision(scene, domain, rng))
    return claims


def vary_topic(text: str, topic: str, rng: random.Random) -> str:
    """Mention the full topic once, then stop repeating it.

    A 0.6B model trained on repetitive data will happily repeat the user's
    sentence verbatim. We remove that failure mode before it reaches the model.
    """

    needle = f"「{topic}」"
    if text.count(needle) <= 1:
        return text
    parts = text.split(needle)
    replacements = ("这件事", "这个问题", "它", "这个情况")
    result = parts[0]
    for index, part in enumerate(parts[1:]):
        if index == 0:
            result += needle + part
        else:
            result += rng.choice(replacements) + part
    return result


def assemble(
    claims: list[Claim], scene: SceneCard, domain: Domain, rng: random.Random
) -> str:
    lead = rng.choice(("先说结论。", "这个问题得拆开看。", "结论不太好听。", "先别急着下判断。"))
    paragraphs = [lead + claims[0].text]

    middle = claims[1:-1]
    if middle:
        paragraphs.append("具体看两个指标。" + "".join(claim.text for claim in middle))

    paragraphs.append("所以，" + claims[-1].text + "这不是态度问题，是参数问题。")
    return vary_topic("\n\n".join(paragraphs), scene.topic, rng)
