"""Re-score stored AutoHotkey answers with the current harness (no model calls). Appends to results/suites.jsonl.

Needed once after the harness was changed to suppress error dialogs (#NoTrayIcon, #Warn All StdOut, OnError, dialog functions
neutralized): answers scored earlier could hang on a dialog until the timeout. Latest record per task wins in the exports.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import suite_runner as sr  # noqa: E402

spec = json.loads((sr.SUITES / "code-languages.json").read_text(encoding="utf-8"))
tasks = {t["id"]: t for t in spec["tasks"] if t["lang"] == "autohotkey"}
latest = {}
for line in sr.OUT.read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if r.get("suite") == "code-languages" and r.get("task") in tasks and r.get("response") is not None:
        latest[(r["model"], r["task"])] = r
n = 0
for (model, tid), r in latest.items():
    pts, mx, det = sr.run_code(tasks[tid], r["response"])
    new = {**r, "score": pts, "max": mx, "detail": det, "rescored": "ahk-harness-v2", "previous_score": r.get("score"), "previous_detail": r.get("detail")}
    with sr.OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(new) + "\n")
    n += 1
    print(f"{model:36} {tid:11} {r.get('score')} -> {pts}  {str(det)[:70]}")
print(n, "re-scored")
