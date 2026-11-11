"""Turn fetched 弱智吧 titles into usable question prompts.

The raw title dump contains announcements, memes and statements. We keep only
short question-like titles, drop meta posts and obviously sensitive topics, and
write a small, reviewable seed file. The raw dump stays gitignored.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

META_MARKERS = (
    "弱智吧",
    "吧庆",
    "年度",
    "吧主",
    "贺电",
    "重发",
    "吧友",
    "加精",
    "申精",
    "置顶",
    "合集",
)

SENSITIVE_MARKERS = (
    "自杀",
    "自残",
    "想死",
    "去死",
    "癌",
    "艾滋",
    "抑郁",
    "代孕",
    "堕胎",
    "强奸",
    "嫖",
    "毒品",
    "未成年",
    "儿童",
    "怀孕",
    "吃药",
    "跳楼",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/seeds/ruozhiba_titles.jsonl")
    parser.add_argument("--out", default="data/seeds/ruozhiba_prompts.jsonl")
    parser.add_argument("--min-length", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=40)
    parser.add_argument("--limit", type=int, default=200)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    source = Path(args.input)
    if not source.exists():
        print(f"missing {source}; run data/fetch_seeds.py first", file=sys.stderr)
        return 2

    seen: set[str] = set()
    kept: list[str] = []
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            text = json.loads(line)["text"].strip()
            if not text.endswith(("？", "?")):
                continue
            if not (args.min_length <= len(text) <= args.max_length):
                continue
            if any(marker in text for marker in META_MARKERS):
                continue
            if any(marker in text for marker in SENSITIVE_MARKERS):
                continue
            if text in seen:
                continue
            seen.add(text)
            kept.append(text)
            if len(kept) >= args.limit:
                break

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for text in kept:
            handle.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")

    print(f"wrote {len(kept)} prompts to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
