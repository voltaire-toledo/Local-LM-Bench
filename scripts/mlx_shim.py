"""Ollama-compatible subset over mlx-lm, so the same runners measure MLX builds (schema v3, TASK-3/TASK-4).

Run with the mlx venv:  HF_HOME=.local/hf .local/mlx-venv/bin/python -I scripts/mlx_shim.py
Then run any runner with BENCH_RUNTIME=mlx-lm. Endpoints: /api/version, /api/tags, /api/ps, POST /api/chat (stream false, tools supported via mlx-lm tool parsers;
gpt-oss harmony calls parsed here).
Differences from Ollama, recorded on purpose: MLX has no preallocated context, so num_ctx only truncates the prompt
(oldest tokens dropped, as Ollama does); prompts longer than num_ctx are reported via prompt_eval_count.
Failures return HTTP 500 with JSON {"error": "..."}.
"""
import json, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import mlx.core as mx
import mlx_lm
from huggingface_hub import model_info, snapshot_download
from mlx_lm import load, stream_generate
from mlx_lm.sample_utils import make_sampler

PORT = 11435
# alias -> (repo, revision, quant label, params). Aliases keep the GGUF family prefix so runner rules (gpt-oss) still apply.
MODELS = {
    "qwen3.5:9b-mlx-4bit": ("mlx-community/Qwen3.5-9B-4bit", "8b2b98c00a6b4d291155e4890773ca8f769aee53", "MLX 4-bit", "9.7B"),
    "gemma4:12b-it-mlx-4bit": ("mlx-community/gemma-4-12B-it-4bit", "73bcf09092aa277861d5a191b989b666f7f32e8f", "MLX 4-bit", "12B"),
    "gpt-oss:20b-mlx-mxfp4": ("mlx-community/gpt-oss-20b-MXFP4-Q8", "773a7da77e569019bb0fd17a554b263738d669a3", "MXFP4 experts, Q8 rest", "20.9B"),
}
_cur = {"name": None, "model": None, "tok": None, "sha": {}}


def sha(name):
    if name not in _cur["sha"]:
        repo, rev = MODELS[name][:2]
        try:
            _cur["sha"][name] = rev or model_info(repo).sha
        except Exception:
            _cur["sha"][name] = rev or "unknown"
    return _cur["sha"][name]


def get(name):
    if _cur["name"] != name:
        _cur.update(name=None, model=None, tok=None)
        mx.clear_cache()
        repo = MODELS[name][0]
        t0 = time.time()
        path = snapshot_download(repo, revision=sha(name), local_files_only=True)
        _cur["model"], _cur["tok"] = load(path)
        _cur["name"], _cur["load_s"] = name, time.time() - t0
        mx.reset_peak_memory()
        return time.time() - t0
    return 0.0


def final_text(name, text):
    if name.startswith("gpt-oss"):
        m = re.search(r"<\|channel\|>final<\|message\|>(.*?)(?:<\|return\|>|<\|end\|>|$)", text, re.S)
        thinking = re.search(r"<\|channel\|>analysis<\|message\|>(.*?)<\|end\|>", text, re.S)
        return (m.group(1) if m else ""), (thinking.group(1) if thinking else text if not m else "")
    t = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S)
    return t.strip(), ""


def norm_msgs(msgs):
    """Ollama message shapes -> Hugging Face chat-template shapes (tool_name -> name, typed tool_calls)."""
    out = []
    for m in msgs:
        m = dict(m)
        if m.get("role") == "tool" and "tool_name" in m:
            m["name"] = m.pop("tool_name")
        if m.get("tool_calls"):
            m["tool_calls"] = [{"type": "function", "function": {"name": c["function"]["name"], "arguments": c["function"].get("arguments", {})}} for c in m["tool_calls"]]
        out.append(m)
    return out


def tool_calls(name, tok, text, tools):
    """Parse tool calls out of raw output. Returns (content_without_calls, [ollama-style calls])."""
    calls = []
    if name.startswith("gpt-oss"):  # harmony: <|channel|>commentary to=functions.NAME ... <|message|>{json}<|call|>
        for fn, args in re.findall(r"to=functions\.([\w-]+)[^<]*(?:<\|constrain\|>\w+)?<\|message\|>(.*?)(?:<\|call\|>|<\|end\|>|$)", text, re.S):  # <|call|> is a stop token, often absent
            try:
                calls.append({"function": {"name": fn, "arguments": json.loads(args)}})
            except Exception:
                calls.append({"function": {"name": fn, "arguments": {"_raw": args}}})
        return text, calls
    if not getattr(tok, "has_tool_calling", False):
        return text, calls
    a, b = re.escape(tok.tool_call_start), re.escape(tok.tool_call_end or "")
    for seg in re.findall(a + "(.*?)" + (b if b else "$"), text, re.S):
        try:
            got = tok.tool_parser(seg.strip(), tools)
        except Exception as e:
            got = {"name": "_unparsed", "arguments": {"_raw": seg.strip()[:500], "_error": str(e)}}
        for g in (got if isinstance(got, list) else [got]):
            args = g.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {"_raw": args}
            calls.append({"function": {"name": g.get("name"), "arguments": args}})
    return re.sub(a + ".*?" + (b if b else "$"), "", text, flags=re.S), calls


def chat(body):
    name = body["model"]
    if name not in MODELS:
        raise ValueError(f"unknown model {name}")
    o = body.get("options", {})
    load_s = get(name)
    tok = _cur["tok"]
    kw = {"reasoning_effort": "low"} if name.startswith("gpt-oss") else {"enable_thinking": bool(body.get("think"))}
    tools = body.get("tools")
    if tools:
        kw["tools"] = tools
    ids = tok.apply_chat_template(norm_msgs(body["messages"]), add_generation_prompt=True, **kw)
    if isinstance(ids, str):
        ids = tok.encode(ids)
    n_ctx, n_pred = int(o.get("num_ctx", 4096)), int(o.get("num_predict", 512))
    if len(ids) > n_ctx:
        ids = ids[-n_ctx:]
    mx.random.seed(int(o.get("seed", 0)))
    sampler = make_sampler(temp=float(o.get("temperature", 0)))
    text, last = "", None
    for r in stream_generate(_cur["model"], tok, ids, max_tokens=n_pred, sampler=sampler):
        text += r.text
        last = r
    text, calls = tool_calls(name, tok, text, tools) if tools else (text, [])
    content, thinking = final_text(name, text)
    pt, gt = last.prompt_tokens, last.generation_tokens
    return {"model": name, "message": {"role": "assistant", "content": content, "thinking": thinking, **({"tool_calls": calls} if calls else {})}, "done": True,
            "done_reason": "length" if last.finish_reason == "length" else "stop",
            "load_duration": int(load_s * 1e9), "prompt_eval_count": pt, "prompt_eval_duration": int(pt / last.prompt_tps * 1e9) if last.prompt_tps else 0,
            "eval_count": gt, "eval_duration": int(gt / last.generation_tps * 1e9) if last.generation_tps else 0, "peak_gb": round(last.peak_memory, 2)}


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/api/version":
            return self._send(200, {"version": f"mlx-lm {mlx_lm.__version__} / mlx {mx.__version__}"})
        if self.path == "/api/tags":
            return self._send(200, {"models": [{"name": n, "digest": sha(n), "details": {"quantization_level": q, "parameter_size": p}} for n, (_, _, q, p) in MODELS.items()]})
        if self.path == "/api/ps":
            return self._send(200, {"model": _cur["name"], "peak_gb": round(mx.get_peak_memory() / 1e9, 2)})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path != "/api/chat" or body.get("stream"):
                return self._send(400, {"error": "only POST /api/chat with stream false"})
            mx.reset_peak_memory()
            self._send(200, chat(body))
        except Exception as e:
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    srv.daemon_threads = True
    print(json.dumps({"status": "ready", "port": PORT}), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
