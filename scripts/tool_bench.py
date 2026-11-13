"""Tool-calling benchmark for Ollama models. Appends to results/toolruns.jsonl.

Usage: python -I tool_bench.py --models a,b [--ctx 16384] [--only TC1,TC4] [--variant none|grounded]

Safety: file tools are confined to a per-run scratch dir; run_python executes in that dir with
python -I and a 10 s timeout; run_shell runs inside WSL with a command whitelist; there is no
delete, network or purchase tool. Every call is logged.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HOST = bench_env.API  # BENCH_RUNTIME=mlx-lm switches to scripts/mlx_shim.py
MAX_STEPS = 8

TOOLS = [
    {"type": "function", "function": {"name": "list_dir", "description": "List files in a directory (relative path, '.' for root).",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a UTF-8 text file by relative path.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write text to a file by relative path (creates folders).",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run_python", "description": "Run a python file from the working dir and return stdout/stderr.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "calculator", "description": "Evaluate an arithmetic expression using + - * / ( ) and numbers.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "search_docs", "description": "Search the internal documentation index. Returns matching snippets or 'NO RESULTS'.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "run_shell", "description": "Run a read-only Linux command in the working dir (WSL). Allowed: grep wc sort uniq head tail cat ls, pipes allowed.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
]
TOOL_PROPS = {t["function"]["name"]: (t["function"]["parameters"]["required"], t["function"]["parameters"]["properties"]) for t in TOOLS}

DOCS = {"azure policy": "Azure Policy evaluates resources against rules; effects include Audit, Deny, Modify, DeployIfNotExists.",
        "landing zone": "Azure landing zones use a management group hierarchy: Tenant Root > Platform (Identity, Management, Connectivity) and Landing Zones (Corp, Online)."}


def api(body, timeout=900):
    req = urllib.request.Request(HOST + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def safe(wd, rel):
    p = (wd / rel).resolve()
    if wd.resolve() not in p.parents and p != wd.resolve():
        raise ValueError("path escapes sandbox")
    return p


def exec_tool(wd, name, args):
    try:
        if name == "list_dir":
            return "\n".join(sorted(x.name + ("/" if x.is_dir() else "") for x in safe(wd, args["path"]).iterdir()))
        if name == "read_file":
            return safe(wd, args["path"]).read_text(encoding="utf-8")[:6000]
        if name == "write_file":
            p = safe(wd, args["path"]); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(args["content"], encoding="utf-8")
            return f"wrote {len(args['content'])} chars to {args['path']}"
        if name == "run_python":
            r = subprocess.run([sys.executable, "-I", str(safe(wd, args["path"]))], cwd=wd, capture_output=True, timeout=10, text=True)
            return f"exit={r.returncode}\nstdout:\n{r.stdout[-1500:]}\nstderr:\n{r.stderr[-1500:]}"
        if name == "calculator":
            if not re.fullmatch(r"[0-9+\-*/(). ]+", args["expression"]):
                return "ERROR: invalid expression"
            return str(eval(args["expression"], {"__builtins__": {}}))  # noqa - charset-restricted
        if name == "search_docs":
            q = args["query"].lower()
            hits = [v for k, v in DOCS.items() if k in q]
            return "\n".join(hits) if hits else "NO RESULTS"
        if name == "run_shell":
            cmd = args["command"]
            if re.search(r"[;&><`$\\]|\$\(", cmd):
                return "ERROR: disallowed characters"
            for seg in cmd.split("|"):
                if seg.strip().split(" ")[0] not in ("grep", "wc", "sort", "uniq", "head", "tail", "cat", "ls"):
                    return "ERROR: command not allowed"
            if sys.platform == "win32":
                r = subprocess.run(["wsl.exe", "--cd", str(wd), "-e", "bash", "-c", cmd], capture_output=True, timeout=30, text=True)
            else:  # macOS or Linux: run the same allowlisted command in the sandbox folder
                r = subprocess.run(["bash", "-c", cmd], cwd=str(wd), capture_output=True, timeout=30, text=True)
            return (r.stdout + r.stderr)[-1500:] or "(no output)"
    except KeyError as e:
        return f"ERROR: missing argument {e}"
    except Exception as e:  # noqa
        return f"ERROR: {e}"
    return f"ERROR: unknown tool {name}"


def validate(call):
    fn = call.get("function", {}); name = fn.get("name"); args = fn.get("arguments", {})
    if name not in TOOL_PROPS:
        return "unknown_tool"
    req, props = TOOL_PROPS[name]
    if not isinstance(args, dict) or any(k not in args for k in req):
        return "bad_args"
    if any(k not in props for k in args):
        return "extra_args"
    return "ok"


BUGGY = "def avg(xs):\n    return sum(xs) / (len(xs) + 1)\n\nif __name__ == '__main__':\n    print(avg([2, 4, 6]))\n"

TASKS = [
    {"id": "TC1-select", "prompt": "Use a tool to compute 1234 * 5678 and tell me the result.",
     "check": lambda c, f, wd: any(x["name"] == "calculator" and re.sub(r"\s", "", x["args"].get("expression", "")) in ("1234*5678",) for x in c) and "7006652" in f.replace(",", "")},
    {"id": "TC2-no-tool", "prompt": "What is the capital of France? Answer from your own knowledge.",
     "check": lambda c, f, wd: not c and "Paris" in f},
    {"id": "TC3-write-exact", "prompt": "Create the file notes/todo.txt containing exactly this text: buy milk; call dentist",
     "check": lambda c, f, wd: (wd / "notes" / "todo.txt").exists() and (wd / "notes" / "todo.txt").read_text().strip() == "buy milk; call dentist"},
    {"id": "TC4-chain-read", "setup": {"data/report.txt": "Quarterly report\nServer count: 42\nOwner: Dana\n"},
     "prompt": "Find the file in the data folder and tell me the server count.",
     "check": lambda c, f, wd: [x["name"] for x in c][:2] == ["list_dir", "read_file"] and "42" in f},
    {"id": "TC5-error-recovery", "setup": {"config.yml": "port: 8443\n"},
     "prompt": "Read config.yaml and tell me the port.",
     "check": lambda c, f, wd: "8443" in f and any(x["name"] == "read_file" and x["args"].get("path") == "config.yml" for x in c)},
    {"id": "TC6-faithful-empty", "prompt": "Search the docs for 'Azure Quantum Gateway' and summarize what it says.",
     "check": lambda c, f, wd: any(x["name"] == "search_docs" for x in c) and bool(re.search(r"no results|not found|no (matching|relevant)|couldn'?t find|didn'?t (find|return)|does not|doesn'?t", f, re.I)) and "quantum gateway is" not in f.lower()},
    {"id": "TC7-fix-and-run", "setup": {"avg.py": BUGGY},
     "prompt": "avg.py should compute the mean of a list but prints 3.0 for [2,4,6] when it should print 4.0. Fix the bug, run it, and confirm the output.",
     "check": lambda c, f, wd: "4.0" in subprocess.run([sys.executable, "-I", str(wd / "avg.py")], cwd=wd, capture_output=True, text=True, timeout=10).stdout and any(x["name"] == "run_python" for x in c)},
    {"id": "TC8-missing-tool", "prompt": "Send an email to dana@example.com saying the report is ready.",
     "check": lambda c, f, wd: all(x["name"] in TOOL_PROPS for x in c) and not any(x["name"] == "write_file" for x in c) and bool(re.search(r"can['’]?t|cannot|unable|no (tool|email)|don['’]?t have|not able|do not have|not (have )?(the )?(ability|capab)", f, re.I))},
    {"id": "TC9-wsl-shell", "setup": {"log.txt": "ok\nERROR disk\nok\nERROR net\nERROR disk\n"},
     "prompt": "How many lines in log.txt contain ERROR? Use the shell tool.",
     "check": lambda c, f, wd: any(x["name"] == "run_shell" for x in c) and re.search(r"\b3\b", f) is not None},
]

VARIANTS = {"none": "", "grounded": "You are an agent with tools. Use a tool when it is needed, never invent tool results, and say so plainly if a tool returns nothing or you lack a suitable tool."}


def run_task(model, task, ctx, variant):
    wd = Path(tempfile.mkdtemp(prefix="toolbench_"))
    try:
        for rel, txt in task.get("setup", {}).items():
            p = wd / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt, encoding="utf-8")
        msgs = ([{"role": "system", "content": VARIANTS[variant]}] if VARIANTS[variant] else []) + [{"role": "user", "content": task["prompt"]}]
        calls, valid, steps, toks, final, err = [], [], 0, 0, "", None
        t0 = time.time()
        while steps < MAX_STEPS:
            steps += 1
            r = api({"model": model, "messages": msgs, "tools": TOOLS, "stream": False, "think": False,
                     "options": {"num_ctx": ctx, "temperature": 0, "num_predict": 1500}})
            m = r["message"]; toks += r.get("eval_count", 0)
            msgs.append({k: v for k, v in m.items() if k in ("role", "content", "tool_calls")})
            tcs = m.get("tool_calls") or []
            if not tcs:
                final = m.get("content", ""); break
            for tc in tcs:
                v = validate(tc); valid.append(v)
                name = tc["function"]["name"]; args = tc["function"].get("arguments", {}) if isinstance(tc["function"].get("arguments", {}), dict) else {}
                calls.append({"name": name, "args": args})
                msgs.append({"role": "tool", "tool_name": name, "content": exec_tool(wd, name, args)})
        else:
            err = "max_steps"
        try:
            ok = bool(task["check"](calls, final, wd))
        except Exception as e:  # noqa
            ok, err = False, f"check_error {e}"
        return {"pass": ok, "steps": steps, "calls": calls, "validity": valid, "tokens": toks, "secs": round(time.time() - t0, 1), "final": final[:3000], "err": err, "prompt_tokens_last": r.get("prompt_eval_count"), "done_reason": r.get("done_reason")}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")[:200]
        return {"pass": False, "err": f"http {e.code}: {body}", "no_tool_support": "tool" in body.lower()}
    finally:
        shutil.rmtree(wd, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True); ap.add_argument("--ctx", type=int, default=16384)
    ap.add_argument("--only", default=""); ap.add_argument("--variant", default="none")
    a = ap.parse_args()
    only = [x for x in a.only.split(",") if x]
    out = ROOT / "results" / "toolruns.jsonl"
    for model in a.models.split(","):
        for t in TASKS:
            if only and not any(t["id"].startswith(o) for o in only):
                continue
            res = run_task(model, t, a.ctx, a.variant)
            rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "id": t["id"], "variant": a.variant, "ctx": a.ctx, "env": bench_env.static_env(model), "split": bench_env.ps_split(model), **res}
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            print(model, t["id"], "PASS" if res["pass"] else "FAIL", res.get("steps"), res.get("validity"), res.get("err") or "", flush=True)
            if res.get("no_tool_support"):
                break
        subprocess.run(["ollama", "stop", model], capture_output=True)


if __name__ == "__main__":
    main()
