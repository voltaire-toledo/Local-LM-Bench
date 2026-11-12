"""Unattended, resumable batch for one power setting. Everything is recorded with the power limit; steps already done are skipped.

Usage: python run_all.py --label 110W --expect-watts 110
Steps (in order): tool calling and main quality suite for models that lack them, speed sweep for the new model, image tests,
new suites per model, viable-context per model. Logs to results/logs/run_all.log, state in results/run_all_<label>.state.json.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_env as be  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "scripts"
UD = "hf.co/unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_M"
MODELS = ["gemma4:12b-it-q4_K_M", "qwen3.5:9b", "gemma4:26b-a4b-it-qat", "laguna-xs-2.1:q4_K_M", "qwen3.6:35b-a3b-q4_K_M", UD,
          "granite4:32b-a9b-h", "nemotron-3.5-lightning:30b-a3b", "qwen3-coder:30b-a3b-q4_K_M", "gpt-oss:20b"]
SVG_MODELS = ["gemma4:12b-it-q4_K_M", "laguna-xs-2.1:q4_K_M", "qwen3.6:35b-a3b-q4_K_M", "qwen3.5:9b"]
NEED_MAIN = ["granite4:32b-a9b-h", "qwen3-coder:30b-a3b-q4_K_M", UD]
SUITES = "code-languages,summarize-categorize,consulting-cases,planted-patterns"
PY = sys.executable


def steps():
    out = [("tool-calling " + UD, [PY, str(S / "tool_bench.py"), "--models", UD]),
           ("speed-sweep " + UD, [PY, str(S / "speed_sweep.py"), "--label", "110W", "--models", UD, "--ctx", "16384,32768,65536", "--repeats", "3"])]
    for m in NEED_MAIN:
        out.append(("main-quality " + m, [PY, str(S / "run_bench.py"), "--models", m, "--ctx", "16384", "--variants", "none,grounded,context"]))
    out.append(("images core", [PY, str(S / "image_bench.py"), "--models", "zimage,flux2klein,sdxl", "--tests", "logo-png,carousel,folder-icon"]))
    out.append(("images svg", [PY, str(S / "image_bench.py"), "--tests", "logo-svg", "--svg-models", ",".join(SVG_MODELS)]))
    for m in MODELS:
        out.append(("suites " + m, [PY, str(S / "suite_runner.py"), "--suite", SUITES, "--models", m]))
    for m in MODELS:
        out.append(("viable-context " + m, [PY, str(S / "viable_ctx.py"), "--models", m]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--expect-watts", type=float, required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    (ROOT / "results" / "logs").mkdir(parents=True, exist_ok=True)
    state_p = ROOT / "results" / f"run_all_{a.label}.state.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {"done": {}, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    logf = (ROOT / "results" / "logs" / "run_all.log").open("a", encoding="utf-8")

    def say(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()

    todo = steps()
    if a.dry_run:
        for n, _ in todo:
            print(("done  " if n in state["done"] else "todo  ") + n)
        return
    say(f"start {a.label}: {len(todo)} steps; GPU {be.gpu_now()}; other GPU procs {be.gpu_procs()}")
    for name, cmd in todo:
        if name in state["done"]:
            continue
        g = be.gpu_now()
        if not be.IS_MAC and g.get("power_limit_w") != a.expect_watts:  # Macs have no nvidia-smi power limit
            say(f"ABORT: power limit is {g.get('power_limit_w')} W, expected {a.expect_watts} W (results would be mixed)")
            sys.exit(2)
        say(f"begin {name}")
        t0 = time.time()
        r = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT)
        state["done"][name] = {"rc": r.returncode, "minutes": round((time.time() - t0) / 60, 1), "power_limit_w": g.get("power_limit_w"), "other_gpu_procs": be.gpu_procs()}
        state_p.write_text(json.dumps(state, indent=1))
        say(f"end {name} rc={r.returncode} {state['done'][name]['minutes']} min")
    state["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    state_p.write_text(json.dumps(state, indent=1))
    say("ALL DONE")


if __name__ == "__main__":
    main()
