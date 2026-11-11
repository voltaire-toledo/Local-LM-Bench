---
layout: ../layouts/Base.astro
title: FAQ
description: Common questions about how the scores work and why they are built this way.
---
# FAQ

## Why is speed not factored into the overall scores?

Speed is measured and shown in every report, and there is a slider if you want it to count. It carries less weight by default because the biggest variable for anyone reading this is the hardware they choose. The NVIDIA GPU used here was bought in the summer of 2021 for under $300, when my thirteen-year-old daughter wanted to build her own rig. It was the COVID-19 era, and it was winter 2022 before I first looked into ChatGPT. So yes, I am using her leftover hardware. How does that saying go about the cobbler's children and their shoes? Your machine will differ; the quality scores should travel better than the speeds.

## What does the asterisk on a score mean?

The model has not been run on every test you weighted, so its score covers only the tests it has. It sorts below fully tested models.

## Why Ollama?

One runtime, one set of model files and one API makes models comparable. Tool-calling results depend on the runtime as well as the model, so they belong to the pair. Other runtimes (LM Studio, llama.cpp directly, MLX on a Mac) will be measured as their own rows.

## Why only 16k context?

Because the point is to keep the model and its context inside 12 GB of VRAM. The speed runs also test 32k and 64k.

## Why do some models look worse than I expected?

The test sets are small, the checkers are mine and they have had bugs. When I find one I fix it and re-score the stored answers instead of re-running the models. If a result surprises you, the model page lists what was measured and what was not.

## Can I trust the verdicts?

They are my reading of small tests on one machine. Use them to build a shortlist, then test the shortlist on your own work. That is the point of this project.
