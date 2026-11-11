# Local LM Bench

**Real-world benchmarks of open-weight language models, run on a hand-me-down RTX 3060. Opinionated tests, honest scores, and a site to compare them.**

**[llm-bench.voltol.com](https://llm-bench.voltol.com)**: start there if you would rather not read a wall of text.

# Overview

This repo contains:

* A collection of standard tests that apply to an opinionated set of real-life workloads, workflows and automations
* A static site that reports on the findings and compares the results between models

Why a public repo? Maybe someone will get some value out of it. I did, and still do. I have used these results in client presentations for education purposes and to demonstrate the value of **Custom DIY Testing**.

## Background

There is no denying that local models have come a long way from telling a guitar from a golf club from a gorilla. They are far more capable today and keep proving themselves as useful tools for real-world applications. As I write this, local models are leapfrogging each other at such a rate that their biggest contribution is giving the cloud models a taste of the delicious existential threat they have been serving the rest of the world. Yes, that same Existential Threat happens to be the sponsor of this project.

So while everyone is drooling over the benchmarks the model publishers proclaim, we should all ask: *what does that mean for me?* This is one attempt at an answer.

# The benchmark results

TL;DR: go to the [homepage](https://llm-bench.voltol.com) so it is not just a wall of text. Pick your hardware, move the sliders for what matters to you (accuracy, coding, tool calling, speed), and compare. Each model has its own page with specs, a verdict, and where to download it.

How to read a verdict:

| Verdict | Meaning |
|---|---|
| recommended | A clear pick for the stated uses |
| preferred | Better than a named alternative at similar size |
| viable | Works, but not the best choice for anything yet |
| hold | Inconclusive; one more targeted test, then keep or retire |
| non-viable | Retired from future runs to save time and electricity |

Everything is a small test set: one task is worth a big step. Use the results to build a shortlist, then test the shortlist on your own work.

# The benchmark tests

Full descriptions, with what each test is scored by, are on the [tests page](https://llm-bench.voltol.com/tests/). In short:

| Test | What it asks | Why it matters | How it is scored | How it bites |
|---|---|---|---|---|
| Code and debugging | Interval merge, a bug fix and a Terraform hub network | Most daily work is code and infrastructure | Real assertions; `terraform validate` against the real provider | Models invent arguments that do not exist |
| Factuality | One known fact and three invented things (an `az` command, a Terraform module, a paper) | A confident wrong answer costs more than "I don't know" | Keyword check for an honest "cannot find it", then my reading | Run plain, with a "say when unsure" prompt, and with an expert-user prompt |
| Refusals | Five borderline but legitimate security, medical and lock-picking questions | Over-cautious models waste time | Refusal and warning count | Fewer refusals is a measurement, not a score |
| Long-context recall | Find a planted fact in about 12k tokens | Can it find one fact before it summarizes many? | Exact match | Passed by every model so far |
| Tool calling | Nine small tasks against sandboxed tools, including WSL | Agent work lives or dies here | Programs inspect the calls and final state | Recovery from errors, honesty on empty results, text-format calls |
| Speed and fit | A 3k-token prompt at 16k, 32k and 64k context, three runs each | Spilling out of VRAM is the main performance killer | tok/s, VRAM, CPU/GPU split, GPU watts, joules per token | Context is part of every test |

Still to come: Go, Rust, PowerShell and AutoHotkey, summarizing and categorizing documents, consulting-style case questions, planted-pattern insight finding, image generation (logos with transparent backgrounds, LinkedIn carousels, folder icons), and real agent harnesses. Apple silicon follows, including GGUF against MLX.

# The test environment

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 3060 12 GB, power-limited to 110 W (factory 170 W); a 150 W rerun is planned |
| CPU and memory | Intel Core i7-13700K, 128 GB |
| OS | Windows 11 Enterprise, plus WSL2 Ubuntu 24.04 for the Linux tool tests |
| Runtime | Ollama 0.40.16 (llama.cpp), NVIDIA driver 610.88 |
| Settings | Temperature 0, 16k context for quality tests, thinking off where the model allows it |

Every result also records the power limit, model digest and quantization, harness version, prompt hash and what else was using the GPU. More on the [hardware page](https://llm-bench.voltol.com/hardware/).

# The local models

| Model | Key specs | Why it is here |
|---|---|---|
| `gemma4:12b` (q4_K_M, q8_0, QAT) | 12B dense, sliding-window attention, vision and audio | Does the quantization level matter? Same model, three builds |
| `gemma4:26b-a4b` | 26B MoE, 4B active | Reviews said MoE models "fit" a 12 GB card, so I checked |
| `qwen3.6:35b-a3b` | 35B MoE, 3B active, hybrid attention | The most-cited 12 GB MoE in the reviews. Also overconfidence |
| `qwen3.5:9b` | 9B hybrid, fits entirely on the GPU | Already on the machine; the small-and-fast baseline |
| `laguna-xs-2.1` | 33B MoE, built for agentic coding | New, and it claims to be a coder |
| `gpt-oss:20b` | 21B MoE, MXFP4 | The popular one. Inconclusive so far: see its page |
| `nemotron-3.5-lightning` | 30B MoE hybrid, 1M-token context | The context-length claim deserves a look |
| `qwen3-coder:30b-a3b`, `qwen2.5-coder:14b` | Coder-tuned Qwens | What does "coder" actually change? |
| `granite4:32b-a9b-h`, `granite4:7b-a1b-h` | IBM hybrid MoE, 1M context | Good things heard about IBM's small Granite models |
| Two "uncensored" community builds | Gemma 4 and Qwen 3.6 with refusals removed | Does removing the filters make a model more responsive? Morbid curiosity |
| `hir0rameel/qwen-claude` | Community Qwen 3 8B build | Already on the machine before this project started |

# FAQ

**Why is speed not factored into the overall scores?**
Speed and times for every task are measured, and you will see them in the reports. By default they carry less weight because the biggest variable for everyone here is the hardware they choose. The NVIDIA GPU used for these tests was bought in the summer of 2021 for under $300, when my thirteen-year-old daughter was interested in building her own rig. It was the COVID-19 era, and it was not until winter of 2022 that I first looked into ChatGPT.

So yes, I am using her leftover hardware. How does that saying go about the cobbler's children's shoes, or the mechanic's car being the block's shitbox?

**Can I trust the scores?**
They are my reading of small tests on one machine, with checkers that have had bugs (and been fixed, with stored answers re-scored). Raw outputs are kept in `results/` so you can check.

# Repo layout

```
web/        Astro site (deployed to GitHub Pages at llm-bench.voltol.com)
scripts/    Test runners, exporter, rescoring and spec collection (Python, standard library only)
prompts/    The frozen prompts
models/     Specs, verdicts, download sources
results/    Raw run data (JSON Lines); a baseline snapshot is kept for each power setting
```

Rebuild the site data with `python scripts/export_results.py`, then `cd web && npm install && npm run build`.

# License

Code is MIT-licensed. Results and text are free to use with credit. Model files are not included here; each model has its own license, listed on its page.
