"""Speed/fit/power sweep. Appends to results/speed/<label>/speed_runs.jsonl.

Usage: python speed_sweep.py --label 110W --models a,b --ctx 16384,32768,65536 --repeats 3

Per run: gen/prompt tok/s, load s, time-to-first-token, CPU/GPU split, model size in memory, VRAM peak,
GPU power avg/max, clocks, temperature, energy (J) and J/token, throttle time deltas, Ollama RAM.
Run 'cold' (first repeat after a fresh load) is flagged. Quality is NOT measured here.
"""
import argparse, json, subprocess, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_env as be  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FILLER = "The migration plan covers identity, networking, policy and monitoring for the landing zone. " * 150  # about 3k tokens
PROMPT = FILLER + "\n\nIn about 200 words, explain the main risks of this plan and how to reduce them."


def chat(model, ctx):
    body = {"model": model, "messages": [{"role": "user", "content": PROMPT}], "stream": False, "think": False,
            "options": {"num_ctx": ctx, "temperature": 0, "seed": 1, "num_predict": 300}}
    req = urllib.request.Request(be.API + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--ctx", default="16384,32768,65536")
    ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    out_dir = ROOT / "results" / "speed" / a.label
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "speed_runs.jsonl"
    for model in a.models.split(","):
        for ctx in [int(c) for c in a.ctx.split(",")]:
            subprocess.run(["ollama", "stop", model], capture_output=True)
            time.sleep(2)
            for rep in range(a.repeats):
                rec = {"model": model, "ctx": ctx, "rep": rep, "cold": rep == 0, "label": a.label, "env": be.static_env(model),
                       "baseline_vram_mib": be.gpu_now().get("vram_mib") if rep == 0 else None, "other_gpu_procs": be.gpu_procs()}
                th0 = be.throttle_counters()
                t0 = time.time()
                try:
                    with be.PowerSampler() as ps:
                        r = chat(model, ctx)
                    wall = time.time() - t0
                    th1 = be.throttle_counters()
                    s = ps.summary()
                    gen_s = r["eval_duration"] / 1e9 if r.get("eval_duration") else None
                    ttft = (r.get("load_duration", 0) + r.get("prompt_eval_duration", 0)) / 1e9
                    energy = round(s.get("power_avg_w", 0) * wall, 1) if s else None
                    rec.update({
                        "gen_tps": round(r["eval_count"] / gen_s, 1) if gen_s else None,
                        "prompt_tps": round(r["prompt_eval_count"] / (r["prompt_eval_duration"] / 1e9), 1) if r.get("prompt_eval_duration") else None,
                        "prompt_tokens": r.get("prompt_eval_count"), "gen_tokens": r.get("eval_count"), "load_s": round(r.get("load_duration", 0) / 1e9, 1),
                        "ttft_s": round(ttft, 1), "wall_s": round(wall, 1), "done_reason": r.get("done_reason"),
                        "split": be.ps_split(model), "ollama_ram_mb": be.ollama_ram_mb(), **s, "energy_j": energy,
                        "j_per_token": round(energy / r["eval_count"], 2) if energy and r.get("eval_count") else None,
                        "throttle_us": {k: th1.get(k, 0) - th0.get(k, 0) for k in th1}})
                except Exception as e:  # noqa
                    rec["error"] = str(e)[:300]
                with out.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
                print(model, ctx, rep, rec.get("gen_tps"), rec.get("split"), rec.get("power_avg_w"), rec.get("error", ""), flush=True)
        subprocess.run(["ollama", "stop", model], capture_output=True)


if __name__ == "__main__":
    main()
