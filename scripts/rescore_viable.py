"""Re-score stored viable-context records with the v1.1 rule (retrieval of all three codes gates; the "largest" comparison is reported
separately; failure reason recorded). Expected codes are rebuilt from the same seed, so no model call is needed. Appends to results/viable.jsonl.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import viable_ctx as vc  # noqa: E402

OUT = vc.OUT
MIN_TPS, MAX_S = 15, 180
latest = {}
for line in OUT.read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    latest[(r["model"], r["ctx"])] = r
n = 0
for (model, ctx), r in latest.items():
    if "error" in r or r.get("rescored") == "v1.1" or "retrieval" in r:
        continue
    _, codes, largest = vc.build(ctx, seed=ctx)
    text = r.get("response", "")
    a, b = text.find("{"), text.rfind("}")
    try:
        got = json.loads(text[a:b + 1])
    except Exception:
        got = {}
    ret = sum(str(got.get(k.lower(), "")).strip() == v for k, v in codes.items())
    rea = int(str(got.get("largest", "")).lower().strip() == largest)
    tps, wall = r.get("gen_tps"), r.get("wall_s") or 0
    viable = bool(ret == 3 and not r.get("truncated") and tps and tps >= MIN_TPS and wall <= MAX_S)
    reason = None if viable else ("truncated" if r.get("truncated") else "recall" if ret < 3 else "too slow" if wall > MAX_S else "low tok/s")
    new = {**r, "retrieval": ret, "reasoning": rea, "viable": viable, "fail_reason": reason, "rescored": "v1.1", "previous_viable": r.get("viable")}
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(new) + "\n")
    n += 1
    print(f"{model[:44]:44} {ctx//1024:>4}k retrieval={ret}/3 reasoning={rea} viable {r.get('viable')} -> {viable} {reason or ''}")
print(n, "re-scored")
