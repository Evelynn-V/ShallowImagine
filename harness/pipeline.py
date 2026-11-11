"""The eight-node shallow pipeline."""

from __future__ import annotations

import random

from .backends import Backend, TemplateBackend
from .confidence import add_conclusion, register_lock
from .domains import DOMAINS
from .guard import assess
from .metrics import score_answer
from .misread import choose_domain
from .models import Result
from .operators import assemble, build_claims
from .parse import parse
from .persona import apply_persona, get_persona

ABSURD_DOMAINS: tuple[str, ...] = ("civil", "cooking", "astronomy", "printing")


class ShallowImagion:
    """A deliberately wrong agent.

    The pipeline is deterministic for a given ``(question, seed)`` pair, which
    makes it usable as a data generator as well as a toy.
    """

    def __init__(
        self,
        backend: Backend | None = None,
        persona: str = "default",
        seed: int = 42,
        mode: str = "harness",
    ) -> None:
        if mode not in ("harness", "standalone"):
            raise ValueError("mode must be 'harness' or 'standalone'")
        self.backend = backend or TemplateBackend()
        self.persona = persona
        self.seed = seed
        self.mode = mode

    def generate(
        self,
        text: str,
        persona: str | None = None,
        seed: int | None = None,
    ) -> Result:
        rng = random.Random(self.seed if seed is None else seed)
        scene = parse(text)

        guard = assess(scene)
        scene.guarded = guard.guarded
        scene.guard_groups = guard.groups
        persona_obj = get_persona(persona or self.persona)

        # A fine-tuned model can answer directly. Guarded inputs never take this
        # path: they stay inside the deterministic, detail-free harness.
        if self.mode == "standalone" and not guard.guarded and self.backend.standalone:
            try:
                direct = self.backend.answer(text, persona=persona_obj.name)
                return Result(
                    direct,
                    {
                        "topic": scene.topic,
                        "topic_key": scene.topic_key,
                        "primary_domain": scene.primary_domain,
                        "target_domain": None,
                        "target_domain_name": None,
                        "shared_property": None,
                        "operators": [],
                        "guarded": False,
                        "guard_groups": [],
                        "backend": self.backend.name,
                        "backend_error": None,
                        "persona": persona_obj.key,
                        "mode": "standalone",
                        "metrics": score_answer(text, direct),
                    },
                )
            except Exception:
                pass  # fall back to the deterministic path

        domain, shared = choose_domain(scene, rng)
        if guard.guarded:
            domain = DOMAINS[rng.choice(ABSURD_DOMAINS)]
            shared = "纯荒诞模式：保留结构，去掉可执行细节"

        claims = build_claims(scene, domain, rng, guarded=guard.guarded)
        draft = assemble(claims, scene, domain, rng)
        draft = register_lock(draft, rng)
        if not guard.guarded:
            draft = add_conclusion(draft, scene, domain, rng)

        backend = TemplateBackend() if guard.guarded else self.backend
        backend_error: str | None = None
        try:
            draft = backend.polish(draft, scene, domain)
        except Exception as exc:  # a dead local server should not kill the demo
            backend_error = f"{type(exc).__name__}: {exc}"
            backend = TemplateBackend()

        final = apply_persona(draft, persona_obj, scene, rng)
        metrics = score_answer(text, final)

        meta = {
            "topic": scene.topic,
            "topic_key": scene.topic_key,
            "primary_domain": scene.primary_domain,
            "target_domain": domain.key,
            "target_domain_name": domain.name,
            "shared_property": shared,
            "operators": [claim.operator for claim in claims],
            "guarded": guard.guarded,
            "guard_groups": guard.groups,
            "backend": backend.name,
            "backend_error": backend_error,
            "persona": persona_obj.key,
            "mode": "harness",
            "metrics": metrics,
        }
        return Result(final, meta)
