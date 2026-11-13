"""Join `sudo powermetrics -f plist` samples to Mac speed-sweep records (TASK-4).

Usage: python scripts/mac_power_join.py --plist .local/powermetrics.plist --label mac-m4-pro-24g-power
Reads results/speed/<label>/speed_runs.jsonl (never modified) and writes power_join.jsonl beside it:
one record per sweep request with GPU, CPU and combined average watts, energy (J) and J per generated token.
Window per request: env.ts (local time, start) to start + wall_s. Failures print JSON {"status": "error", ...}.
"""
import argparse, json, plistlib, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def samples(path):
    out = []
    for chunk in Path(path).read_bytes().split(b"\x00"):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            d = plistlib.loads(chunk)
        except Exception:
            continue  # last chunk may be partial while powermetrics is still writing
        p = d.get("processor", {})
        end = d["timestamp"].replace(tzinfo=None)  # UTC
        out.append({"start": end - timedelta(microseconds=d["elapsed_ns"] / 1000), "end": end,
                    "gpu_w": p.get("gpu_power", 0) / 1000, "cpu_w": p.get("cpu_power", 0) / 1000,
                    "all_w": p.get("combined_power", 0) / 1000})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plist", required=True)
    ap.add_argument("--label", required=True)
    a = ap.parse_args()
    runs = ROOT / "results" / "speed" / a.label / "speed_runs.jsonl"
    if not runs.exists():
        print(json.dumps({"status": "error", "reason": f"missing {runs}"}))
        sys.exit(1)
    s = samples(a.plist)
    if not s:
        print(json.dumps({"status": "error", "reason": "no readable powermetrics samples"}))
        sys.exit(1)
    joined, missing = [], 0
    for line in runs.read_text().splitlines():
        r = json.loads(line)
        if r.get("error") or not r.get("wall_s"):
            continue
        t0 = datetime.fromtimestamp(datetime.fromisoformat(r["env"]["ts"]).timestamp(), timezone.utc).replace(tzinfo=None)
        t1 = t0 + timedelta(seconds=r["wall_s"])
        win = [x for x in s if x["end"] > t0 and x["start"] < t1]
        if not win:
            missing += 1
            continue
        avg = {k: round(sum(x[k] for x in win) / len(win), 2) for k in ("gpu_w", "cpu_w", "all_w")}
        e = {k: round(avg[k] * r["wall_s"], 1) for k in avg}
        joined.append({"model": r["model"], "ctx": r["ctx"], "rep": r["rep"], "cold": r["cold"], "label": a.label,
                       "env": r["env"], "gen_tps": r.get("gen_tps"), "wall_s": r["wall_s"], "gen_tokens": r.get("gen_tokens"),
                       "power_avg_w": avg, "energy_j": e, "n_samples": len(win), "source": "powermetrics gpu_power,cpu_power",
                       "j_per_token": {k: round(v / r["gen_tokens"], 2) for k, v in e.items()} if r.get("gen_tokens") else None})
    out = runs.parent / "power_join.jsonl"
    out.write_text("".join(json.dumps(j) + "\n" for j in joined))
    print(json.dumps({"status": "ok", "joined": len(joined), "no_samples": missing, "out": str(out.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
