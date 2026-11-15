---
layout: ../layouts/Base.astro
title: Hardware
description: The machine, the settings and the software the benchmarks run on.
---
# The test environment

Two machines. Quality scores belong to a model file and are measured once; speed, viable context and power belong to a machine and are never mixed across them.

## Windows PC

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 3060, 12 GB (bought summer 2021 for under $300) |
| GPU power limit | 110 W for the first full run (factory default 170 W, adjustable 100 to 187 W). A 150 W rerun of the speed sweep is also published. |
| CPU | Intel Core i7-13700K |
| System memory | 128 GB |
| OS | Windows 11 Enterprise, with WSL2 Ubuntu 24.04 for the Linux tool tests |
| Runtime | Ollama 0.40.16 (llama.cpp underneath), NVIDIA driver 610.88 |
| Terraform | 1.13.5 |

## Settings that matter

- **Temperature 0** and a fixed seed for the speed runs, so answers are as repeatable as the runtime allows.
- **Context 16k** for the quality tests, and 16k, 32k and 64k for the speed runs. Context costs VRAM, and a model that spills into system memory gets much slower, so context is part of every test. See [KV cache](/learn/kv-cache/).
- **Thinking turned off** where the model allows it. Some models ignore the setting, which hurt `gpt-oss:20b` in the first run.
- **Power limit recorded with every run.** Quality does not depend on it; speed does.

## What was recorded for each run

Model digest and quantization, Ollama version, prompt hash, harness version, GPU power limit, GPU memory before loading, other processes using the GPU, power, clocks and temperature during the run, and the CPU/GPU split. Raw outputs are kept and re-scored when a checker improves, so old results are never overwritten.

## MacBook Pro (Apple silicon)

| | |
|---|---|
| Chip | Apple M4 Pro (12-core CPU), 273 GB/s memory bandwidth |
| Memory | 24 GB unified, shared by the GPU, macOS and apps. About 16 GB is available to the GPU by default. |
| OS | macOS 27.2 |
| Runtimes | Ollama 0.40.15 (llama.cpp, Metal) for GGUF files; mlx-lm 0.32 for MLX builds, through a small Ollama-compatible bridge so the same tests run unchanged |
| Power | GPU power from `powermetrics`, which needs administrator rights. Macs have no power limit to set. |

The Mac runs the same GGUF files as the PC (same digests), so their quality scores carry over and only speed and context are measured again. MLX builds are different files and get their own quality scores. Laguna XS 2.1 loaded only after raising the GPU memory limit to 20 GB.

**Separate VRAM versus shared memory.** The PC's 12 GB card spills into 128 GB of system memory, and only the model slows down. On the Mac, everything shares 24 GB, so a large model slows the whole machine. See [what runs well on the Mac](/mac/).
