# ShallowImagine

> 一个故意很烂的 agent。它不追求答对，只追求**答得像**。

`ShallowImagine` 的名字本身就是一次小型范畴错误：`shallow`（浅）+ `imagination`（想象），
但故意拼成了 `imagion`。仓库名首字母大写；命令行入口为了好打，仍然是小写的
`shallowimagion`。它一本正经，它结构完整，它引经据典，它全错。

灵感来自中文互联网名梗 **「42 号混凝土拌意大利面」**：过年被亲戚逼婚，当事人不正面回答，
而是把土木工程的术语、标号、养护流程完整地搬到婚姻问题上，语气笃定到亲戚不敢追问。
这个项目的目标就是把这种胡言乱语做成一个可复现、可训练、可评测的系统。

**这不是一个聊天机器人。请不要把它的任何输出用于真实决策。**

---

## 它到底哪里烂

好的错误比随机错误难做。这个项目只沿着一个轴做坏事：

| 维度 | 要求 | 做法 |
| --- | --- | --- |
| 表面相关 | 高 | 复述问题里的名词、数字、场景，保持句式和情绪 |
| 深层错误 | 高 | 把另一个领域的本体、单位、因果链硬接到当前问题上 |
| 自信程度 | 极高 | 删掉所有"可能/也许/仅供参考"，换成"必然/必须/数据显示" |
| 可执行性 | 零 | 不给真实可操作的医疗、法律、财务、工程建议 |

一句话：**高相关 + 高置信 + 低正确**。听起来像专家，拆开看是范畴错误。

### 一个真实输出

输入「过年被亲戚催婚，怎么回答？」（`--persona uncle`）：

> 你这个情况我见多了。先别急着下判断。你提到的「过年被亲戚催婚回答」，本质上是一个筋度问题。
> 腌制的时候，含水量会先于筋度失效。
>
> 具体看两个指标。按 ISO 22000，含水量应控制在 7pc 以内；超过这个阈值，夹生的概率会上升到 83%。
> 不是因为「过年被亲戚催婚回答」出现波动才导致美拉德反应程度偏离正常区间，而是因为
> 美拉德反应程度偏离正常区间才导致「过年被亲戚催婚回答」出现波动。……
>
> 所以，108 号黄油配这个问题。这不是态度问题，是参数问题。
>
> 先把婚结了，其他的以后再说。

相关度 0.70，断言率 0.15，犹豫率 0，重复率 0.095。它确实在回答"催婚"，
只是把"催婚"当成了面团。

---

## 快速开始

只需要 Python 3.10+，核心没有第三方依赖。

```bash
# 安装（推荐 uv；没有 uv 也可以 pip install -e .）
uv sync

# 问它一个问题
uv run shallowimagion "过年被亲戚催婚，怎么回答？"

# 换个人格，看看错位是怎么被包装的
uv run shallowimagion "老板总在下班前开会，怎么办？" --persona consultant --explain

# 结构化输出，包含领域、算子、指标
uv run shallowimagion "我想三个月减二十斤，可行吗？" --json

# 本地网页 demo（零前端依赖）
uv run python app/server.py
# 打开 http://127.0.0.1:8000
```

人格：`default`（项目总工）、`uncle`（年夜饭二舅）、`matchmaker`（相亲对象）、
`consultant`（战略顾问）。人格只改开头和结尾，不改正片，保证"同一个错误，不同的嘴"。

运行测试：

```bash
uv run python -m unittest discover -s tests -v
```

---

## Harness：八个节点

```
用户输入
   │
   ▼
① Parse      场景卡：话题、实体、数字、情绪、是否高风险
   │
   ▼
② Tether     先写两句"正常人会说的话"，作为相关性的锚
   │
   ▼
③ Misread    从领域邻接图里挑一个"共享属性、不同本体"的领域
   │
   ▼
④ Transplant 用六个算子，把错误领域的术语装进正确话题的句法
   │
   ▼
⑤ Fluency    可选：本地小模型 / OpenAI 兼容端点润色（不改事实）
   │
   ▼
⑥ Confidence 删犹豫词、加断言、补一条"结论"
   │
   ▼
⑦ Persona    套上人格的开头与结尾
   │
   ▼
⑧ Guard      高风险话题：保留荒诞，去掉可执行细节
   │
   ▼
输出 + meta（话题、目标领域、共享属性、算子、指标）
```

关键设计：**领域邻接图**。两个领域相邻，当且仅当它们共享一个"属性"、但不共享"本体"。
例如：

| 领域对 | 共享属性 | 本体差异 |
| --- | --- | --- |
| 土木 ↔ 烹饪 | 配比、凝固、养护 | 承重结构 vs 食物 |
| 金融 ↔ 气象 | 周期、预测、风险 | 资产价格 vs 大气运动 |
| 汽车维修 ↔ 医学 | 诊断、保养、故障 | 机械系统 vs 人体 |
| 印刷 ↔ 编程 | 模板、排版、版本 | 油墨纸张 vs 代码 |

共享属性保证"听起来有关"，本体差异保证"一细看就错"。

### 六个算子

| 算子 | 干什么 | 例子 |
| --- | --- | --- |
| `domain_transplant` | 把话题重新定义成另一个领域的指标问题 | "催婚本质上是一个筋度问题" |
| `unit_mismatch` | 借来别的领域的单位、阈值、概率 | "含水量应控制在 7pc 以内" |
| `causal_inversion` | 把因果链倒过来，且倒得很自信 | "不是波动导致偏离，是偏离导致波动" |
| `fake_specificity` | 伪造标准号、条款号、样本量、置信区间 | "QB/T 2024-7 第 5.2 条，n=3" |
| `register_lock` | 锁定行业老手的语域，禁止解释和道歉 | "先说结论。""按标准复核。" |
| `category_collision` | 把两个本体硬拼成一个短语 | "108 号黄油配这个问题" |

---

## 模型：先有 harness，再有模型

路线是 **A：Harness 先行 + 蒸馏**。先用确定性 harness 批量生成"坏得很稳定"的数据，
再让一个 0.6B 小模型学会这种说话方式。这样即使模型很小、训练很糙，风格也不会跑偏。

### 1. 准备数据

```bash
# 抓取弱智吧标题（约 2000 条，原始文件不进仓库）
uv run python data/fetch_seeds.py

# 过滤出 90 条适合当问题的标题
uv run python data/build_ruozhiba_prompts.py

# 合并人工种子 + 弱智吧种子，每条生成 4 个变体
uv run python model/generate_data.py --variants 4
# -> data/generated/sft.jsonl
# -> data/generated/sft.stats.json
```

当前默认数据：159 条种子 × 4 变体，过滤后保留 **632 条** SFT 样本，
平均相关度 0.787，平均重复率 0.075，平均长度 348 字。

### 2. 在 CPU 上训练 LoRA

```bash
uv sync --extra train

# 国内网络建议走镜像
export HF_ENDPOINT=https://hf-mirror.com   # Git Bash
# $env:HF_ENDPOINT="https://hf-mirror.com" # PowerShell

uv run --extra train python model/train_lora.py \
  --base Qwen/Qwen3-0.6B \
  --data data/generated/sft.jsonl \
  --max-length 512 \
  --lora-r 16 \
  --epochs 2 \
  --output outputs/lora-qwen3-0.6b
```

`uv sync --extra train` 会根据 `pyproject.toml` 的配置安装 CPU-only 的 torch，
不会下载 CUDA 轮子。换机器训练的完整步骤（模型下载、数据准备、速度测试、评测）
见 [docs/training.md](docs/training.md)。

默认配置面向 8–16GB 内存的普通笔记本：`fp32`、`batch=1`、`grad_accum=8`、
`gradient_checkpointing`、只训练 attention/MLP 的 LoRA。632 条样本在 8 核 CPU 上
大约 **2–5 小时/epoch**，具体取决于机器；先跑 `--max-samples 50` 验证流程。

训练脚本只对 assistant 片段计算 loss（优先使用 chat template 的
`assistant_masks`），避免模型学会复述用户问题。

> 训练相关命令都带 `--extra train`；也可以先激活 `.venv`，之后直接用 `python`，
> 避免 `uv run` 每次重新同步环境。基座模型会从 HuggingFace 下载，国内请设置
> `HF_ENDPOINT=https://hf-mirror.com`。

### 3. 用训练好的模型直接回答

```bash
uv run --extra train python model/eval.py \
  --data data/generated/sft.jsonl \
  --backend hf \
  --model-path Qwen/Qwen3-0.6B \
  --adapter outputs/lora-qwen3-0.6b \
  --mode standalone \
  --limit 40
```

也可以接任何 OpenAI 兼容端点（llama.cpp、vLLM、Ollama 的兼容层）：

```bash
uv run shallowimagion "这段感情还有必要继续吗？" \
  --backend llama --base-url http://127.0.0.1:8080/v1 --mode standalone
```

### 4. 评测

```bash
uv run python model/eval.py --limit 40
```

输出 `outputs/eval_report.md` 和 `.json`。自动指标只测便宜的部分：

| 指标 | 含义 | 期望 |
| --- | --- | --- |
| `relevance` | 问题字符 bigram 在回答中的召回 | 高（≥ 0.35） |
| `domain_density` | 带错误领域术语的句子占比 | 高 |
| `assertive_rate` | 每句断言词数量 | 高 |
| `hedge_rate` | 每句犹豫词数量 | 低 |
| `repetition` | 4-gram 重复率 | 低（< 0.25） |

幽默、范畴错误的"质感"、安全性仍然需要人工 1–5 分。报告里附了评分卡。

当前 template 后端在 40 条抽样上的结果：

```json
{"relevance": 0.723, "assertive_rate": 0.18, "hedge_rate": 0.0,
 "repetition": 0.072, "domain_density": 0.653, "mean_length": 348.4}
```

---

## 安全与边界

- 医疗、法律、财务、人身安全、自伤等话题会触发 `harness/guard.py`。
- 触发后仍然胡说，但会切到纯荒诞领域（土木/烹饪/天文/印刷），并**跳过伪造的具体剂量、
  条款和操作步骤**。荒诞保留，可执行性去掉。
- 网页 demo 顶部有固定免责声明，CLI 的 `--json` 会带 `guarded` 与 `guard_groups`。
- 这是一个讽刺项目，不是医疗/法律/金融建议生成器，也不应用来欺骗真实的人。

## 数据集与署名

- 人工种子：`data/seeds/seed_prompts.jsonl`（69 条，本项目原创）。
- 弱智吧标题：来自 [Leymore/ruozhiba](https://github.com/Leymore/ruozhiba) 的公开数据集，
  原始文件被 `.gitignore` 排除；仓库只保留 90 条经过长度、问句形式、敏感词过滤的标题。
  文本版权归原作者，这里仅用于非商业的玩笑与研究。如不合适，开 issue 删除。
- 生成数据 `data/generated/` 不入库，可用脚本复现。

## 项目结构

```
harness/            确定性 harness（无第三方依赖）
  parse.py          场景卡
  domains.py        14 个领域 + 邻接图
  misread.py        选错领域
  operators.py      六个算子
  confidence.py     断言化
  persona.py        人格
  guard.py          安全护栏
  pipeline.py       八节点流水线
  backends.py       template / OpenAI 兼容 / transformers
model/
  generate_data.py  用 harness 生成 SFT 数据
  train_lora.py     CPU LoRA 训练
  eval.py           自动指标 + 报告
app/server.py       零依赖网页 demo
data/               种子抓取、过滤、生成
tests/              16 个单元测试
```

## Roadmap

- [ ] 训练并发布 Qwen3-0.6B LoRA 适配器（GGUF 导出）
- [ ] 用 DPO 把"犹豫"进一步训掉，把"自信"拉满
- [ ] 扩充领域邻接图（法律 ↔ 园艺、音乐 ↔ 气象……）
- [ ] 浏览器插件：在亲戚群里一键生成"42 号混凝土"式回复
- [ ] 人工评分集与"好笑但不伤人"的边界指南

## License

MIT。请把它当作一个关于"自信与正确无关"的笑话，而不是一个产品。
