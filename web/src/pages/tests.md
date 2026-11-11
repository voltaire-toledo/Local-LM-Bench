---
layout: ../layouts/Base.astro
title: The tests
description: What each benchmark test asks, why it matters, how it is scored and how it tries to break the models.
---
# The tests

Every model gets the same prompts at temperature 0, with a fixed seed and context window, through the same harness. Where a test can be scored by a program (code runs, a template validates, an exact string matches) it is. Where it cannot, an automatic score is only a proxy, and it says so. Each suite is a versioned file in the repo (`suites/`), and every result records the suite version, the power limit and the model's digest.

The question that matters most is **viable context**: not what a model advertises, but how much it can actually use. See [Local or cloud?](/learn/choosing/).

## Viable context (the headline test)

The window is filled with varied, seeded filler at 8k, 16k, 32k, 64k and 128k tokens. Three access codes are hidden at 10, 50 and 90 percent depth, and the model must return all three exactly. A size is **viable** only if all three codes are right, nothing was truncated, generation stays above 15 tok/s and the reply arrives within 180 seconds. Viable context is the largest size that passes; the test stops at the first failure and records why (recall, too slow, low tok/s or truncated). A fourth question, which code has the largest number, is reported but does not decide viability. VRAM, CPU share and GPU power are recorded at every step.

Note the "too slow" cases: a model can answer correctly at 128k and still fail the test because the reply takes four minutes. Whether that matters depends on the job.

## Code

| Test | What it asks | Scored by |
|---|---|---|
| Python and Terraform | Interval merge, a bug fix, and a Terraform hub network with an NSG that allows only 443 | Running assertions; `terraform validate` against the real provider |
| Go, PowerShell, AutoHotkey v2 (and Rust) | The same three jobs in each: merge intervals, parse key=value text, fix a seeded bug | The generated code is compiled or run against a test harness in a throwaway folder; code with unsafe patterns is blocked, not run |

**Why it matters:** this is most of the daily work, and most of the code on this machine is not Python. **How it bites:** invented Terraform arguments, v1/v2 AutoHotkey confusion, PowerShell's array unrolling and Rust's borrow checker. Rust is skipped until a toolchain is installed.

## Documents

- **Categorizing:** 24 support tickets into six labels, scored against known answers.
- **Summarizing:** three documents (an incident report, a policy memo and a meeting transcript), each in at most 120 words. Scored by how many of ten key facts survive, with penalties for claims the document never made and for running long.

## Reasoning

- **Consulting-style cases:** six cases in industries the model has no special knowledge of (cement, a hospital clinic, a market entry, a break-even, an LTV/CAC check and a piano-tuner estimate). The automatic score checks structure (a breakdown, assumptions, risks, a recommendation, a stated hypothesis), the use of relevant frameworks, and the number where the case is computable. It is a proxy for quality, not a substitute for reading the answer.
- **Planted-pattern insight:** a table of weekly operations data with three planted patterns (a lagged effect, a step change in one region, a threshold effect) and a decoy column. The model returns findings as JSON. Scored by planted patterns found, minus a penalty for claiming the decoy.

## Factuality, refusals and tools

- **Factuality:** one known fact and three invented things (an `az` command, a Terraform module, a paper), run plain, with a "say when unsure" prompt and with an expert-user prompt. Scored by a keyword check for an honest "cannot find it".
- **Refusals:** five borderline but legitimate prompts. A measurement, not a score.
- **Tool calling:** nine small tasks against sandboxed tools (right tool, exact arguments, no call when none is needed, chaining, error recovery, honesty on empty results, declining without a suitable tool, and a Linux command in WSL).

## Speed and fit

The same 3,000-token prompt and 300-token reply at 16k, 32k and 64k context, three times each. Generation and prompt speed, time to first token, share running on the CPU, peak VRAM, GPU power, energy per token and time spent power-capped. See [Hardware](/hardware/).

## Images

Four jobs: [transparent logo PNGs](/images/) (generated on a flat green background and cut out; scored for background cleanup, edge fringing and green spill), SVG logos written by text models (valid markup, no external references, sensible size), a five-slide LinkedIn carousel (a vision model reads each headline back), and a folder image derived from a generated logo (contrast at 256, 64 and 32 px). ICO conversion is out of scope.

## Not tested yet

Real agent harnesses (Claude Code, Codex, Hermes) are deliberately out of scope: the point is what a model can do on its own. Rust waits for a toolchain. Apple silicon, and GGUF against MLX, come next.
