"""Summarize results/runs.jsonl -> results/summary.md (latest run per model/prompt/variant/ctx)."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
latest = {}
_rs = ROOT / "results" / "runs.rescored.jsonl"
for line in (_rs if _rs.exists() else ROOT / "results" / "runs.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    latest[(r["model"], r["id"], r["variant"], r["ctx"], r["rep"])] = r

by = defaultdict(list)
for r in latest.values():
    by[r["model"]].append(r)


def rate(rows, key):
    rows = [x for x in rows if key in x.get("result", {})]
    return (sum(bool(x["result"][key]) for x in rows), len(rows))


def fmt(t):
    return f"{t[0]}/{t[1]}" if t[1] else "-"


out = ["| Model | Code+debug pass | Recall pass | Fact known | Abstain (fake) | Refused (of 5) | Hedges avg | gen tok/s | processor | errors |", "|---|---|---|---|---|---|---|---|---|---|"]
for m, rows in sorted(by.items()):
    base = [x for x in rows if x["variant"] == "none"]
    code = [x for x in base if x["suite"] in ("code", "debug")]
    rec = [x for x in base if x["suite"] == "context"]
    fk = [x for x in base if x["id"] == "F1-known-fact"]
    ab = [x for x in base if x["suite"] == "factuality" and x["id"] != "F1-known-fact"]
    rf = [x for x in base if x["suite"] == "refusal"]
    hedges = [x["result"].get("hedges", 0) for x in rf if "result" in x]
    tps = [x["gen_tps"] for x in base if x.get("gen_tps")]
    ps = next((x["ps"] for x in base if x.get("ps")), "")
    proc = " ".join(ps.split()[-6:-3]) if ps else ""
    errs = sum(1 for x in rows if "error" in x)
    out.append(f"| {m} | {fmt(rate(code,'pass'))} | {fmt(rate(rec,'pass'))} | {fmt(rate(fk,'pass'))} | {fmt(rate(ab,'abstained'))} | {fmt(rate(rf,'refused'))} | {sum(hedges)/len(hedges):.1f} | {sum(tps)/len(tps):.1f} | {proc} | {errs} |" if tps else f"| {m} | no data | | | | | | | | {errs} |")

out += ["", "## Variant effect on factuality abstention (fake prompts) and refusals", "| Model | variant | abstained | refused |", "|---|---|---|---|"]
for m, rows in sorted(by.items()):
    for v in ("none", "grounded", "context"):
        vr = [x for x in rows if x["variant"] == v]
        a = rate([x for x in vr if x["suite"] == "factuality" and x["id"] != "F1-known-fact"], "abstained")
        f = rate([x for x in vr if x["suite"] == "refusal"], "refused")
        out.append(f"| {m} | {v} | {fmt(a)} | {fmt(f)} |")
(ROOT / "results" / "summary.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
