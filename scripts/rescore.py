"""Re-score stored responses with the current checkers -> results/runs.rescored.jsonl (originals untouched).
Only text-based checks are re-run (abstain, refusal, contains); code/terraform results are kept as recorded.
Run without -I:  python rescore.py
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_bench as rb  # noqa: E402

ROOT = HERE.parent
cfg = json.loads((ROOT / "prompts" / "prompts.json").read_text(encoding="utf-8"))
spec = {p["id"]: p["check"] for p in cfg["prompts"] if p.get("check")}
n = changed = 0
with (ROOT / "results" / "runs.rescored.jsonl").open("w", encoding="utf-8") as out:
    for line in (ROOT / "results" / "runs.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        s = spec.get(r["id"])
        if s and s["type"] in ("abstain", "refusal", "contains") and "response" in r:
            new = rb.check(s, r["response"])
            n += 1
            if new != r.get("result"):
                changed += 1
                r["result_original"] = r.get("result")
                r["result"] = new
                r["rescored"] = True
        out.write(json.dumps(r) + "\n")
print(f"rescored {n} text-checked runs, {changed} changed")
