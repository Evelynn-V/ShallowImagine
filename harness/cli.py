from __future__ import annotations

import argparse
import json
import sys

from .backends import make_backend
from .pipeline import ShallowImagion
from .persona import PERSONAS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shallowimagion",
        description="A deliberately wrong little agent. Thinks shallow, speaks full.",
    )
    parser.add_argument("question", nargs="*", help="the question to misunderstand")
    parser.add_argument(
        "--persona",
        default="default",
        choices=sorted(PERSONAS),
        help="who delivers the nonsense",
    )
    parser.add_argument("--seed", type=int, default=42, help="reproducibility seed")
    parser.add_argument(
        "--backend",
        default="template",
        choices=("template", "llama", "hf"),
        help="template is dependency-free; llama needs a local OpenAI-compatible server",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8080/v1",
        help="OpenAI-compatible endpoint for --backend llama",
    )
    parser.add_argument("--model", default="qwen3-0.6b", help="model name for --backend llama")
    parser.add_argument("--model-path", default=None, help="local model path for --backend hf")
    parser.add_argument("--adapter", default=None, help="LoRA adapter path for --backend hf")
    parser.add_argument(
        "--mode",
        default="harness",
        choices=("harness", "standalone"),
        help="harness: corrupt a draft; standalone: let a fine-tuned model answer directly",
    )
    parser.add_argument("--explain", action="store_true", help="print the wrong-frame trace")
    parser.add_argument("--json", action="store_true", help="emit structured JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    question = " ".join(args.question).strip()
    if not question:
        print('usage: shallowimagion "your question"', file=sys.stderr)
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
    result = agent.generate(question)

    if args.json:
        print(json.dumps({"text": result.text, "meta": result.meta}, ensure_ascii=False, indent=2))
    else:
        print(result.text)
        if args.explain:
            print()
            print(result.explain())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
