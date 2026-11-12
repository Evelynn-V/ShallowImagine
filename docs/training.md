# 在新机器上继续训练

这台旧笔记本上的训练停在 epoch 1、step 10/158，**没有保存 adapter**（checkpoint 只在每个
epoch 结束时写）。换机器后从头开始即可，数据量很小。

## 0. 准备

- Python 3.10+，推荐 [uv](https://docs.astral.sh/uv/)
- 磁盘至少 5GB（基座模型 1.5GB + 环境约 2GB + 输出）
- 内存 8GB 能跑，16GB 更稳
- 能访问 PyPI 和 `download.pytorch.org`；国内下载模型时用 hf-mirror

## 1. 拉代码、装环境

```bash
git clone https://github.com/Evelynn-V/ShallowImagine.git
cd ShallowImagine
uv sync --extra train
```

`pyproject.toml` 已经把 `torch` 指向 CPU-only 的 PyTorch 索引，不会下载几个 GB 的 CUDA 轮子。

如果 `download.pytorch.org` 太慢，也可以手动装：

```bash
uv pip install torch --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match
uv pip install "transformers>=4.51" "peft>=0.14" accelerate jinja2
```

## 2. 准备基座模型

新机器重新下载：

```bash
export HF_ENDPOINT=https://hf-mirror.com

# Windows Git Bash
.venv/Scripts/hf.exe download Qwen/Qwen3-0.6B --local-dir outputs/qwen3-0.6b-base

# Linux / macOS
.venv/bin/hf download Qwen/Qwen3-0.6B --local-dir outputs/qwen3-0.6b-base
```

也可以直接从旧机器拷贝 `outputs/qwen3-0.6b-base/`（约 1.5GB），省一次下载。

## 3. 准备 SFT 数据

两种方式任选：

```bash
# A. 重新生成（几秒钟，不需要模型）
uv run --extra train python model/generate_data.py --variants 4

# B. 从旧机器拷贝 data/generated/sft.jsonl（632 条）
```

`data/generated/` 被 `.gitignore` 排除，所以不在仓库里；脚本可以完整复现。

## 4. 先做速度测试

正式训练前，用 8 条样本测一下新机器的速度：

```bash
uv run --extra train python model/train_lora.py \
  --base outputs/qwen3-0.6b-base \
  --data data/generated/sft.jsonl \
  --max-samples 8 \
  --epochs 1 \
  --max-length 384 \
  --grad-accum 2 \
  --log-every 1 \
  --threads 8 \
  --output outputs/bench-lora
```

看日志里的 `tokens/s` 和每个 step 的耗时。总 step 数是：

```
ceil(632 / 8) × epochs = 79 × epochs
```

用 `每 step 耗时 × 79` 估算每个 epoch 的时间。旧机器（i5-10210U，6 线程）大约是
**3 小时/epoch**；8 核以上的桌面 CPU 预计 1–2 小时/epoch。

## 5. 正式训练

```bash
uv run --extra train python model/train_lora.py \
  --base outputs/qwen3-0.6b-base \
  --data data/generated/sft.jsonl \
  --max-length 512 \
  --batch-size 1 \
  --grad-accum 8 \
  --epochs 2 \
  --lr 1e-4 \
  --lora-r 16 \
  --lora-alpha 32 \
  --threads 8 \
  --log-every 5 \
  --output outputs/lora-qwen3-0.6b
```

- `--threads` 建议设为逻辑核心数减 2，给系统和浏览器留余量。
- 每个 epoch 结束会保存一次 adapter；中途退出会丢失当前 epoch 的进度。
- 想先快速看效果，可以只跑 `--epochs 1`。

## 6. 评测

```bash
uv run --extra train python model/eval.py \
  --data data/generated/sft.jsonl \
  --backend hf \
  --model-path outputs/qwen3-0.6b-base \
  --adapter outputs/lora-qwen3-0.6b \
  --mode standalone \
  --limit 40
```

报告写到 `outputs/eval_report.md`，包含相关度、错误领域密度、断言率、犹豫率、重复率和样例。

## 7. 注意

- 训练脚本目前是 **CPU-only**；有 NVIDIA GPU 的机器也用不上，脚本不会自动 `.to("cuda")`。
- `uv run` 不带 `--extra train` 时可能把训练依赖从环境里清掉。训练期间建议先激活
  `.venv`，之后统一用 `python` 命令：

  ```bash
  source .venv/Scripts/activate   # Windows Git Bash
  source .venv/bin/activate       # Linux / macOS
  ```

- 旧机器上的网页 demo 与代码无关，换机器后按 README 重新启动即可。
