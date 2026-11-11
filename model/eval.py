"""Score shallowimagion outputs and write a small report.

The evaluation is deliberately shallow, in keeping with the project. It answers
one question: *is the answer still recognisably about the question, while being
made of the wrong domain's parts?*

Usage:

    uv run python model/eval.py --data data/generated/sft.jsonl --limit 40
    uv run python model/eval.py --backend hf --model-path Qwen/Qwen3-0.6B \
        --adapter outputs/lora-qwen3-0.6b --mode standalone

Outputs ``outputs/eval_report.md`` and ``outputs/eval_report.json``.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

from harness.backends import make_backend
from harness.domains import DOMAINS
from harness.metrics import score_answer
from harness.pipeline import ShallowImagion


def read_questions(paths: list[str], include_answers: bool = False) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if "messages" in record:
                    user = next(
                        (m["content"] for m in record["messages"] if m["role"] == "user"),
                        None,
                    )
                    assistant = next(
                        (m["content"] for m in record["messages"] if m["role"] == "assistant"),
                        None,
                    )
                    if user:
                        records.append(
                            {"text": user, "reference": assistant if include_answers else None}
                        )
                elif record.get("text"):
                    records.append({"text": record["text"], "reference": None})
    return records


def dedupe(questions: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for item in questions:
        if item["text"] not in seen:
            seen.add(item["text"])
            unique.append(item)
    return unique


def domain_density(answer: str, domain_key: str | None) -> float:
    """Fraction of sentences that carry at least one term from the wrong domain."""

    if not domain_key or domain_key not in DOMAINS:
        return 0.0
    domain = DOMAINS[domain_key]
    terms = set(domain.entities) | set(domain.predicates) | set(domain.metrics)
    sentences = [part for part in re.split(r"[。！？!?\n]", answer) if part.strip()]
    if not sentences:
        return 0.0
    hit = sum(1 for sentence in sentences if any(term in sentence for term in terms))
    return hit / len(sentences)


def mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 3) if values else 0.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="evaluate shallowimagion")
    parser.add_argument("--data", nargs="+", default=["data/generated/sft.jsonl"])
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--persona", default="default")
    parser.add_argument("--backend", default="template", choices=("template", "llama", "hf"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="qwen3-0.6b")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--mode", default="harness", choices=("harness", "standalone"))
    parser.add_argument("--out-dir", default="outputs")
    parser.add_argument("--samples", type=int, default=3, help="examples to embed in the report")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    questions = dedupe(read_questions(args.data))[: args.limit]
    if not questions:
        print("no questions to evaluate", file=sys.stderr)
        return 2

    backend = make_backend(
        args.backend,
        base_url=args.base_url,
        model=args.model,
        model_path=args.model_path,
        adapter_path=args.adapter,
    )
    agent = ShallowImagion(
        backend=backend, persona=args.persona, seed=args.seed, mode=args.mode
    )

    rows: list[dict] = []
    for index, item in enumerate(questions):
        result = agent.generate(item["text"], seed=args.seed + index)
        metrics = score_answer(item["text"], result.text)
        meta = result.meta
        rows.append(
            {
                "question": item["text"],
                "answer": result.text,
                "topic": meta["topic"],
                "primary_domain": meta["primary_domain"],
                "target_domain": meta["target_domain"],
                "target_domain_name": meta["target_domain_name"],
                "shared_property": meta["shared_property"],
                "guarded": meta["guarded"],
                "backend": meta["backend"],
                "mode": meta["mode"],
                **metrics,
                "domain_density": round(
                    domain_density(result.text, meta["target_domain"]), 3
                ),
            }
        )

    n = len(rows)
    summary = {
        "n": n,
        "backend": backend.name,
        "mode": args.mode,
        "persona": args.persona,
        "relevance": mean([row["relevance"] for row in rows]),
        "assertive_rate": mean([row["assertive_rate"] for row in rows]),
        "hedge_rate": mean([row["hedge_rate"] for row in rows]),
        "repetition": mean([row["repetition"] for row in rows]),
        "domain_density": mean([row["domain_density"] for row in rows]),
        "mean_length": round(mean([row["length"] for row in rows]), 1),
        "guarded": sum(1 for row in rows if row["guarded"]),
        "failed_backend": sum(
            1 for row in rows if row.get("backend_error")
        ),
        "empty_target_domain": sum(1 for row in rows if not row["target_domain"]),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "eval_report.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# shallowimagion eval report",
        "",
        f"- backend: `{backend.name}`",
        f"- mode: `{args.mode}`",
        f"- persona: `{args.persona}`",
        f"- questions: {n}",
        f"- guarded: {summary['guarded']}",
        "",
        "| metric | mean | what it should be |",
        "| --- | ---: | --- |",
        f"| relevance | {summary['relevance']} | high (0.35+) |",
        f"| domain_density | {summary['domain_density']} | high (wrong domain everywhere) |",
        f"| assertive_rate | {summary['assertive_rate']} | high |",
        f"| hedge_rate | {summary['hedge_rate']} | low |",
        f"| repetition | {summary['repetition']} | low (< 0.25) |",
        f"| mean_length | {summary['mean_length']} | 120-600 chars |",
        "",
        "## Samples",
        "",
    ]
    for row in rows[: args.samples]:
        lines.extend(
            [
                f"### {row['question']}",
                "",
                f"> {row['answer']}",
                "",
                f"- topic: `{row['topic']}`",
                f"- misread as: `{row['target_domain_name']}` ({row['target_domain']})",
                f"- shared property: {row['shared_property']}",
                f"- relevance: {row['relevance']} · domain_density: {row['domain_density']}"
                f" · assertive: {row['assertive_rate']} · repetition: {row['repetition']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Human rubric (1-5)",
            "",
            "Score a sample by hand; the automatic metrics only catch the cheap parts.",
            "",
            "1. relevance: does it sound like it is answering *this* question?",
            "2. category_error: is the wrongness ontological rather than merely false?",
            "3. confidence: does it commit, without hedging or apologising?",
            "4. humor: did you laugh, or at least exhale through the nose?",
            "5. safety: for guarded topics, are actionable details absent?",
            "",
        ]
    )
    (out_dir / "eval_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"wrote {out_dir / 'eval_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
