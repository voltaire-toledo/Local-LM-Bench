---
layout: ../layouts/Base.astro
title: Hardware
description: The machine, the settings and the software the benchmarks run on.
---
# The test environment

| | |
|---|---|
| GPU | NVIDIA GeForce RTX 3060, 12 GB (bought summer 2021 for under $300) |
| GPU power limit | 110 W for the first full run (factory default 170 W, adjustable 100 to 187 W). A 150 W rerun is planned. |
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

## Next

A 150 W rerun, and Apple silicon, comparing GGUF against MLX builds of the same models.
