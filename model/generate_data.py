"""Generate SFT data with the deterministic harness.

Each output record is a chat example:

    {"messages": [{"role": "user", ...}, {"role": "assistant", ...}], "meta": {...}}

The meta block is intentionally kept: it makes it possible to audit which
operator produced which sentence, and to filter the dataset by failure mode.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness.backends import make_backend
from harness.pipeline import ShallowImagion


def read_jsonl(paths: list[str]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def dedupe(records: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for record in records:
        text = (record.get("text") or "").strip()
        if text and text not in seen:
            seen.add(text)
            unique.append(record)
    return unique


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="generate shallowimagion SFT data")
    parser.add_argument(
        "--seeds",
        nargs="+",
        default=["data/seeds/seed_prompts.jsonl"],
        help="one or more JSONL files with a 'text' field",
    )
    parser.add_argument("--out", default="data/generated/sft.jsonl")
    parser.add_argument("--variants", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--persona", default="default")
    parser.add_argument("--backend", default="template", choices=("template", "llama", "hf"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="qwen3-0.6b")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--min-relevance", type=float, default=0.35)
    parser.add_argument("--max-repetition", type=float, default=0.25)
    parser.add_argument("--min-length", type=int, default=120)
    parser.add_argument("--max-length", type=int, default=600)
    parser.add_argument("--include-guarded", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    seeds = dedupe(read_jsonl(args.seeds))
    if args.limit:
        seeds = seeds[: args.limit]
    if not seeds:
        print("no seed prompts found", file=sys.stderr)
        return 2

    backend = make_backend(
        args.backend,
        base_url=args.base_url,
        model=args.model,
        model_path=args.model_path,
        adapter_path=args.adapter,
    )
    agent = ShallowImagion(backend=backend, persona=args.persona, seed=args.seed)

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)

    kept = 0
    skipped = 0
    seen_answers: set[str] = set()
    totals = {"relevance": 0.0, "repetition": 0.0, "length": 0.0}

    with output.open("w", encoding="utf-8") as handle:
        for index, seed_record in enumerate(seeds):
            question = seed_record["text"].strip()
            for variant in range(args.variants):
                result = agent.generate(
                    question, seed=args.seed + index * 1000 + variant
                )
                metrics = result.meta["metrics"]
                answer = result.text.strip()

                if result.meta["guarded"] and not args.include_guarded:
                    skipped += 1
                    continue
                if metrics["relevance"] < args.min_relevance:
                    skipped += 1
                    continue
                if metrics["repetition"] > args.max_repetition:
                    skipped += 1
                    continue
                if not (args.min_length <= len(answer) <= args.max_length):
                    skipped += 1
                    continue
                if answer in seen_answers:
                    skipped += 1
                    continue

                seen_answers.add(answer)
                record = {
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    "meta": result.meta,
                }
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                kept += 1
                totals["relevance"] += metrics["relevance"]
                totals["repetition"] += metrics["repetition"]
                totals["length"] += metrics["length"]

            if (index + 1) % 50 == 0:
                print(f"seeds: {index + 1}/{len(seeds)}  kept: {kept}  skipped: {skipped}")

    stats = {
        "seeds": len(seeds),
        "variants": args.variants,
        "kept": kept,
        "skipped": skipped,
        "mean_relevance": round(totals["relevance"] / kept, 3) if kept else 0.0,
        "mean_repetition": round(totals["repetition"] / kept, 3) if kept else 0.0,
        "mean_length": round(totals["length"] / kept, 1) if kept else 0.0,
    }
    stats_path = output.with_suffix(".stats.json")
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
