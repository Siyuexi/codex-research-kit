# Available Skills for research-workflow

This file is the **whitelist of skills that research-workflow may invoke or recommend** during a research project. It exists because the global skill registry contains many domain-specific items whose relevance to a given research project varies; this curated list keeps the routing in research-workflow SKILL.md Section 6 honest.

When you spot that a different skill in `~/.codex/skills/` would help and isn't listed here, **suggest adding it** rather than silently using it. The user maintains the whitelist.

---

## Sub-skills (always relevant, part of the research-workflow family)

| Skill | Purpose | Invoked by |
|---|---|---|
| `research-survey` | Survey a sub-topic (sub-area sweep, not single-paper intake) | research-workflow Workflow E' |
| `research-cowork` | Execute queued code TODOs via parallel codex/subagent workers + GitHub PRs | research-workflow Workflow G |
| `research-review` | Key-checkpoint parallel independent review (codex + Codex, four dimensions) | research-workflow Workflow H |

These three are **first-class citizens** of the research-workflow framework. They share the brief-input-contract pattern, log into the same `log/entries/` timeline, and inherit the research-workflow constitution.

---

## Research-stage skills (relevance depends on project phase)

| Skill | Use at | Notes |
|---|---|---|
| `brainstorming-research-ideas` | Early ideation, pivoting | Before proposal.md stabilizes |
| `creative-thinking-for-research` | When stuck, need a creative leap | Cognitive-science-grounded frameworks |
| `first-principles` | When repeated debates suggest unclear roots | Often triggered by research-review coherence findings |
| `20-ml-paper-writing` (a.k.a. `ml-paper-writing`) | Drafting / refining the paper | Owns `doc/` writing discipline + citation verification |
| `codex-memory` | Cross-session continuity | Recall past sessions, search prior discussions |

---

## Technical skills (relevance depends on the project's substrate)

The research-workflow framework is technology-agnostic; these skills appear here because they are commonly invoked from inside a research-workflow project's `src/`. Use only those that match the project's actual stack.

### RL / post-training
- `verl`, `openrlhf`, `trl-fine-tuning`, `grpo-rl-training`, `slime`, `miles`, `torchforge`

### Distributed training scaffolding
- `accelerate`, `pytorch-fsdp2`, `megatron-core`, `pytorch-lightning`, `deepspeed`, `torchtitan`

### Inference / serving
- `vllm`, `sglang`, `tensorrt-llm`, `llama-cpp`

### Evaluation
- `lm-evaluation-harness`, `bigcode-evaluation-harness`, `nemo-evaluator`

### Experiment tracking / observability
- `weights-and-biases`, `mlflow`, `tensorboard`, `langsmith`, `phoenix`

### Quantization / efficiency
- `awq`, `gptq`, `bitsandbytes`, `hqq`, `gguf`, `unsloth`, `peft`, `model-pruning`, `flash-attention`, `speculative-decoding`, `model-merging`

### Fine-tuning frameworks
- `llama-factory`, `axolotl`, `litgpt`, `nanogpt`, `simpo`, `knowledge-distillation`

### Data / RAG
- `langchain`, `llamaindex`, `dspy`, `crewai`, `chroma`, `faiss`, `pinecone`, `qdrant`, `sentence-transformers`, `nemo-curator`, `ray-data`

### Multimodal
- `clip`, `blip-2`, `llava`, `segment-anything`, `stable-diffusion`, `whisper`, `audiocraft`

### Safety / guardrails
- `nemo-guardrails`, `llamaguard`, `prompt-guard`, `constitutional-ai`

### Interpretability
- `transformer-lens`, `nnsight`, `pyvene`, `saelens`

### Infrastructure / orchestration
- `ray-train`, `skypilot`, `lambda-labs`, `modal`

### Long-context / alternative architectures
- `long-context`, `mamba`, `rwkv`, `moe-training`

### Structured outputs / tokenization
- `instructor`, `outlines`, `guidance`, `huggingface-tokenizers`, `sentencepiece`

### Schematic / paper figure (always relevant when writing `doc/`)
- Drawing schematic figures: direct LaTeX/TikZ in `doc/figures/` (standalone, no skill required)
- Post-research talk slides: `document-skills:pptx` (only for `talk.pptx`, never for paper figures)

---

## How to maintain this list

- **Adding a skill**: when a new `~/.codex/skills/<name>/` is installed and is relevant to research work, add a row above in the appropriate section. Keep one-line descriptions.
- **Removing a skill**: skills uninstalled from `~/.codex/skills/` should be removed here too. Do not silently keep dead pointers.
- **Reorganizing**: if a section grows past ~8 entries, split it. If a section shrinks to 1, merge it into a neighbor.
- **Sub-skill changes**: if a new research-workflow sub-skill is added (a fourth `research-*`), add it to the top table AND update research-workflow SKILL.md Section 6 routing table AND add a new Workflow to Section 3.

This file is intentionally not exhaustive about what each skill does — that's in each skill's own SKILL.md. This file's job is to answer "which skills are appropriate at which point in a research project".
