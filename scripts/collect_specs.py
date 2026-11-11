"""Collect hardware-independent model specs from Ollama /api/show -> models/specs.json.

Records architecture facts that decide memory use (layers, KV heads, head size, sliding window, experts, SSM),
advertised context length, capabilities, license and default parameters, plus derived KV-cache figures.
"""
import json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def post(path, body):
    req = urllib.request.Request("http://localhost:11434" + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


tags = json.load(urllib.request.urlopen("http://localhost:11434/api/tags", timeout=10))["models"]
out = {"schema": 1, "source": "ollama /api/show", "models": {}}
for t in tags:
    m = t["name"]
    try:
        s = post("/api/show", {"model": m})
    except Exception as e:
        out["models"][m] = {"error": str(e)[:120]}
        continue
    mi = s.get("model_info", {})
    arch = mi.get("general.architecture")
    g = lambda suf: mi.get(f"{arch}.{suf}") if arch else None
    layers = g("block_count")
    kv = g("attention.head_count_kv")
    heads = g("attention.head_count")
    emb = g("embedding_length")
    klen = g("attention.key_length")
    if isinstance(kv, int):
        kv = [kv] * (layers or 0)
    hd = klen or ((emb // (max(heads) if isinstance(heads, list) else heads)) if emb and heads else None)
    attn_layers = sum(1 for x in (kv or []) if x) if kv else None
    kv_bytes_upper = sum(x * hd * 4 for x in kv if x) if kv and hd else None  # K+V, 2 bytes each (f16), all attention layers full-length
    lic = (s.get("license") or "").strip().splitlines()
    params = {}
    for line in (s.get("parameters") or "").splitlines():
        p = line.split(None, 1)
        if len(p) == 2:
            params.setdefault(p[0], []).append(p[1].strip())
    out["models"][m] = {
        "architecture": arch, "family": s.get("details", {}).get("family"), "parameters": s.get("details", {}).get("parameter_size"),
        "quantization": s.get("details", {}).get("quantization_level"), "format": s.get("details", {}).get("format"),
        "size_gb": round(t["size"] / 1e9, 1), "digest": t["digest"][:12], "modified": t.get("modified_at"),
        "capabilities": s.get("capabilities"), "context_length_advertised": g("context_length"),
        "layers": layers, "attention_layers": attn_layers, "attention_heads": heads, "kv_heads": kv if not isinstance(kv, list) or len(set(kv)) > 1 else kv[0],
        "head_dim": hd, "embedding_length": emb, "sliding_window": g("attention.sliding_window"),
        "experts_total": g("expert_count"), "experts_active": g("expert_used_count"), "ssm_state": g("ssm.state_size"),
        "kv_kb_per_token_f16_upper_bound": round(kv_bytes_upper / 1024, 1) if kv_bytes_upper else None,
        "kv_note": "Upper bound assuming every attention layer caches the full context; sliding-window layers need far less.",
        "license_first_line": lic[0][:120] if lic else None, "default_params": params or None,
        "has_system_prompt_in_modelfile": bool(re.search(r"^SYSTEM\s", s.get("modelfile", ""), re.M)),
    }
(ROOT / "models" / "specs.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(f"{len(out['models'])} models -> models/specs.json")
for m, v in out["models"].items():
    print(f"{m[:34]:35} arch={v.get('architecture')} ctx={v.get('context_length_advertised')} layers={v.get('layers')} attnL={v.get('attention_layers')} experts={v.get('experts_active')}/{v.get('experts_total')} swa={v.get('sliding_window')} kvKB/tok<={v.get('kv_kb_per_token_f16_upper_bound')} cap={v.get('capabilities')} sys={v.get('has_system_prompt_in_modelfile')}")
