"""Build the site's data file: web/src/data/results.json (schema v2).

Inputs (never modified): results/runs.rescored.jsonl (or runs.jsonl), results/toolruns.jsonl,
results/speed/<label>/speed_runs.jsonl, models/specs.json, models/verdicts.json, models/sources.json.
Quality is keyed by model; performance is keyed by (model, hardware, power label).
"""
import json, re, time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HW = {
    "win-rtx3060-12g": {"label": "Windows PC, RTX 3060 12 GB, 128 GB RAM", "kind": "discrete-gpu", "memory_gb": 12, "system_ram_gb": 128,
                        "cpu": "Intel Core i7-13700K", "os": "Windows 11", "runtime": "Ollama 0.40.16 (llama.cpp)", "driver": "NVIDIA 610.88",
                        "bandwidth_gbs": 360, "power_default_w": 170},
}
HW_ID = "win-rtx3060-12g"
SPEED_LABEL = "110W"


def jl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def latest(rows, keyfn):
    out = {}
    for r in rows:
        out[keyfn(r)] = r
    return out


def slug(m):
    return re.sub(r"[^a-z0-9]+", "-", m.lower()).strip("-")


def js(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def split_from_ps(model, ps):
    if not ps or not ps.split()[0].startswith(model):
        return None
    m = re.search(r"(\d+)%/(\d+)% CPU/GPU", ps)
    if m:
        return {"cpu": int(m.group(1)), "gpu": int(m.group(2))}
    return {"cpu": 0, "gpu": 100} if "100% GPU" in ps else None


def cnt(rows, f):
    return [sum(1 for r in rows if f(r)), len(rows)] if rows else None


def main():
    rs = ROOT / "results" / "runs.rescored.jsonl"
    runs = latest(jl(rs if rs.exists() else ROOT / "results" / "runs.jsonl"), lambda r: (r["model"], r["id"], r["variant"], r["ctx"], r["rep"]))
    tool = latest(jl(ROOT / "results" / "toolruns.jsonl"), lambda r: (r["model"], r["id"], r["variant"], r["ctx"]))
    specs = js(ROOT / "models" / "specs.json").get("models", {})
    verdicts, sources = js(ROOT / "models" / "verdicts.json"), js(ROOT / "models" / "sources.json")
    sweep = defaultdict(list)
    for r in jl(ROOT / "results" / "speed" / SPEED_LABEL / "speed_runs.jsonl"):
        if "error" not in r:
            sweep[(r["model"], r["ctx"])].append(r)
    models = sorted({k[0] for k in runs} | {k[0] for k in tool} | set(specs))
    out = {"schema": 2, "generated": time.strftime("%Y-%m-%d"), "hardware": HW, "speed_label": SPEED_LABEL, "models": []}
    for m in models:
        mr = [r for k, r in runs.items() if k[0] == m]
        base = [r for r in mr if r["variant"] == "none"]
        tr = [r for k, r in tool.items() if k[0] == m]
        code = [r for r in base if r["suite"] in ("code", "debug")]
        fake = [r for r in base if r["suite"] == "factuality" and r["id"] != "F1-known-fact"]
        gfake = [r for r in mr if r["variant"] == "grounded" and r["suite"] == "factuality" and r["id"] != "F1-known-fact"]
        refus = [r for r in base if r["suite"] == "refusal"]
        old_tps = [r["gen_tps"] for r in base if r.get("gen_tps")]
        old_split = next((s for s in (split_from_ps(m, r.get("ps")) for r in base) if s), None)
        sw = {}
        for (mm, c), rows in sweep.items():
            if mm != m:
                continue
            warm = [x for x in rows if not x["cold"]] or rows
            av = lambda k: round(sum(x.get(k) or 0 for x in warm) / len(warm), 1)
            sw[str(c)] = {"tps": av("gen_tps"), "power_w": av("power_avg_w"), "j_per_token": av("j_per_token"), "cpu_pct": (rows[-1].get("split") or {}).get("cpu"),
                          "vram_peak_mib": max(x.get("vram_peak_mib") or 0 for x in rows), "ttft_cold_s": next((x["ttft_s"] for x in rows if x["cold"]), None),
                          "power_capped_s": round(sum(x.get("throttle_us", {}).get("SW Power Capping", 0) for x in rows) / 1e6, 1)}
        s16 = sw.get("16384")
        sp = specs.get(m, {})
        src = sources.get("models", {}).get(m)
        out["models"].append({
            "id": m, "slug": slug(m), "report": verdicts.get(m), "specs": sp or None, "sources": src,
            "family": sp.get("family"), "params": sp.get("parameters"), "quant": sp.get("quantization"), "size_gb": sp.get("size_gb"), "digest": sp.get("digest"),
            "quality": {
                "code": cnt(code, lambda r: r["result"].get("pass")),
                "fake_caught": cnt(fake, lambda r: r["result"].get("abstained")),
                "fake_caught_grounded": cnt(gfake, lambda r: r["result"].get("abstained")),
                "refused": cnt(refus, lambda r: r["result"].get("refused")),
                "tools": cnt(tr, lambda r: r.get("pass"))},
            "perf": {HW_ID: {"tps": s16["tps"] if s16 else (round(sum(old_tps) / len(old_tps), 1) if old_tps else None),
                             "tps_source": "sweep" if s16 else ("short-test" if old_tps else None),
                             "split": ({"cpu": s16["cpu_pct"], "gpu": 100 - s16["cpu_pct"]} if s16 and s16["cpu_pct"] is not None else old_split),
                             "sweep": sw or None}}})
    d = ROOT / "web" / "src" / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{len(out['models'])} models -> web/src/data/results.json")


if __name__ == "__main__":
    main()
