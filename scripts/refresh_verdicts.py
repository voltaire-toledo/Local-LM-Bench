"""Refresh the data-driven parts of models/verdicts.json from web/src/data/results.json (run export_results.py first).

Only measured sentences are written: other languages, documents/reasoning/insight, and viable context with speed. Headlines, verdicts,
recommendations and caveats stay hand-curated. Idempotent: it replaces the sentences it wrote earlier (marked by a leading tag).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "web" / "src" / "data" / "results.json").read_text(encoding="utf-8"))
vp = ROOT / "models" / "verdicts.json"
V = json.loads(vp.read_text(encoding="utf-8"))
pct = lambda v: "not tested" if v is None else f"{round(v * 100)}%"
TAG = "[data] "


import re

STALE = re.compile(r"^(Not tested|Not run|Code suite not run|Factuality suite not run)\b[^.]*\.?$", re.I)


def put(area, text):
    base = area.get("text", "").split(TAG)[0].strip()  # drop sentences an earlier version appended
    area["text"] = "" if STALE.match(base) else base
    area["measured"] = text
    area["level"] = "measured"


for m in data["models"]:
    r = V.get(m["id"])
    if not r or not r.get("areas"):
        continue
    s, v = m.get("suites"), m.get("viable")
    if s:
        langs = ", ".join(f"{k} {x[0]}/{x[1]}" for k, x in (s["by_language"] or {}).items() if x) or "none"
        put(r["areas"]["apps"], f"Other languages (run for real): {langs}; Rust skipped (no toolchain).")
        docs = [x for x in (s["categorize"], s["summaries"]) if x is not None]
        note = " It claimed patterns that were not in the data (including the decoy), which is what the test is built to catch." if (s["insight"] or 0) < 0.35 else ""
        if "analysis" in r["areas"]:
            put(r["areas"]["analysis"], f"Ticket categorizing {pct(s['categorize'])}, executive summaries {pct(s['summaries'])}, consulting cases {pct(s['cases'])} (structure proxy), planted-pattern insight {pct(s['insight'])}.{note}")
    if v:
        ladder = v["ladder"]
        best = v["viable_ctx"]
        nxt = next((x for x in ladder if x["ctx"] > best), None)
        why = f" Next size ({nxt['ctx'] // 1024}k) failed: {nxt.get('fail_reason') or 'error'}." if nxt and not nxt["viable"] else ""
        tps = (m["perf"].get("win-rtx3060-12g") or {}).get("tps")
        sp = (m["perf"].get("win-rtx3060-12g") or {}).get("split") or {}
        put(r["areas"]["workflows"], f"Viable context {best // 1024 if best else 0}k (all three planted codes recalled, at least 15 tok/s, reply within 180 s).{why} At 16k: {tps if tps else '?'} tok/s with {sp.get('cpu', '?')}% on the CPU.")
vp.write_text(json.dumps(V, indent=1), encoding="utf-8")
print("verdicts refreshed")
