---
layout: ../../layouts/Base.astro
title: Quantization, explained
description: What Q4_K_M, Q8_0, QAT, MXFP4 and the other labels mean, and how they change size, speed and quality.
---
# Quantization, explained

A model is a very large pile of numbers called weights. Quantization stores each one with fewer bits, so the file is smaller and the model fits in less memory. Less precision can cost some quality.

## Reading the labels

| Label | What it means |
|---|---|
| **Q4, Q8** | Roughly 4 or 8 bits stored per weight (a little more in practice, because of scales) |
| **K** | A "K-quant": weights are stored in small blocks, and each block carries its own scale. This preserves quality much better than the older simple formats |
| **_S, _M, _L** | Small, medium or large *mix*: which sensitive tensors keep extra precision. `_M` is the usual default |
| **Q4_0, Q8_0** | The older, simpler formats, one scale per block |
| **QAT** | Quantization-aware training: the model was trained or fine-tuned knowing it would be squeezed to 4 bits, so it loses less than a model converted afterwards |
| **IQ3_XS, IQ2...** | "i-quants" use an importance matrix to decide where to spend bits. Smaller and lossier, mostly for squeezing a big model into a small card |
| **MXFP4** | A 4-bit floating-point format with a shared exponent per small block. `gpt-oss` is released in it natively |
| **FP16, BF16** | The full-precision originals, about 16 bits per weight |

## What it does to size, speed and quality

- **Size** is roughly parameters times bits. In our tests the same 12B model is 8.0 GB at Q4_K_M and 12.8 GB at Q8_0.
- **Speed** on a GPU is mostly limited by how many bytes must be read for each token, so fewer bits is faster, until the model no longer fits. Our 8-bit Gemma spilled out of a 12 GB card and ran about four times slower than the 4-bit build.
- **Quality**: 8-bit is usually very close to the original, 4-bit K-quants lose a little, and below 4 bits quality falls faster. How much depends on the model. In our small tests the 8-bit Gemma was not clearly better than the 4-bit one.

For a 12 GB card the practical rule is to take the largest model whose 4-bit build, plus its context cache, still fits in VRAM.

## On a Mac: MLX and GGUF

Apple's MLX has its own 4-bit and 8-bit formats, which are not identical to GGUF's K-quants, so equal "bits" does not mean equal quality. Comparing the two is part of the Apple silicon tests.
