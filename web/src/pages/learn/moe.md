---
layout: ../../layouts/Base.astro
title: Mixture of experts
description: What mixture-of-experts models are, why they run well on a small GPU, and what the catch is.
---
# Mixture of experts (MoE)

A dense model uses all of its parameters for every token. A mixture-of-experts model splits most of its layers into many small "experts" and uses only a few of them per token. `qwen3.6:35b-a3b` has 256 experts per layer and uses 8, so it holds 35 billion parameters but only computes with about 3 billion at a time. The "a3b" in the name means "3 billion active".

## What that does and does not save

- **It saves compute.** Each token needs the work of a small model, so generation is fast.
- **It does not save memory.** All the experts must still be stored somewhere. A 35B MoE needs the file size of a 35B model.

## Why it works on a 12 GB card

The experts can sit in system memory while the parts every token needs (attention, shared layers and the cache) stay on the GPU. Because only a few experts are read per token, the slower system memory is not much of a bottleneck. Our measurements on an RTX 3060 with 128 GB of RAM:

| Model | Size | Share on CPU | Speed |
|---|---|---|---|
| gemma4:26b-a4b | 15.6 GB | 42 to 48% | 44 to 47 tok/s |
| qwen3.6:35b-a3b | 23.9 GB | 58 to 60% | 42 to 45 tok/s |
| laguna-xs-2.1 | 20.3 GB | 52 to 61% | 51 to 54 tok/s |

A dense model of that size, forced onto the CPU the same way, runs several times slower.

## The catch

- You need enough system memory for the whole model.
- Loading is slower because there is more to read.
- Memory bandwidth between CPU and GPU, and how much of each layer lands where, decide the speed, so results differ between runtimes.
