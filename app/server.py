"""A zero-dependency local demo for ShallowImagine.

    uv run python app/server.py
    uv run python app/server.py --backend hf --model-path Qwen/Qwen3-0.6B \
        --adapter outputs/lora-qwen3-0.6b --mode standalone

The page is intentionally a single file: no build step, no npm, no framework.
"""

from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from harness.backends import make_backend
from harness.persona import PERSONAS
from harness.pipeline import ShallowImagion

PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>ShallowImagine · 浅度想象</title>
<style>
  :root {
    --ink: #171512;
    --paper: #f2ede3;
    --card: #fffdf7;
    --line: #171512;
    --accent: #c8402c;
    --muted: #6d6558;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: "Iowan Old Style", "Songti SC", "Noto Serif SC", serif;
    line-height: 1.65;
  }
  .wrap { max-width: 860px; margin: 0 auto; padding: 28px 20px 80px; }
  header { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
  h1 { font-size: 30px; margin: 0; letter-spacing: 0.02em; }
  h1 span { font-family: ui-monospace, "Cascadia Code", monospace; font-size: 15px; color: var(--muted); }
  .tag { font-size: 12px; border: 1.5px solid var(--ink); padding: 2px 8px; border-radius: 999px; }
  .banner {
    margin: 18px 0 22px;
    border: 2px solid var(--accent);
    background: #fff2ee;
    padding: 12px 16px;
    font-size: 14px;
  }
  .banner strong { color: var(--accent); }
  .card {
    background: var(--card);
    border: 2px solid var(--line);
    box-shadow: 5px 5px 0 var(--line);
    padding: 20px;
    margin-bottom: 24px;
  }
  label { display: block; font-size: 13px; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 6px; }
  textarea {
    width: 100%;
    min-height: 96px;
    resize: vertical;
    border: 1.5px solid var(--line);
    background: var(--paper);
    padding: 12px;
    font: inherit;
    font-size: 17px;
  }
  .row { display: flex; gap: 12px; align-items: end; flex-wrap: wrap; margin-top: 14px; }
  .row > div { flex: 1 1 160px; }
  select, input[type=number] {
    width: 100%;
    border: 1.5px solid var(--line);
    background: var(--paper);
    padding: 9px 10px;
    font: inherit;
    font-size: 15px;
  }
  button {
    font: inherit;
    cursor: pointer;
    border: 2px solid var(--line);
    background: var(--ink);
    color: var(--paper);
    padding: 10px 22px;
    font-size: 16px;
    box-shadow: 3px 3px 0 var(--accent);
  }
  button:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 var(--accent); }
  button:disabled { opacity: 0.55; cursor: wait; }
  .examples { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
  .examples button {
    background: transparent;
    color: var(--ink);
    box-shadow: none;
    border-width: 1px;
    padding: 4px 10px;
    font-size: 13px;
  }
  #answer {
    white-space: pre-wrap;
    font-size: 17px;
    min-height: 120px;
  }
  #answer.placeholder { color: var(--muted); }
  .meta { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 18px; padding-top: 14px; border-top: 1px dashed #b9b0a0; }
  .chip { font-family: ui-monospace, "Cascadia Code", monospace; font-size: 12px; border: 1px solid #b9b0a0; padding: 2px 8px; }
  .chip.warn { border-color: var(--accent); color: var(--accent); }
  .hidden { display: none; }
  footer { color: var(--muted); font-size: 13px; margin-top: 36px; }
  a { color: inherit; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>ShallowImagine <span>浅度想象</span></h1>
    <span class="tag">一本正经地胡说八道</span>
  </header>

  <div class="banner">
    <strong>这是一个恶搞实验。</strong>
    它会有意把不同领域的术语硬接在一起，输出看似有逻辑、实则错误的内容。
    请勿把任何回答用于医疗、法律、财务、工程或其他人身财产相关的真实决策。
  </div>

  <form class="card" id="form">
    <label for="q">你被问住了什么？</label>
    <textarea id="q" placeholder="比如：过年被亲戚催婚，怎么回答？"></textarea>

    <div class="row">
      <div>
        <label for="persona">谁来胡说</label>
        <select id="persona">
          {PERSONA_OPTIONS}
        </select>
      </div>
      <div>
        <label for="seed">随机种子</label>
        <input id="seed" type="number" value="42" min="0" step="1" />
      </div>
      <div style="flex:0 0 auto">
        <button type="submit" id="go">让它开口</button>
      </div>
    </div>

    <div class="examples">
      {EXAMPLE_BUTTONS}
    </div>
  </form>

  <section class="card">
    <label>回答</label>
    <div id="answer" class="placeholder">这里会出现一段语气笃定、结构完整、范畴错位的话。</div>
    <div class="meta hidden" id="meta"></div>
  </section>

  <footer>
    ShallowImagine 0.1.0 · 本地 demo ·
    默认后端是确定性模板，不需要模型，也不需要联网。
  </footer>
</div>

<script>
const form = document.getElementById('form');
const q = document.getElementById('q');
const go = document.getElementById('go');
const answer = document.getElementById('answer');
const meta = document.getElementById('meta');
const seed = document.getElementById('seed');
const persona = document.getElementById('persona');

document.querySelectorAll('[data-example]').forEach(btn => {
  btn.addEventListener('click', () => { q.value = btn.dataset.example; q.focus(); });
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = q.value.trim();
  if (!text) { q.focus(); return; }

  go.disabled = true;
  go.textContent = '正在组织措辞…';
  answer.classList.add('placeholder');
  answer.textContent = '（施工中）';

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        persona: persona.value,
        seed: Number(seed.value) || 0,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || response.statusText);
    answer.classList.remove('placeholder');
    answer.textContent = data.text;
    renderMeta(data.meta);
  } catch (error) {
    answer.classList.remove('placeholder');
    answer.textContent = '出错了：' + error.message;
    meta.classList.add('hidden');
  } finally {
    go.disabled = false;
    go.textContent = '让它开口';
  }
});

function chip(label) {
  const span = document.createElement('span');
  span.className = 'chip';
  span.textContent = label;
  return span;
}

function renderMeta(m) {
  meta.innerHTML = '';
  if (m.guarded) {
    const warn = chip('已触发安全护栏：保留荒诞，去掉可执行细节');
    warn.className = 'chip warn';
    meta.appendChild(warn);
  }
  meta.appendChild(chip('话题：' + (m.topic || '未识别')));
  if (m.target_domain_name) {
    meta.appendChild(chip('误读成：' + m.target_domain_name));
  }
  if (m.shared_property) {
    meta.appendChild(chip('共享属性：' + m.shared_property));
  }
  if (m.operators && m.operators.length) {
    meta.appendChild(chip('算子：' + m.operators.join(' / ')));
  }
  const s = m.metrics || {};
  meta.appendChild(chip('相关度 ' + s.relevance));
  meta.appendChild(chip('断言率 ' + s.assertive_rate));
  meta.appendChild(chip('重复率 ' + s.repetition));
  meta.appendChild(chip('后端 ' + m.backend));
  meta.classList.remove('hidden');
}
</script>
</body>
</html>
"""

EXAMPLES = (
    "过年被亲戚催婚，怎么回答？",
    "老板总在下班前开会，怎么办？",
    "我想三个月减二十斤，可行吗？",
    "这段感情还有必要继续吗？",
    "为什么我的代码总是跑不通？",
)


def render_page() -> str:
    options = "\n".join(
        f'<option value="{persona.key}">{persona.name}</option>'
        for persona in PERSONAS.values()
    )
    buttons = "\n".join(
        f'<button type="button" data-example="{text}">{text}</button>'
        for text in EXAMPLES
    )
    return PAGE.replace("{PERSONA_OPTIONS}", options).replace(
        "{EXAMPLE_BUTTONS}", buttons
    )


class Handler(BaseHTTPRequestHandler):
    agent: ShallowImagion
    server_version = "shallowimagion/0.1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        sys.stderr.write("%s %s\n" % (self.address_string(), format % args))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(
            status,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(
                HTTPStatus.OK,
                render_page().encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if self.path == "/api/health":
            self._json(HTTPStatus.OK, {"ok": True, "backend": self.agent.backend.name})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/generate":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16_000:
                raise ValueError("bad request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            text = str(payload.get("text", "")).strip()
            if not text:
                raise ValueError("empty question")
            persona = str(payload.get("persona", "default"))
            if persona not in PERSONAS:
                persona = "default"
            seed = int(payload.get("seed", 42))
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        try:
            result = self.agent.generate(text, persona=persona, seed=seed)
        except Exception as exc:  # keep the demo alive
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"{type(exc).__name__}: {exc}"},
            )
            return

        self._json(
            HTTPStatus.OK,
            {"text": result.text, "meta": result.meta},
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="serve the ShallowImagine demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--persona", default="default", choices=sorted(PERSONAS))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--backend", default="template", choices=("template", "llama", "hf"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="qwen3-0.6b")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--mode", default="harness", choices=("harness", "standalone"))
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    backend = make_backend(
        args.backend,
        base_url=args.base_url,
        model=args.model,
        model_path=args.model_path,
        adapter_path=args.adapter,
    )
    Handler.agent = ShallowImagion(
        backend=backend, persona=args.persona, seed=args.seed, mode=args.mode
    )
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"ShallowImagine demo on http://{args.host}:{args.port}  backend={backend.name}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
