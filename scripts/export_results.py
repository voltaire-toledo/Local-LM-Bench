"""Build the site's data file: web/src/data/results.json (schema v2).

Inputs (never modified): results/runs.rescored.jsonl (or runs.jsonl), results/toolruns.jsonl,
results/speed/<label>/speed_runs.jsonl, models/specs.json, models/verdicts.json, models/sources.json.
Quality is keyed by model; performance is keyed by (model, hardware, power label).
"""
import json, re, shutil, time
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


LANG_OF = {"go": "Go", "rust": "Rust", "ps": "PowerShell", "ahk": "AutoHotkey"}


def ratio(pairs):
    pairs = [(s, m) for s, m in pairs if s is not None and m]
    return round(sum(s for s, _ in pairs) / sum(m for _, m in pairs), 3) if pairs else None


def extras():
    """New-suite scores, viable context and image summaries (latest record per key; raw files untouched)."""
    suites = {}
    for r in latest(jl(ROOT / "results" / "suites.jsonl"), lambda r: (r["model"], r["suite"], r["task"])).values():
        if "error" in r:
            continue
        suites.setdefault(r["model"], []).append(r)
    s_out = {}
    for m, rows in suites.items():
        sel = lambda suite: [(r["score"], r["max"]) for r in rows if r["suite"] == suite]
        langs = {}
        for key, name in LANG_OF.items():
            lr = [(r["score"], r["max"]) for r in rows if r["suite"] == "code-languages" and r["task"].startswith(key + "-")]
            sc = [x for x in lr if x[0] is not None]
            langs[name] = [sum(s for s, _ in sc), len(sc)] if sc else None
        summ = [(r["score"], r["max"]) for r in rows if r["task"].startswith("summarize-")]
        cat = [(r["score"], r["max"]) for r in rows if r["task"] == "categorize-tickets"]
        s_out[m] = {"languages": ratio(sel("code-languages")), "by_language": langs, "categorize": ratio(cat), "summaries": ratio(summ), "cases": ratio(sel("consulting-cases")),
                    "insight": ratio(sel("planted-patterns")), "empty_answers": sum(1 for r in rows if r.get("empty")), "tasks": len(rows)}
    v_out = {}
    byv = defaultdict(dict)
    for r in latest(jl(ROOT / "results" / "viable.jsonl"), lambda r: (r["model"], r["ctx"])).values():
        byv[r["model"]][r["ctx"]] = r
    for m, d in byv.items():
        ladder, best = [], 0
        for c in sorted(d):
            r = d[c]
            ladder.append({"ctx": c, "viable": bool(r.get("viable")), "score": r.get("score"), "retrieval": r.get("retrieval"), "reasoning": r.get("reasoning"), "fail_reason": r.get("fail_reason"), "tps": r.get("gen_tps"), "wall_s": r.get("wall_s"), "prefill_s": r.get("prefill_s"),
                           "cpu_pct": (r.get("split") or {}).get("cpu"), "vram_peak_mib": r.get("vram_peak_mib"), "power_w": r.get("power_avg_w"), "error": r.get("error")})
        for x in ladder:
            if not x["viable"]:
                break
            best = x["ctx"]
        v_out[m] = {"viable_ctx": best, "ladder": ladder}
    imgs = latest(jl(ROOT / "results" / "images.jsonl"), lambda r: (r["kind"], r["model"], r["name"]))
    im = defaultdict(lambda: defaultdict(list))
    for (kind, model, name), r in imgs.items():
        im[model][kind].append(r)
    i_out = {}
    for model, kinds in im.items():
        e = {}
        for kind, rs in kinds.items():
            ok = [x for x in rs if x.get("ok")]
            e[kind] = {"n": len(rs), "passed": sum(1 for x in rs if x.get("pass")), "avg_secs": round(sum(x["secs"] for x in ok if x.get("secs")) / max(1, sum(1 for x in ok if x.get("secs"))), 1) if ok else None,
                       "avg_j": round(sum(x["j_per_image"] for x in ok if x.get("j_per_image")) / max(1, sum(1 for x in ok if x.get("j_per_image")))) if ok else None,
                       "avg_match": round(sum(x["match"] for x in rs if x.get("match") is not None) / max(1, sum(1 for x in rs if x.get("match") is not None)), 2) if kind == "carousel-ocr" else None}
        i_out[model] = e
    gallery = {}
    kp = ROOT / "results" / "images"
    if kp.exists():
        for f in sorted(kp.rglob("*")):
            if f.is_file():
                gallery.setdefault(str(f.parent.relative_to(kp)).replace("\\", "/"), []).append(f.name)
        dst = ROOT / "web" / "public" / "gallery"
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(kp, dst)
    return s_out, v_out, {"summary": i_out, "gallery": gallery}


def main():
    SUITE_AGG, VIABLE_AGG, IMAGES = extras()
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
            "id": m, "slug": slug(m), "suites": SUITE_AGG.get(m), "viable": VIABLE_AGG.get(m), "report": verdicts.get(m), "specs": sp or None, "sources": src,
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
    out["images"] = IMAGES
    d = ROOT / "web" / "src" / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{len(out['models'])} models -> web/src/data/results.json")


if __name__ == "__main__":
    main()
