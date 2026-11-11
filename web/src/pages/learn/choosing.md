---
layout: ../../layouts/Base.astro
title: Local or cloud? A decision flow
description: Five questions that decide whether a task belongs on a local model or a cloud one, with viable context as the hard limit.
---
# Local or cloud? A decision flow

Choosing a model almost always comes down to the same five questions. Two are **hard limits** that can veto the choice outright, so ask them first. Three are **preferences** that tilt it.

## Hard limits

### 1. Does the data need to stay private?
**Yes: local, no exceptions.** Then the only question left is whether the job fits (see 2).

### 2. Will the instructions and the data fit in the model's *viable* context?
Not the advertised window: the largest size where the model still finds facts, answers correctly, runs at a usable speed and fits in memory. This site measures it for each model.

**No: this is a deal breaker.** Pick one:
- Split the work (summarize in chunks, retrieve only what is needed, hand off between steps).
- If the data is not private, use a cloud model with a larger window.
- If the data is private and cannot be split, keep it local and accept a weaker result.
- Only if you still need the cloud, decide whether the risk of sending private data is acceptable. That is your call, not a default.

## Preferences

### 3. What is the objective?
The more **deterministic** the task, the more it belongs on a local model. If it is fully deterministic, a plain script beats any model. Local models earn their place where the work is mostly mechanical with fuzzy edges: sorting, extracting, rewriting, running a checklist.

### 4. Can I afford the tokens, and do I want to spend them here?
Local models win when the work is:
- high volume and repetitive,
- very long running,
- an agent that must be durable and start itself (MQTT messages, webhooks, schedules).

A cloud subscription wins for one-off or low-volume jobs where its quality matters more than its cost.

### 5. What is the time coefficient?
Assume a local model runs at a fraction of cloud speed. That suits **agentic work, troubleshooting and coding**, where waiting is fine. It suits **strategic planning, architecture, high-volume research and real-time sentiment** badly.

If time does not matter, lean local, but only with the four things that make a small model dependable:
1. a capable harness,
2. agent definitions and instructions,
3. battle-tested skills,
4. written SOPs.

## The flow at a glance

| Question | Answer | Lean |
|---|---|---|
| Must the data stay private? | Yes | Local |
| Do instructions and data fit the viable context? | No | Split the work, or decide on the cloud risk yourself |
| Is the task mostly deterministic? | Yes | Local (or a script) |
| High volume, long running or trigger-started? | Yes | Local |
| Do I mind slow? | No | Local, with harness, agents, skills and SOPs |
| Strategic, architectural or real-time? | Yes | Cloud |

Most real setups end up **hybrid**: cloud for planning and judgment, local for the volume and the private data.
