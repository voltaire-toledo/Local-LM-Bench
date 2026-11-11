---
layout: ../../layouts/Base.astro
title: Context and the KV cache
description: Why a longer context window costs memory, and why some models pay far less for it than others.
---
# Context and the KV cache

Context is how much text the model can keep in view, counted in tokens. While it reads, the model keeps notes on every token so far, called the key-value cache. The cache grows with every token, and it lives in the same memory as the model. When it no longer fits in VRAM, part of it moves to system memory and everything slows down.

## What decides the cost

For each layer that uses full attention, the cache needs about:

`2 (keys and values) x KV heads x head size x bytes per value`

per token. The number of layers with full attention, the number of KV heads and the numeric precision are what differ between models.

- **Hybrid models** (Qwen 3.5 and 3.6, Granite 4, Nemotron) use full attention in only a few layers, so their cache is tiny. A 64k context costs 0.5 to 2 GB.
- **Sliding-window models** (Gemma 4, Laguna, gpt-oss) let most layers see only the last few hundred or thousand tokens. Their cache stops growing for those layers.
- **Full-attention models** pay for every layer. `qwen3-coder` needs about 96 KB per token, so 128k tokens would need around 13 GB.
- **Cache precision** matters too: an 8-bit cache is about half the size of a 16-bit one.

## Our estimates, 16-bit cache

| Model | 32k | 64k | 128k |
|---|---|---|---|
| nemotron-3.5-lightning | 0.2 GB | 0.5 | 0.9 |
| granite4:32b-a9b-h | 0.5 | 1.1 | 2.1 |
| qwen3.6:35b-a3b | 0.7 | 1.3 | 2.7 |
| gemma4:12b | 1.2 | 1.7 | 2.8 |
| gemma4:26b-a4b | 1.1 | 1.8 | 3.1 |
| qwen3.5:9b | 1.1 | 2.1 | 4.3 |
| laguna-xs-2.1 (layer split assumed) | 1.4 | 2.7 | 5.4 |
| qwen3-coder:30b | 3.2 | 6.4 | 12.9 |

Add about 1 GB for working memory. These are estimates from each model's published architecture, checked against one measurement: `qwen3.5:9b` grew from 6.0 GB at 16k to 9.8 GB at 128k.

## Why the spec pages show a "worst case"

Each model page lists the cache per token assuming every attention layer remembers everything. For sliding-window models that overstates the real cost a lot, so the page says so.
