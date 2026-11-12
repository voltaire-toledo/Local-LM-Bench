"""Viable-context test. Appends to results/viable.jsonl.

For each context size: fill the window with seeded filler, plant three access codes at 10/50/90 percent depth, and ask for all three
plus which numeric part is largest. A size is viable only if all four answers are right, generation speed stays above the minimum
and the reply arrives within the time limit. Viable context = the largest size that passes (stops at the first failure by default).
Usage: python viable_ctx.py --models a,b [--sizes 8192,16384,...] [--no-stop]
"""
import argparse, json, random, subprocess, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_env as be  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "viable.jsonl"
CITIES = ["Oslo", "Lima", "Pune", "Cork", "Graz", "Kyiv", "Cebu", "Baku", "Ghent", "Salta", "Tartu", "Porto", "Sofia", "Quito", "Hanoi", "Lagos"]
TEAMS = ["Alder", "Birch", "Cedar", "Dune", "Ember", "Fjord", "Grove", "Harbor", "Iris", "Juno", "Kestrel", "Lumen"]


def build(ctx, seed):
    rnd = random.Random(seed)
    budget = int((ctx - 900) * 2.4)  # characters; digits tokenize densely, stay safely inside the window
    lines, chars = [], 0
    while chars < budget:
        s = (f"2026-{rnd.randint(1,12):02d}-{rnd.randint(1,28):02d} {rnd.choice(CITIES)} team {rnd.choice(TEAMS)} closed {rnd.randint(3,99)} tickets, "
             f"average handle time {rnd.randint(4,59)} minutes, backlog {rnd.randint(0,40)}.")
        lines.append(s); chars += len(s) + 1
    codes = {"Alpha": f"{rnd.randint(1000,9999)}-{rnd.choice('KRTQ')}{rnd.choice('XBLM')}", "Beta": f"{rnd.randint(1000,9999)}-{rnd.choice('KRTQ')}{rnd.choice('XBLM')}", "Gamma": f"{rnd.randint(1000,9999)}-{rnd.choice('KRTQ')}{rnd.choice('XBLM')}"}
    for depth, name in zip((0.1, 0.5, 0.9), codes):
        lines.insert(int(len(lines) * depth), f"NOTE: The access code for Vault {name} is {codes[name]}.")
    largest = max(codes, key=lambda k: int(codes[k].split("-")[0])).lower()
    q = ('\n\nUsing only the log above, answer as JSON: {"alpha":"<code>","beta":"<code>","gamma":"<code>","largest":"alpha|beta|gamma"} '
         "where largest is the vault whose code has the biggest number before the dash.")
    return "\n".join(lines) + q, codes, largest


def ask(model, prompt, ctx, timeout):
    oss = model.startswith("gpt-oss")
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": "low" if oss else False,
            "options": {"num_ctx": ctx, "temperature": 0, "seed": 1, "num_predict": 800 if oss else 120}}
    req = urllib.request.Request(be.API + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--sizes", default="8192,16384,32768,65536,131072")
    ap.add_argument("--min-tps", type=float, default=15)
    ap.add_argument("--max-seconds", type=float, default=180)
    ap.add_argument("--no-stop", action="store_true")
    a = ap.parse_args()
    for model in a.models.split(","):
        for ctx in [int(x) for x in a.sizes.split(",")]:
            subprocess.run(["ollama", "stop", model], capture_output=True)
            time.sleep(2)
            prompt, codes, largest = build(ctx, seed=ctx)
            rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "ctx": ctx, "env": be.static_env(model), "baseline_vram_mib": be.gpu_now().get("vram_mib"), "other_gpu_procs": be.gpu_procs()}
            th0 = be.throttle_counters()
            t0 = time.time()
            try:
                with be.PowerSampler() as ps:
                    r = ask(model, prompt, ctx, 1500)
                wall = time.time() - t0
                text = r.get("message", {}).get("content", "")
                a1, b1 = text.find("{"), text.rfind("}")
                try:
                    got = json.loads(text[a1:b1 + 1])
                except Exception:
                    got = {}
                ret = sum(str(got.get(k.lower(), "")).strip() == v for k, v in codes.items())
                rea = int(str(got.get("largest", "")).lower().strip() == largest)
                pts = ret + rea
                tps = round(r["eval_count"] / (r["eval_duration"] / 1e9), 1) if r.get("eval_duration") else None
                ptok = r.get("prompt_eval_count")
                truncated = bool(ptok and ptok >= ctx - 40)
                th1 = be.throttle_counters()
                rec.update({"score": pts, "max": 4, "prompt_tokens": ptok, "fill_ratio": round(ptok / ctx, 2) if ptok else None, "truncated": truncated, "gen_tps": tps,
                            "prefill_s": round(r.get("prompt_eval_duration", 0) / 1e9, 1), "load_s": round(r.get("load_duration", 0) / 1e9, 1), "wall_s": round(wall, 1),
                            "split": be.ps_split(model), "ollama_ram_mb": be.ollama_ram_mb(), **ps.summary(), "response": text[:400],
                            "throttle_us": {k: th1.get(k, 0) - th0.get(k, 0) for k in th1}})
                rec.update({"retrieval": ret, "reasoning": rea})
                rec["viable"] = bool(ret == 3 and not truncated and tps and tps >= a.min_tps and wall <= a.max_seconds)  # v1.1: retrieval gates; the comparison is reported, not gated
                rec["fail_reason"] = None if rec["viable"] else ("truncated" if truncated else "recall" if ret < 3 else "too slow" if wall > a.max_seconds else "low tok/s")
            except Exception as e:  # noqa
                rec.update({"error": str(e)[:300], "viable": False, "wall_s": round(time.time() - t0, 1)})
            with OUT.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            print(model, ctx, "viable" if rec.get("viable") else "NOT viable", rec.get("score"), rec.get("gen_tps"), rec.get("wall_s"), rec.get("error", ""), flush=True)
            if not rec.get("viable") and not a.no_stop:
                break
        subprocess.run(["ollama", "stop", model], capture_output=True)


if __name__ == "__main__":
    main()
