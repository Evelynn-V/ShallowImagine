"""CPU-friendly LoRA SFT for shallowimagion.

This is intentionally a small, readable training loop rather than a framework
wrapper. It assumes the data was produced by ``model/generate_data.py`` and that
each record has a standard ``messages`` list.

Quick start (after ``uv pip install -e ".[train]"``):

    uv run python model/train_lora.py --dry-run
    uv run python model/train_lora.py --base Qwen/Qwen3-0.6B --max-length 384
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any


def read_jsonl(paths: list[str]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def find_subsequence(sequence: list[int], subsequence: list[int]) -> int:
    if not subsequence:
        return -1
    limit = len(sequence) - len(subsequence) + 1
    for index in range(max(0, limit)):
        if sequence[index : index + len(subsequence)] == subsequence:
            return index
    return -1


def encode_example(tokenizer: Any, messages: list[dict], max_length: int) -> dict | None:
    """Tokenize a chat example and mask the prompt tokens.

    The assistant-only mask is what teaches the model *when* to be wrong. If the
    chat template does not expose assistant masks, we fall back to a string
    search for the assistant content.
    """

    try:
        encoded = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=False,
            return_assistant_tokens_mask=True,
            return_dict=True,
            truncation=True,
            max_length=max_length,
        )
        input_ids = list(encoded["input_ids"])
        masks = encoded.get("assistant_masks") or encoded.get("assistant_tokens_mask")
        if masks is not None and any(int(mask) for mask in masks):
            labels = [
                token if int(mask) else -100
                for token, mask in zip(input_ids, masks)
            ]
            return {
                "input_ids": input_ids,
                "labels": labels,
                "attention_mask": [1] * len(input_ids),
            }
    except Exception:
        pass

    if hasattr(tokenizer, "apply_chat_template"):
        full_text = tokenizer.apply_chat_template(messages, tokenize=False)
        try:
            prompt_text = tokenizer.apply_chat_template(
                messages[:-1], tokenize=False, add_generation_prompt=True
            )
            prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
        except Exception:
            prompt_ids = []
    else:
        full_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        prompt_ids = []

    full_ids = tokenizer(
        full_text,
        add_special_tokens=False,
        truncation=True,
        max_length=max_length,
    )["input_ids"]

    start = -1
    if prompt_ids and full_ids[: len(prompt_ids)] == prompt_ids:
        start = len(prompt_ids)
    else:
        content_ids = tokenizer(
            messages[-1]["content"], add_special_tokens=False
        )["input_ids"]
        start = find_subsequence(full_ids, content_ids)
    if start < 0:
        start = 0

    labels = [-100] * start + list(full_ids[start:])
    if all(label == -100 for label in labels):
        labels = list(full_ids)
    return {
        "input_ids": list(full_ids),
        "labels": labels,
        "attention_mask": [1] * len(full_ids),
    }


def collate(batch: list[dict], pad_token_id: int, torch: Any) -> dict:
    max_length = max(len(item["input_ids"]) for item in batch)
    input_ids = torch.full((len(batch), max_length), pad_token_id, dtype=torch.long)
    attention_mask = torch.zeros((len(batch), max_length), dtype=torch.long)
    labels = torch.full((len(batch), max_length), -100, dtype=torch.long)

    for row, item in enumerate(batch):
        length = len(item["input_ids"])
        input_ids[row, :length] = torch.tensor(item["input_ids"], dtype=torch.long)
        attention_mask[row, :length] = torch.tensor(
            item["attention_mask"], dtype=torch.long
        )
        labels[row, :length] = torch.tensor(item["labels"], dtype=torch.long)

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CPU LoRA SFT for shallowimagion")
    parser.add_argument("--data", nargs="+", default=["data/generated/sft.jsonl"])
    parser.add_argument("--base", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--output", default="outputs/lora-qwen3-0.6b")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument(
        "--target-modules",
        default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj",
    )
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--gradient-checkpointing",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    records = read_jsonl(args.data)
    if args.max_samples:
        records = records[: args.max_samples]
    if not records:
        print(f"no training records found in {args.data}", file=sys.stderr)
        return 2

    if args.dry_run:
        lengths = [
            sum(len(message["content"]) for message in record["messages"])
            for record in records
        ]
        print(f"records: {len(records)}")
        print(
            "characters per example: "
            f"min={min(lengths)} mean={sum(lengths) / len(lengths):.0f} max={max(lengths)}"
        )
        print("dry run only; no model loaded")
        return 0

    try:
        import torch
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        print(
            "training dependencies are missing; run:\n"
            '  uv pip install -e ".[train]"',
            file=sys.stderr,
        )
        print(f"import error: {exc}", file=sys.stderr)
        return 2

    torch.set_num_threads(args.threads or os.cpu_count() or 1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    tokenizer = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        args.base,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
    model.config.use_cache = False
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=[item.strip() for item in args.target_modules.split(",") if item.strip()],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    if args.gradient_checkpointing and hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    model.print_trainable_parameters()

    items: list[dict] = []
    for record in records:
        encoded = encode_example(tokenizer, record["messages"], args.max_length)
        if encoded and len(encoded["input_ids"]) > 1:
            items.append(encoded)
    if not items:
        print("no usable examples after tokenization", file=sys.stderr)
        return 2

    random.Random(args.seed).shuffle(items)
    batches = [
        items[index : index + args.batch_size]
        for index in range(0, len(items), args.batch_size)
    ]

    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.0)
    total_steps = max(1, math.ceil(len(batches) / args.grad_accum) * args.epochs)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps)

    pad_token_id = tokenizer.pad_token_id
    model.train()
    step = 0
    micro_step = 0
    tokens_seen = 0
    started = time.time()
    optimizer.zero_grad(set_to_none=True)

    for epoch in range(args.epochs):
        for batch_items in batches:
            batch = collate(batch_items, pad_token_id, torch)
            outputs = model(**batch)
            loss = outputs.loss / args.grad_accum
            loss.backward()

            tokens_seen += int(batch["attention_mask"].sum().item())
            micro_step += 1

            if micro_step % args.grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                step += 1

                if step % args.log_every == 0 or step == total_steps:
                    elapsed = max(1e-6, time.time() - started)
                    speed = tokens_seen / elapsed
                    remaining = max(0, total_steps - step) * args.grad_accum * args.batch_size
                    eta_minutes = remaining / max(1e-6, speed) / 60
                    print(
                        f"epoch={epoch + 1}/{args.epochs} step={step}/{total_steps} "
                        f"loss={loss.item() * args.grad_accum:.4f} "
                        f"tokens/s={speed:.1f} eta_min={eta_minutes:.1f}"
                    )

    if micro_step % args.grad_accum != 0:
        torch.nn.utils.clip_grad_norm_(trainable, 1.0)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output)
    tokenizer.save_pretrained(output)
    (output / "training_args.json").write_text(
        json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved adapter to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
