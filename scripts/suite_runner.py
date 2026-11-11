"""Unified runner for the standard suites in suites/*.json. Appends to results/suites.jsonl.

Usage: python suite_runner.py --suite code-languages,consulting-cases --models a,b [--only go-] [--ctx 16384]
Scoring types: run_code (real execution, sandboxed temp dir, denylist guard), labels, checklist, case, planted.
Every record carries suite version + hash, environment (power limit, digest...), speed and split.
"""
import argparse, json, random, re, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SUITES = ROOT / "suites"
OUT = ROOT / "results" / "suites.jsonl"
AHK = next((p for p in (r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe", r"C:\Program Files\AutoHotkey\v2\AutoHotkey.exe") if Path(p).exists()), None)
DANGER = re.compile(r"(?i)(remove-item|\brmdir\b|\brd\s|\bdel\s|format-volume|invoke-(webrequest|restmethod|expression)|\biex\b|start-process|set-itemproperty|new-psdrive|downloadstring|os/exec|net/http|\"syscall\"|os\.remove|ioutil|std::process|std::fs|std::net|filedelete|dirdelete|\brun\(|runwait|dllcall|regwrite|regdelete|urldownloadtofile|\.exec\()")


def chat(model, prompt, d, timeout=900):
    oss = model.startswith("gpt-oss")  # reasoning cannot be switched off; use low effort and a larger output budget
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": "low" if oss else d.get("think", False),
            "options": {"num_ctx": d["num_ctx"], "temperature": d["temperature"], "seed": d["seed"], "num_predict": d["num_predict"] * (3 if oss else 1)}}
    req = urllib.request.Request("http://localhost:11434/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def code_of(text):
    m = re.search(r"```[\w+#-]*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip() + "\n"


def sh(cmd, cwd, timeout=90, env=None):
    import os
    e = {**os.environ, **(env or {})}
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=e, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def run_code(task, text):
    lang, code = task["lang"], code_of(text)
    if DANGER.search(code):
        return 0, 1, "blocked: unsafe pattern in generated code"
    with tempfile.TemporaryDirectory(prefix="suite_") as d:
        d = Path(d)
        try:
            if lang == "go":
                (d / "solution.go").write_text(code, encoding="utf-8"); (d / "harness.go").write_text(task["harness"], encoding="utf-8")
                sh(["go", "mod", "init", "t"], d, 30, {"GOTOOLCHAIN": "local"})
                r = sh(["go", "run", "."], d, 120, {"GOTOOLCHAIN": "local", "GOFLAGS": "-mod=mod"})
            elif lang == "rust":
                if not shutil.which("rustc"):
                    return None, 1, "skipped: rustc not installed"
                (d / "solution.rs").write_text(code, encoding="utf-8"); (d / "harness.rs").write_text(task["harness"], encoding="utf-8")
                c = sh(["rustc", "harness.rs", "-o", "t.exe"], d, 120)
                if c.returncode:
                    return 0, 1, "compile error: " + c.stderr[-300:]
                r = sh([str(d / "t.exe")], d, 30)
            elif lang == "powershell":
                (d / "solution.ps1").write_text(code, encoding="utf-8"); (d / "harness.ps1").write_text(task["harness"], encoding="utf-8")
                r = sh(["pwsh", "-NoProfile", "-NonInteractive", "-File", "harness.ps1"], d, 60)
            elif lang == "autohotkey":
                if not AHK:
                    return None, 1, "skipped: AutoHotkey v2 not installed"
                code = re.sub(r"(?im)^\s*#Requires.*\n", "", code)
                code = re.sub(r"\b(MsgBox|InputBox|ToolTip|TrayTip|FileSelect|DirSelect|Gui)\b", "NoOp", code)  # no dialogs or windows from generated code
                header = ("#Requires AutoHotkey v2.0\n#NoTrayIcon\n#Warn All, StdOut\n"
                          "OnError((e, mode) => (FileAppend(\"ERROR: \" e.Message \"`n\", \"*\"), ExitApp(2)))\n"
                          "NoOp(*) => \"\"\n")
                (d / "solution.ahk").write_text(code, encoding="utf-8"); (d / "harness.ahk").write_text(header + task["harness"], encoding="utf-8")
                r = sh([AHK, "/ErrorStdOut", "harness.ahk"], d, 30)
            else:
                return None, 1, f"unknown language {lang}"
        except subprocess.TimeoutExpired:
            return 0, 1, "timeout"
        out = (r.stdout + r.stderr).strip()
        ok = r.returncode == 0 and "OK" in r.stdout
        return (1 if ok else 0), 1, "ok" if ok else re.sub(r"\s+", " ", out)[-300:]


def first_json(text):
    t = re.sub(r"```(?:json)?", "", text)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


def score_labels(task, text):
    got = first_json(text) or {}
    wrong = [t["id"] for t in task["tickets"] if str(got.get(t["id"], "")).strip().lower() != t["label"]]
    return len(task["tickets"]) - len(wrong), len(task["tickets"]), {"wrong": wrong, "invalid": [k for k, v in got.items() if str(v).lower() not in task["labels"]][:8]}


def score_checklist(task, text):
    low = text.lower()
    hits = sum(1 for g in task["facts"] if any(s in low for s in g))
    bad = [p for p in task["forbidden"] if re.search(p, low)]
    words = len(text.split())
    pen = 2 * len(bad) + (1 if words > task["max_words"] * 1.25 else 0)
    return max(0, hits - pen), len(task["facts"]), {"facts_hit": hits, "forbidden": bad, "words": words}


def num_after(text, key):
    m = re.findall(re.escape(key) + r"\s*[:=]\s*\$?([\d,]*\.?\d+)", text)
    return float(m[-1].replace(",", "")) if m else None


def score_case(task, text):
    pts, mx, det = 0, 0, {}
    for c in task["checks"]:
        n = len(re.findall(c["re"], text, re.I | re.M))
        ok = n >= c["min"]
        pts += ok; mx += 1; det[c["name"]] = ok
    hit = sum(1 for g in task["frameworks"] if any(s in text.lower() for s in g))
    pts += min(3, hit); mx += 3; det["frameworks"] = hit
    if task.get("numeric"):
        v = num_after(text, task["numeric"]["pattern"])
        ok = v is not None and task["numeric"]["low"] <= v <= task["numeric"]["high"]
        pts += 3 if ok else 0; mx += 3; det["numeric"] = v
    return pts, mx, det


def make_planted(seed, weeks):
    rnd = random.Random(seed)
    regions = ("North", "East", "West")
    deploys = {w: rnd.randint(2, 12) for w in range(1, weeks + 1)}
    step = int(weeks * 0.6)
    rows = ["week,region,deploys,tickets,resolution_hours,csat,office_plants"]
    for w in range(1, weeks + 1):
        for r in regions:
            tickets = int(40 + 3 * deploys.get(w - 2, 6) + rnd.gauss(0, 4))
            res = 26 + rnd.gauss(0, 4)
            if r == "East" and w > step:
                res *= 2
            csat = 4.4 - (1.2 if res > 48 else 0) + rnd.gauss(0, 0.15)
            rows.append(f"{w},{r},{deploys[w]},{tickets},{res:.1f},{csat:.2f},{rnd.randint(0, 9)}")
    return "\n".join(rows)


PLANTED = {
    "lagged deploy effect": [r"deploy", r"ticket", r"(lag|later|after|following|two weeks|2 weeks|week[s]? (earlier|before|prior)|delay)"],
    "east step change": [r"east", r"(jump|step|doubl|increas|rise|spike|shift|jumped)", r"(week\s*\d+|after|from|since)"],
    "csat threshold": [r"csat|satisf", r"(threshold|48|above|exceed|over|longer|slow)"],
}


def score_planted(task, text):
    got = first_json(text)
    finds = got.get("findings", []) if isinstance(got, dict) else []
    blobs = [(str(f.get("claim", "")) + " " + str(f.get("evidence", ""))).lower() if isinstance(f, dict) else str(f).lower() for f in finds]
    found = {k: any(all(re.search(p, b) for p in pats) for b in blobs) for k, pats in PLANTED.items()}
    claims = [str(f.get("claim", "")).lower() for f in finds if isinstance(f, dict)]
    decoy = any("plant" in c and not re.search(r"\b(no|not|n't|unrelated|irrelevant|noise|without|nothing)\b", c) for c in claims)
    unmatched = sum(1 for b in blobs if not any(all(re.search(p, b) for p in pats) for pats in PLANTED.values()) )
    pts = max(0, sum(found.values()) - (1 if decoy else 0))
    return pts, 3, {"found": found, "claimed_decoy": decoy, "findings": len(blobs), "unmatched": unmatched}


def planted_prompt(task):
    data = make_planted(task["seed"], task["weeks"])
    return ("Below is weekly operations data for a support organization (CSV). Find the non-obvious patterns that the data actually supports. "
            "Only report patterns you are confident about, and say nothing about columns that carry no signal. Return only JSON: "
            '{"findings":[{"claim":"...","evidence":"..."}]}. If you find nothing reliable, return an empty list.\n\n' + data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--ctx", type=int, default=0)
    a = ap.parse_args()
    OUT.parent.mkdir(exist_ok=True)
    for model in a.models.split(","):
        for sname in a.suite.split(","):
            spec = json.loads((SUITES / f"{sname}.json").read_text(encoding="utf-8"))
            d = dict(spec["defaults"])
            if a.ctx:
                d["num_ctx"] = a.ctx
            for t in spec["tasks"]:
                if a.only and not t["id"].startswith(a.only):
                    continue
                prompt = planted_prompt(t) if t["type"] == "planted" else t["prompt"]
                rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "suite": sname, "version": spec["version"], "hash": spec["hash"], "task": t["id"], "model": model, "ctx": d["num_ctx"], "env": bench_env.static_env(model)}
                try:
                    t0 = time.time()
                    r = chat(model, prompt, d)
                    text = r.get("message", {}).get("content", "")
                    typ = t["type"]
                    pts, mx, det = (run_code(t, text) if typ == "run_code" else score_labels(t, text) if typ == "labels" else score_checklist(t, text) if typ == "checklist"
                                    else score_case(t, text) if typ == "case" else score_planted(t, text))
                    rec.update({"score": pts, "max": mx, "detail": det, "response": text[:20000], "secs": round(time.time() - t0, 1),
                                "gen_tps": round(r["eval_count"] / (r["eval_duration"] / 1e9), 1) if r.get("eval_duration") else None, "tokens": r.get("eval_count"),
                                "prompt_tokens": r.get("prompt_eval_count"), "done_reason": r.get("done_reason"), "empty": not text.strip(),
                                "split": bench_env.ps_split(model), "gpu": bench_env.gpu_now()})
                except Exception as e:  # noqa
                    rec["error"] = str(e)[:300]
                with OUT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
                print(model, sname, t["id"], rec.get("score"), "/", rec.get("max"), rec.get("error", ""), flush=True)
        subprocess.run(["ollama", "stop", model], capture_output=True)


if __name__ == "__main__":
    main()
