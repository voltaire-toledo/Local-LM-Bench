---
layout: ../layouts/Base.astro
title: The tests
description: What each benchmark test asks, why it matters, how it is scored and how it tries to break the models.
---
# The tests

Every model gets the same prompts at temperature 0, with a fixed context window, through the same harness. Where a test can be scored by a program (code runs, a template validates, an exact string matches) it is. Where it cannot, I read the answers myself and say so.

## Code and debugging

| Test | What it asks | Scored by |
|---|---|---|
| Interval merge | Write a Python function that merges overlapping intervals | Running four assertions, including empty input and unsorted input |
| Fix the bug | Repair a broken Fibonacci function | Running four assertions |
| Hub network | Write Terraform for a hub VNet with three subnets and an NSG that allows only 443 | `terraform init` and `terraform validate` against the real azurerm provider |

**Why it matters:** this is most of the daily work. **How it bites:** the Terraform test is where models invent arguments that do not exist, such as `network_security_group_id` on a subnet. Valid syntax is the bar; I do not yet check that the result matches every requirement.

## Factuality: does it make things up?

Four questions: one known fact (the SQL Server default port) and three about things that do not exist, an invented `az` command, an invented Terraform module and an invented research paper. A good model says it cannot find them. A bad one writes a confident answer. Each question runs three ways: plain, with a "say when you are unsure" prompt, and with a prompt that tells the model I am an experienced engineer.

**Scored by:** a keyword check for an honest "this does not exist or I cannot verify it", then I read the disagreements. It is a blunt instrument; it has already needed two fixes.

## Refusals on legitimate questions

Five borderline but legitimate prompts: scanning my own lab with nmap, SQL injection against a deliberately vulnerable practice app, a safe acetaminophen dose, how lock picking works, and how attackers persist on Windows (for writing detections). **Scored by:** whether the model refuses or buries the answer in warnings. Fewer refusals is not automatically better, so this is a measurement and not a score.

## Long-context recall

A short fact is hidden in about 12,000 tokens of filler and the model is asked for it. **Why it matters:** a model that cannot find one fact is not going to summarize a long document well. Every model passed, so it does not separate them yet.

## Tool calling

Nine small tasks against a sandboxed set of tools: pick the right tool, write exact arguments, make no call when none is needed, chain two calls, recover from a missing file, report honestly when a search returns nothing, fix a bug and run the result, decline when no suitable tool exists, and run a read-only Linux command in WSL. **Scored by:** programs that inspect the calls and the final state. **How it bites:** the recovery and honesty tasks. Some models also print a correct call as plain text instead of making a real tool call, which a real harness would not accept.

## Speed and fit

Each model runs the same 3,000-token prompt and 300-token reply at 16k, 32k and 64k context, three times each. I record generation and prompt speed, time to first token, how much of the model runs on the CPU, peak VRAM, GPU power, energy per token and time spent power-capped. See [Hardware](/hardware/).

## Not tested yet

Go, Rust, PowerShell and AutoHotkey, summarizing and categorizing documents, consulting-style case questions, planted-pattern insight finding, image generation, and the same models through real agent harnesses such as Claude Code and Codex.
