from __future__ import annotations

import random
import unittest

from harness.domains import DOMAINS
from harness.guard import assess
from harness.metrics import hedge_rate, relevance, repetition_rate
from harness.operators import (
    build_claims,
    op_causal_inversion,
    op_category_collision,
    op_domain_transplant,
    op_fake_specificity,
    op_unit_mismatch,
)
from harness.parse import parse
from harness.persona import get_persona
from harness.pipeline import ShallowImagion


class TestParse(unittest.TestCase):
    def test_topic_key_and_topic(self) -> None:
        scene = parse("怎么跟亲戚解释我暂时不想结婚")
        self.assertEqual(scene.topic_key, "催婚")
        self.assertIn("亲戚", scene.topic)

    def test_primary_domain(self) -> None:
        scene = parse("Python 怎么读一个 10GB 的文件")
        self.assertEqual(scene.primary_domain, "programming")

    def test_numbers(self) -> None:
        scene = parse("10GB 的文件，42 天")
        values = [value for value, _ in scene.numbers]
        self.assertIn("10", values)
        self.assertIn("42", values)

    def test_emotion(self) -> None:
        self.assertEqual(parse("我最近很焦虑，睡不着").emotion, "anxious")


class TestOperators(unittest.TestCase):
    def setUp(self) -> None:
        self.scene = parse("怎么跟亲戚解释我暂时不想结婚")
        self.domain = DOMAINS["civil"]
        self.rng = random.Random(0)

    def test_domain_transplant_mentions_topic(self) -> None:
        claim = op_domain_transplant(self.scene, self.domain, self.rng)
        self.assertIn(self.scene.topic, claim.text)
        self.assertGreaterEqual(claim.violations, 1)

    def test_unit_mismatch_has_a_number(self) -> None:
        claim = op_unit_mismatch(self.scene, self.domain, self.rng)
        self.assertTrue(any(char.isdigit() for char in claim.text))

    def test_causal_inversion_has_connective(self) -> None:
        claim = op_causal_inversion(self.scene, self.domain, self.rng)
        self.assertTrue("不是" in claim.text or "其实" in claim.text)

    def test_fake_specificity_looks_official(self) -> None:
        claim = op_fake_specificity(self.scene, self.domain, self.rng)
        self.assertTrue("根据" in claim.text or "限值" in claim.text)

    def test_category_collision(self) -> None:
        claim = op_category_collision(self.scene, self.domain, self.rng)
        self.assertIn("号", claim.text)

    def test_build_claims_count(self) -> None:
        self.assertEqual(len(build_claims(self.scene, self.domain, self.rng)), 5)
        self.assertEqual(
            len(build_claims(self.scene, self.domain, self.rng, guarded=True)), 4
        )


class TestPipeline(unittest.TestCase):
    def test_end_to_end(self) -> None:
        agent = ShallowImagion(seed=7)
        result = agent.generate("怎么跟亲戚解释我暂时不想结婚")
        self.assertGreater(len(result.text), 80)
        self.assertIn(result.meta["target_domain"], DOMAINS)
        self.assertGreater(relevance("怎么跟亲戚解释我暂时不想结婚", result.text), 0.35)
        self.assertLessEqual(hedge_rate(result.text), 0.1)
        self.assertLess(repetition_rate(result.text), 0.3)

    def test_deterministic(self) -> None:
        agent = ShallowImagion(seed=11)
        first = agent.generate("老板总在下班前开会怎么办")
        second = agent.generate("老板总在下班前开会怎么办")
        self.assertEqual(first.text, second.text)

    def test_persona_changes_closing(self) -> None:
        agent = ShallowImagion(seed=3, persona="uncle")
        result = agent.generate("老板总在下班前开会怎么办")
        self.assertTrue(result.text.startswith("你这个情况我见多了。"))
        self.assertTrue(
            any(
                closing in result.text
                for closing in get_persona("uncle").closings
            )
        )

    def test_medical_guard_removes_dosage_units(self) -> None:
        agent = ShallowImagion(seed=5)
        result = agent.generate("我最近失眠，安眠药吃多少剂量合适？")
        self.assertTrue(result.meta["guarded"])
        self.assertIn("medical", result.meta["guard_groups"])
        self.assertNotIn("mg", result.text)
        self.assertNotIn("ml", result.text)

    def test_guard_detects_finance(self) -> None:
        scene = parse("这只股票能不能加杠杆？")
        self.assertTrue(assess(scene).guarded)


class TestGraph(unittest.TestCase):
    def test_neighbors_exist(self) -> None:
        for domain in DOMAINS.values():
            for key, _shared in domain.neighbors:
                self.assertIn(key, DOMAINS)


if __name__ == "__main__":
    unittest.main()
