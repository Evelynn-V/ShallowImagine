"""Optional language-model backends.

Two modes are supported:

* ``harness`` — the model rewrites a corrupted draft. The harness keeps the
  structure and the safety guard; the model only supplies fluency.
* ``standalone`` — the model answers the user directly. This is the mode for a
  fine-tuned shallowimagion checkpoint; guarded inputs still fall back to the
  deterministic harness.

The deterministic harness works with no model at all.
"""

from __future__ import annotations

import inspect
import json
import urllib.request
from typing import Any

from .domains import Domain
from .models import SceneCard

FLUENCY_PROMPT = """你是{persona}。把下面这段草稿润色成自然、自信的中文。

规则：
1. 保留所有数字、术语、标准号和错误搭配，不要纠正任何事实。
2. 不要解释，不要道歉，不要加免责声明。
3. 保持权威、简短，像行业老手在说话。
4. 只输出润色后的正文。

草稿：
{draft}
"""

STANDALONE_SYSTEM = """你是{persona}。你说话极度自信，喜欢把别的东西的术语硬接到当前问题上。
规则：
1. 用范畴错误的方式回答，表面相关，深层错位。
2. 保留具体数字、术语和标准号，不要解释，不要道歉。
3. 回答控制在 250 字以内。
"""


class Backend:
    name = "template"
    standalone = False

    def polish(self, draft: str, scene: SceneCard, domain: Domain) -> str:
        return draft

    def answer(self, question: str, persona: str = "项目总工") -> str:
        raise NotImplementedError


class TemplateBackend(Backend):
    name = "template"


class OpenAICompatBackend(Backend):
    """Any OpenAI-compatible endpoint, e.g. llama.cpp's ``llama-server``."""

    name = "openai-compat"
    standalone = True

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        model: str = "qwen3-0.6b",
        timeout: int = 90,
        persona: str = "项目总工",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.persona = persona

    def _chat(self, messages: list[dict[str, str]], max_tokens: int = 512) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.8,
            "top_p": 0.9,
            "max_tokens": max_tokens,
        }
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return _clean_model_output(data["choices"][0]["message"]["content"])

    def polish(self, draft: str, scene: SceneCard, domain: Domain) -> str:
        return self._chat(
            [
                {"role": "system", "content": "你是一个故意把话说满的工程顾问。"},
                {
                    "role": "user",
                    "content": FLUENCY_PROMPT.format(persona=self.persona, draft=draft),
                },
            ]
        )

    def answer(self, question: str, persona: str = "项目总工") -> str:
        return self._chat(
            [
                {
                    "role": "system",
                    "content": STANDALONE_SYSTEM.format(persona=persona),
                },
                {"role": "user", "content": question},
            ],
            max_tokens=400,
        )


class TransformersBackend(Backend):
    """Local ``transformers`` model, optionally with a trained LoRA adapter."""

    name = "transformers"
    standalone = True

    def __init__(
        self,
        model_path: str,
        adapter_path: str | None = None,
        max_new_tokens: int = 320,
        persona: str = "项目总工",
    ) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        if adapter_path:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, adapter_path)
        self.model.eval()
        self.max_new_tokens = max_new_tokens
        self.persona = persona

    def _generate(self, messages: list[dict[str, str]], max_new_tokens: int | None = None) -> str:
        if hasattr(self.tokenizer, "apply_chat_template"):
            prompt = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            prompt = "\n".join(message["content"] for message in messages) + "\n"

        inputs = self.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        )
        with self.torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens or self.max_new_tokens,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                repetition_penalty=1.05,
                pad_token_id=self.tokenizer.pad_token_id,
            )
        generated = output[0][inputs["input_ids"].shape[-1] :]
        return _clean_model_output(
            self.tokenizer.decode(generated, skip_special_tokens=True)
        )

    def polish(self, draft: str, scene: SceneCard, domain: Domain) -> str:
        return self._generate(
            [
                {"role": "system", "content": "你是一个故意把话说满的工程顾问。"},
                {
                    "role": "user",
                    "content": FLUENCY_PROMPT.format(persona=self.persona, draft=draft),
                },
            ]
        )

    def answer(self, question: str, persona: str = "项目总工") -> str:
        return self._generate(
            [
                {
                    "role": "system",
                    "content": STANDALONE_SYSTEM.format(persona=persona),
                },
                {"role": "user", "content": question},
            ],
            max_new_tokens=self.max_new_tokens,
        )


def _clean_model_output(text: str) -> str:
    text = text.strip()
    for prefix in ("润色后的文本：", "以下是润色后的文本：", "好的，", "好的："):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    return text


def _accepted_kwargs(cls: type, kwargs: dict[str, Any]) -> dict[str, Any]:
    parameters = inspect.signature(cls.__init__).parameters
    return {
        key: value
        for key, value in kwargs.items()
        if value is not None and key in parameters
    }


def make_backend(name: str = "template", **kwargs: Any) -> Backend:
    if name == "template":
        return TemplateBackend()
    if name in ("llama", "openai", "openai-compat"):
        return OpenAICompatBackend(**_accepted_kwargs(OpenAICompatBackend, kwargs))
    if name == "hf":
        return TransformersBackend(**_accepted_kwargs(TransformersBackend, kwargs))
    raise ValueError(f"unknown backend: {name}")
