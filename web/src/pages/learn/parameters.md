---
layout: ../../layouts/Base.astro
title: Parameters and the API
description: Every knob you can turn when calling a local model, with scripts you can copy and run to watch what each one does.
---
# Parameters: the knobs, and what they do to the scores

Every score on this site comes from a program talking to a model through an API. Same API you can use. This page shows the knobs, with
small scripts you can copy and run, and what they printed when I ran them. Change a number, run it again, watch what happens. That beats
any explanation.

You need [Ollama](https://ollama.com) running and one model pulled (`ollama pull qwen3.5:9b`, about 6.6 GB). The scripts use only the
Python standard library: no installs.

## The helper

Save this as `llm.py`. Every script below imports it, so keep them in the same folder.

```python
# llm.py - a tiny helper for Ollama's chat API (Python standard library only)
import json, time, urllib.request

HOST = "http://localhost:11434"
MODEL = "qwen3.5:9b"  # any model you have pulled with `ollama pull`

def chat(prompt, system=None, model=MODEL, think=False, **options):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = {"model": model, "messages": msgs, "stream": False, "think": think, "options": options}
    req = urllib.request.Request(HOST + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=600))
    r["wall_s"] = round(time.time() - t0, 1)
    r["tok_s"] = round(r["eval_count"] / (r["eval_duration"] / 1e9), 1) if r.get("eval_duration") else None
    return r
```

Every reply carries counters you can learn from: `prompt_eval_count` (tokens read), `eval_count` (tokens written), the durations
behind them in nanoseconds, and `done_reason` (`stop` if it finished, `length` if it ran out of budget).

## The knobs at a glance

| Parameter | What it does | Benchmarks here use | Turn it up when | Turn it down when |
|---|---|---|---|---|
| `temperature` | How adventurous the word choices are | 0 | brainstorming, naming, variety | facts, code, anything you want repeatable |
| `seed` | Fixes the dice so a random run can be replayed | fixed | you want to reproduce a creative result | (leave unset for fresh randomness) |
| `top_p`, `top_k`, `min_p` | Trim the list of candidate words before the dice roll | runtime defaults | rarely; temperature is the main dial | you see rambling or oddball words |
| `num_ctx` | The size of the [context window](/learn/context/) | 16k quality, 16k to 128k speed | long documents, long agent runs | short chats; saves memory and time |
| `num_predict` | Maximum tokens it may write | sized per test | long answers, thinking models | you want short, cheap answers |
| `think` | Lets reasoning models think before answering | off | puzzles, math, multi-step logic | lookups, formatting, speed |
| `repeat_penalty` | Discourages repeating itself | runtime default | it loops or repeats lines | it avoids words it should repeat (names, code) |
| system prompt | Standing instructions above the conversation | none, and "say when unsure" | always worth a line or two | never empty if facts matter |
| `format` | Forces JSON, optionally to a schema | not used; handy for categorizing | you parse the output in code | free text |
| `keep_alive` | How long the model stays loaded after a request | default (5 min) | batch jobs: avoid reloading | you need the memory back |

<a id="temperature"></a>
## Temperature: same question, five times

```python
# temperature.py - same question five times at each temperature
from llm import chat

q = "Suggest a name for a coffee shop run by robots. Reply with the name only."
for temp in (0, 0.7, 1.5):
    names = [chat(q, temperature=temp, num_predict=20)["message"]["content"].strip() for _ in range(5)]
    print(f"temperature {temp}: {len(set(names))} different answers -> {names}")
```

What it printed on the 24 GB Mac with `qwen3.5:9b`:

```text
temperature 0: 1 different answers -> ['BotBrew', 'BotBrew', 'BotBrew', 'BotBrew', 'BotBrew']
temperature 0.7: 3 different answers -> ['RoboBrew', 'Barista 404', 'Bot & Bean', 'RoboBrew', 'RoboBrew']
temperature 1.5: 5 different answers -> ['BotBean', 'The Gears of Joy', 'Brew Bot', 'AutoCafe', 'AutoGrind']
```

**Why the benchmarks run at 0:** a score should mean the same thing tomorrow. At 0 the model picks its single most likely word every
time, so a pass is a pass. Your own work might want more spice; just know that at 1.5 you are scoring a different "model" every run.

<a id="seed"></a>
## Seed: randomness you can replay

```python
# seed.py - randomness you can replay
from llm import chat

q = "Write a one-line slogan for a bike repair shop."
a = chat(q, temperature=1.0, seed=42)["message"]["content"]
b = chat(q, temperature=1.0, seed=42)["message"]["content"]
c = chat(q, temperature=1.0, seed=7)["message"]["content"]
print("seed 42, run 1:", a)
print("seed 42, run 2:", b, "(same)" if a == b else "(different)")
print("seed 7:        ", c)
```

What it printed on the 24 GB Mac with `qwen3.5:9b`:

```text
seed 42, run 1: Fixing fast, riding far.
seed 42, run 2: Fixing fast, riding far. (same)
seed 7:         We fix you up so you can ride away.
```


<a id="accuracy"></a>
## The system prompt: one sentence that changes the accuracy score

The Azure command below does not exist. Watch what one line of instructions does.

```python
# accuracy.py - does it invent things? Same fake question, with and without permission to say "I don't know"
from llm import chat

fake = "What does the Azure CLI command `az network vhub fluxroute enable` do? Show an example."
honest = "If you are not sure something exists, say so plainly instead of guessing."
for system in (None, honest):
    reply = chat(fake, system=system, temperature=0, num_predict=200)["message"]["content"]
    caught = any(w in reply.lower() for w in ("not aware", "does not exist", "doesn't exist", "not sure", "no such", "cannot find", "not a real", "not familiar", "unable to find", "could not find", "isn't a"))
    print(f"system prompt: {'say when unsure' if system else 'none':16} caught the fake: {caught}")
    print("  ", reply[:160].replace("\n", " "), "...\n")
```

What it printed on the 24 GB Mac with `qwen3.5:9b`:

```text
system prompt: none             caught the fake: False
   The Azure CLI command **`az network vhub fluxroute enable`** is used to **enable Flux routing** for a specific Virtual Hub (vHub) within an Azure ExpressRoute G ...

system prompt: say when unsure  caught the fake: True
   The command `az network vhub fluxroute enable` **does not exist** in the current Azure CLI.  There is no such command, and it appears to be a confusion of sever ...
```

This is exactly what the factuality test measures: the same fake questions with no system prompt and with a "say when unsure" one. For anything factual, give the model explicit
permission to say it does not know.

<a id="num_ctx"></a>
## num_ctx: the window size

A code word on the first line, then about 8,500 tokens of filler.

```python
# num_ctx.py - a bigger window costs memory and time even for the same prompt; too small a window silently cuts the prompt
import json, urllib.request
from llm import chat, HOST, MODEL

doc = "The access code is KESTREL-7. " + "Filler sentence about nothing in particular. " * 1200  # about 8,500 tokens
for ctx in (4096, 16384, 65536):
    r = chat(doc + "\nWhat is the access code? Reply with the code only.", temperature=0, num_ctx=ctx, num_predict=20)
    ps = json.load(urllib.request.urlopen(HOST + "/api/ps"))["models"]
    mem = next((m["size"] for m in ps if m["name"].startswith(MODEL)), 0) / 1e9
    print(f"num_ctx {ctx:6}: read {r['prompt_eval_count']:5} tokens, answer {r['message']['content'].strip()!r:14} model+cache in memory {mem:.1f} GB, {r['wall_s']} s")
```

What it printed on the 24 GB Mac with `qwen3.5:9b`:

```text
num_ctx   4096: read  2050 tokens, answer 'I cannot provide an access code, as this appears to be a test of my ability to ignore irrelevant' model+cache in memory 5.5 GB, 13.4 s
num_ctx  16384: read  9635 tokens, answer 'KESTREL-7'    model+cache in memory 6.0 GB, 46.3 s
num_ctx  65536: read  9635 tokens, answer 'KESTREL-7'    model+cache in memory 8.2 GB, 52.1 s
```

Three lessons in one run. At 4k the prompt was **cut without warning** (only about 2,000 tokens survived) and the code word went with it,
so the model had nothing to find. At 16k it worked. At 64k it also worked, but the model held 2.2 GB more memory for the same job.
Set `num_ctx` to what the job needs, not to the maximum. Ollama keeps the newest part of a prompt that is too long, so put the question
last.

<a id="num_predict"></a>
## num_predict: the output budget

```python
# num_predict.py - the output budget; when it runs out the answer just stops
from llm import chat

for n in (30, 400):
    r = chat("Explain in three short paragraphs why the sky is blue.", temperature=0, num_predict=n)
    print(f"num_predict {n}: {r['eval_count']} tokens written, done_reason={r['done_reason']!r}")
    print("  ends with:", repr(r["message"]["content"][-60:]), "\n")
```

What it printed on the 24 GB Mac with `qwen3.5:9b`:

```text
num_predict 30: 30 tokens written, done_reason='length'
  ends with: "h's atmosphere, it collides with gas molecules like nitrogen" 

num_predict 400: 252 tokens written, done_reason='stop'
  ends with: ' is why the sky takes on those warm hues during those times.'
```

If `done_reason` says `length`, the answer was chopped. Thinking models spend this budget on thinking first, which is how you get an
empty answer from a model that "thought" until it ran out.

<a id="think"></a>
## Thinking: on or off

```python
# think.py - thinking on vs off: same puzzle, very different token bill
from llm import chat

q = "A bat and a ball cost $1.10 together. The bat costs $1.00 more than the ball. How much is the ball? Answer with the amount only."
for think in (False, True):
    r = chat(q, think=think, temperature=0, num_predict=4000)
    thought = len(r["message"].get("thinking") or "")
    print(f"think={think!s:5}: answer {r['message']['content'].strip()!r:10} {r['eval_count']:5} tokens generated ({thought} chars of thinking), {r['wall_s']} s")
```

What it printed on the 24 GB Mac with `qwen3.5:9b`:

```text
think=False: answer '0.05'         5 tokens generated (0 chars of thinking), 0.5 s
think=True : answer '$0.05'      809 tokens generated (2407 chars of thinking), 36.3 s
```

Same answer, 160 times the tokens, 70 times the wait. Thinking pays off on genuinely hard multi-step problems; on easy ones it is a tax.
The benchmarks here run with thinking off, so a thinking model is judged on what it does without that crutch.

<a id="speed"></a>
## Speed: reading versus writing

The "tok/s" on the compare page is the **writing** speed. Long prompts add a second cost: the model has to read everything first.

```python
# speed.py - where the time goes: reading the prompt vs writing the answer
from llm import chat

prompt = "Summarize this in two sentences:\n" + ("Quarterly revenue rose in the north region while costs held flat. " * 300)
r = chat(prompt, temperature=0, num_ctx=16384, num_predict=120)
read_s, write_s = r["prompt_eval_duration"] / 1e9, r["eval_duration"] / 1e9
print(f"read  {r['prompt_eval_count']:5} tokens in {read_s:5.1f} s = {r['prompt_eval_count'] / read_s:7.1f} tok/s  (prompt processing)")
print(f"wrote {r['eval_count']:5} tokens in {write_s:5.1f} s = {r['eval_count'] / write_s:7.1f} tok/s  (generation, the number on the compare page)")
print(f"load {r['load_duration'] / 1e9:.1f} s, total {r['wall_s']} s")
```

What it printed on the 24 GB Mac with `qwen3.5:9b`:

```text
read   3622 tokens in  16.5 s =   218.9 tok/s  (prompt processing)
wrote    36 tokens in   1.7 s =    20.9 tok/s  (generation, the number on the compare page)
load 3.5 s, total 21.9 s
```

Reading here ran at about ten times the writing speed, but with 3,600 tokens to read and only 36 to write, reading took most of the
time. Scale the prompt up to 64k and that is why the Mac waits minutes before the first word. Short, focused prompts are faster prompts.

<a id="format"></a>
## format: answers your code can parse

```python
# json_format.py - force structured output with a JSON schema (handy for categorizing)
import json, urllib.request
from llm import HOST, MODEL

schema = {"type": "object", "properties": {"label": {"enum": ["billing", "outage", "access", "bug", "feature", "other"]},
          "confidence": {"type": "number"}}, "required": ["label", "confidence"]}
ticket = "I was charged twice for March and the invoice shows the wrong company name."
body = {"model": MODEL, "stream": False, "think": False, "format": schema, "options": {"temperature": 0},
        "messages": [{"role": "user", "content": f"Categorize this support ticket: {ticket}"}]}
req = urllib.request.Request(HOST + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
print(json.loads(json.load(urllib.request.urlopen(req))["message"]["content"]))
```

What it printed on the 24 GB Mac with `qwen3.5:9b`:

```text
{'label': 'billing', 'confidence': 0.95}
```


<a id="tools"></a>
## Tools: the model asks, your code acts

```python
# tools.py - tool calling: the model asks, your code runs the tool, the model answers
import json, urllib.request
from llm import HOST, MODEL

def get_disk_free(drive):  # a pretend tool
    return {"drive": drive, "free_gb": 41.7}

tools = [{"type": "function", "function": {"name": "get_disk_free", "description": "Free space on a drive in GB",
          "parameters": {"type": "object", "properties": {"drive": {"type": "string"}}, "required": ["drive"]}}}]
msgs = [{"role": "user", "content": "How much free space is on drive D?"}]

def ask():
    body = {"model": MODEL, "messages": msgs, "tools": tools, "stream": False, "think": False, "options": {"temperature": 0}}
    req = urllib.request.Request(HOST + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["message"]

m = ask()
for call in m.get("tool_calls", []):
    fn, args = call["function"]["name"], call["function"]["arguments"]
    print("model called:", fn, args)
    msgs += [m, {"role": "tool", "tool_name": fn, "content": json.dumps(get_disk_free(**args))}]
print("final answer:", ask()["content"])
```

What it printed on the 24 GB Mac with `qwen3.5:9b`:

```text
model called: get_disk_free {'drive': 'D'}
final answer: There is 41.7 GB of free space on drive D.
```

The model never runs anything itself. It replies with a request (`tool_calls`), your code decides whether to run it, and the result goes
back as a `tool` message. Every round trip lands in the context window, which is why agent work eats windows so fast.

## Other runtimes

LM Studio, llama.cpp's `llama-server` and the MLX bridge used for the Mac tests all speak close to the same API (Ollama's, or OpenAI's
`/v1/chat/completions`). The parameter names differ slightly (`max_tokens` instead of `num_predict`, for example); the ideas do not.
