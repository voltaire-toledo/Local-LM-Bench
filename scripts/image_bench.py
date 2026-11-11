"""Image-generation tests (suites/images.json). Appends to results/images.jsonl; keeps small copies in results/images/.

Tests: logo-png (green-key cutout metrics), logo-svg (text models write SVG, validated), carousel (5 slides, headline read back by a
vision model), folder-icon (FLUX.2 klein reference edit of a generated logo, checked at 256/64/32 px). Full-size outputs stay in
.local/imagegen/out (git-ignored). Usage: python image_bench.py --models zimage,flux2klein,sdxl --tests logo-png,carousel,folder-icon
       python image_bench.py --tests logo-svg --svg-models gemma4:12b-it-q4_K_M,...
"""
import argparse, base64, difflib, io, json, re, subprocess, sys, time, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_env as be  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / ".local" / "imagegen"
EXE = B / "bin" / "sd-cli.exe"
OUT = ROOT / "results" / "images.jsonl"
KEEP = ROOT / "results" / "images"
SPEC = json.loads((ROOT / "suites" / "images.json").read_text(encoding="utf-8"))
TASKS = {t["id"]: t for t in SPEC["tasks"]}
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
M = B / "models"
CFG = {
    "zimage": ["--diffusion-model", str(M / "diffusion/z_image_turbo-Q8_0.gguf"), "--vae", str(M / "vae/z_image_ae.safetensors"), "--llm", str(M / "llm/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"), "--cfg-scale", "1.0", "--steps", "8", "--offload-to-cpu"],
    "flux2klein": ["--diffusion-model", str(M / "diffusion/flux-2-klein-4b-Q8_0.gguf"), "--vae", str(M / "vae/flux2_ae.safetensors"), "--llm", str(M / "llm/Qwen3-4B-Q4_K_M.gguf"), "--cfg-scale", "1.0", "--steps", "4", "--offload-to-cpu"],
    "sdxl": ["-m", str(M / "checkpoints/sd_xl_base_1.0.safetensors"), "--cfg-scale", "7", "--steps", "25"],
}


def log(rec):
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    print(rec.get("kind"), rec.get("model"), rec.get("name"), rec.get("ok"), rec.get("secs"), rec.get("error", ""), flush=True)


def keep_thumb(img_path, rel, mode="JPEG"):
    dst = KEEP / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(img_path)
    im.thumbnail((384, 384))
    if mode == "JPEG":
        im.convert("RGB").save(dst.with_suffix(".jpg"), quality=80)
    else:
        im.save(dst.with_suffix(".png"))


def gen(model, prompt, out, seed, w=1024, h=1024, ref=None):
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(EXE), *CFG[model], "-p", prompt, "-W", str(w), "-H", str(h), "-s", str(seed), "-o", str(out)]
    if ref:
        cmd += ["-r", str(ref)]
    th0 = be.throttle_counters()
    t0 = time.time()
    try:
        with be.PowerSampler(0.5) as ps:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        secs = time.time() - t0
        s = ps.summary()
        return {"ok": out.exists() and r.returncode == 0, "secs": round(secs, 1), "power_avg_w": s.get("power_avg_w"), "vram_peak_mib": s.get("vram_peak_mib"),
                "j_per_image": round(s.get("power_avg_w", 0) * secs) if s else None, "stderr": None if out.exists() else r.stderr[-300:]}
    except Exception as e:  # noqa
        return {"ok": False, "secs": round(time.time() - t0, 1), "stderr": str(e)[:200]}


def cutout(src, dst):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    px = list(im.getdata())
    out, keys = [], []
    for r, g, b in px:
        key = g - max(r, b)
        keys.append(key)
        a = 0 if key >= 90 else 255 if key <= 30 else int(255 * (90 - key) / 60)
        if key > 0:
            g = min(g, max(r, b))
        out.append((r, g, b, a))
    res = Image.new("RGBA", (w, h))
    res.putdata(out)
    res.save(dst)
    n = w * h
    bm = max(1, int(min(w, h) * 0.05))
    border = [i for i in range(n) if (i % w) < bm or (i % w) >= w - bm or (i // w) < bm or (i // w) >= h - bm]
    bg_clean = sum(1 for i in border if out[i][3] == 0) / len(border)
    bg_green = sorted(keys[i] for i in border)[len(border) // 2] > 90
    opaque = [i for i in range(n) if out[i][3] > 247]
    return {"bg_is_green": bg_green, "bg_clean": round(bg_clean, 3), "coverage": round(sum(1 for p in out if p[3] > 128) / n, 3),
            "edge_fraction": round(sum(1 for p in out if 8 < p[3] < 247) / max(1, len(opaque)), 3),
            "subject_green": round(sum(1 for i in opaque if keys[i] > 25) / max(1, len(opaque)), 4)}


FILT = {"brief": "", "seeds": 0}


def logo_png(models):
    t = TASKS["logo-png"]
    for model in models:
        for brief in [b for b in t["briefs"] if not FILT["brief"] or b["id"] == FILT["brief"]]:
            for seed in (t["seeds"][:FILT["seeds"]] if FILT["seeds"] else t["seeds"]):
                name = f"{brief['id']}-s{seed}"
                raw = B / "out" / "logo" / model / f"{name}.png"
                rec = {"kind": "logo-png", "model": model, "name": name, "suite_version": SPEC["version"], "env": be.static_env()}
                rec.update(gen(model, t["template"].format(brief=brief["brief"]), raw, seed))
                if rec["ok"]:
                    try:
                        cut = raw.with_name(name + "_cut.png")
                        m = cutout(raw, cut)
                        rec["metrics"] = m
                        rec["pass"] = bool(m["bg_is_green"] and m["bg_clean"] > 0.97 and 0.03 < m["coverage"] < 0.85 and m["subject_green"] < 0.02)
                        keep_thumb(cut, f"logo-png/{model}/{name}", "PNG")
                    except Exception as e:  # noqa
                        rec["error"] = str(e)[:200]
                log(rec)


def svg_check(text):
    m = re.search(r"```(?:svg|xml)?\n(.*?)```", text, re.S)
    svg = (m.group(1) if m else text).strip()
    c = {"size_bytes": len(svg.encode())}
    try:
        root = ET.fromstring(svg)
    except Exception as e:  # noqa
        return svg, {**c, "valid_xml": False, "error": str(e)[:80], "pass": False}
    tags = [e.tag.split("}")[-1].lower() for e in root.iter()]
    bad = [t for t in tags if t in ("image", "script", "foreignobject")]
    ext = any(str(v).startswith(("http", "data:")) for e in root.iter() for k, v in e.attrib.items() if k.endswith("href"))
    c.update({"valid_xml": True, "root_svg": root.tag.split("}")[-1].lower() == "svg", "viewbox": "viewBox" in root.attrib, "elements": len(tags), "forbidden": bad, "external": ext, "text_elements": tags.count("text")})
    c["pass"] = bool(c["root_svg"] and c["viewbox"] and not bad and not ext and 3 <= c["elements"] <= 90 and c["size_bytes"] < 20000)
    return svg, c


def logo_svg(models):
    t = TASKS["logo-svg"]
    for model in models:
        for brief in t["briefs"]:
            rec = {"kind": "logo-svg", "model": model, "name": brief["id"], "suite_version": SPEC["version"], "env": be.static_env(model)}
            t0 = time.time()
            try:
                body = {"model": model, "messages": [{"role": "user", "content": t["template"].format(brief=brief["brief"])}], "stream": False, "think": False,
                        "options": {"num_ctx": 16384, "temperature": 0, "seed": 1, "num_predict": 3000}}
                req = urllib.request.Request("http://localhost:11434/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
                r = json.load(urllib.request.urlopen(req, timeout=900))
                svg, chk = svg_check(r["message"]["content"])
                safe = re.sub(r"[^A-Za-z0-9._-]+", "_", model)
                p = KEEP / "logo-svg" / safe / f"{brief['id']}.svg"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(svg, encoding="utf-8")
                rec.update({"ok": True, "secs": round(time.time() - t0, 1), "gen_tps": round(r["eval_count"] / (r["eval_duration"] / 1e9), 1) if r.get("eval_duration") else None, "metrics": chk, "pass": chk["pass"], "path": str(p.relative_to(ROOT))})
                if chk.get("valid_xml") and Path(EDGE).exists():
                    try:
                        png = B / "out" / "svg" / safe / f"{brief['id']}.png"
                        png.parent.mkdir(parents=True, exist_ok=True)
                        subprocess.run([EDGE, "--headless=new", "--disable-gpu", f"--screenshot={png}", "--window-size=512,512", p.resolve().as_uri()], capture_output=True, timeout=60)
                        if png.exists():
                            im = Image.open(png).convert("L")
                            rec["metrics"]["render_nonwhite"] = round(sum(1 for v in im.getdata() if v < 240) / (im.width * im.height), 3)
                            keep_thumb(png, f"logo-svg/{safe}/{brief['id']}")
                    except Exception:
                        pass
            except Exception as e:  # noqa
                rec.update({"ok": False, "error": str(e)[:200], "secs": round(time.time() - t0, 1)})
            log(rec)
        subprocess.run(["ollama", "stop", model], capture_output=True)


def ocr(path, model="gemma4:12b-it-q4_K_M"):
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    body = {"model": model, "stream": False, "think": False, "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 100},
            "messages": [{"role": "user", "content": "Transcribe all the text in this image exactly as written. Return only the text.", "images": [b64]}]}
    req = urllib.request.Request("http://localhost:11434/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=600))["message"]["content"]


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def carousel(models):
    t = TASKS["carousel"]
    for model in models:
        paths = []
        for s in t["slides"]:
            raw = B / "out" / "carousel" / model / f"{s['id']}.png"
            rec = {"kind": "carousel", "model": model, "name": s["id"], "suite_version": SPEC["version"], "env": be.static_env()}
            rec.update(gen(model, t["template"].format(headline=s["headline"]), raw, 1, t["size"][0], t["size"][1]))
            if rec["ok"]:
                paths.append(raw)
                keep_thumb(raw, f"carousel/{model}/{s['id']}")
            log(rec)
        for s, raw in zip(t["slides"], paths):
            try:
                got = ocr(raw)
                ratio = round(difflib.SequenceMatcher(None, norm(s["headline"]), norm(got)).ratio(), 2)
                log({"kind": "carousel-ocr", "model": model, "name": s["id"], "ok": True, "expected": s["headline"], "read": got[:120], "match": ratio, "pass": ratio >= 0.9, "secs": None})
            except Exception as e:  # noqa
                log({"kind": "carousel-ocr", "model": model, "name": s["id"], "ok": False, "error": str(e)[:150]})
        subprocess.run(["ollama", "stop", "gemma4:12b-it-q4_K_M"], capture_output=True)
        if len(paths) >= 2:  # palette consistency across slides (smaller spread is better)
            avgs = [Image.open(p).convert("RGB").resize((1, 1)).getpixel((0, 0)) for p in paths]
            spread = round(max(max(a[i] for a in avgs) - min(a[i] for a in avgs) for i in range(3)) / 255, 3)
            log({"kind": "carousel-consistency", "model": model, "name": "palette", "ok": True, "palette_spread": spread})


def folder_icon(models):
    t = TASKS["folder-icon"]
    model = "flux2klein"  # the only installed model that supports reference-image editing
    if model not in models:
        return
    src = B / "out" / "logo" / model / "emblem-s1.png"
    if not src.exists():
        r = gen(model, TASKS["logo-png"]["template"].format(brief="an emblem logo of a lighthouse with simple rays"), src, 1)
        if not r["ok"]:
            log({"kind": "folder-icon", "model": model, "name": "derive", "ok": False, "error": "no source logo"})
            return
    out = B / "out" / "folder" / "folder_from_emblem.png"
    rec = {"kind": "folder-icon", "model": model, "name": "derive-from-emblem", "suite_version": SPEC["version"], "env": be.static_env()}
    rec.update(gen(model, t["template"], out, 1, ref=src))
    if rec["ok"]:
        im = Image.open(out).convert("RGB")
        sizes = {}
        for px in (256, 64, 32):
            s = im.resize((px, px), Image.LANCZOS)
            lum = [sum(p) / 3 for p in s.getdata()]
            mean = sum(lum) / len(lum)
            sizes[px] = round((sum((v - mean) ** 2 for v in lum) / len(lum)) ** 0.5, 1)  # contrast: very low means the icon turns to mush
        rec["metrics"] = {"luminance_contrast_by_px": sizes}
        keep_thumb(out, "folder-icon/folder_from_emblem")
        keep_thumb(src, "folder-icon/source_emblem")
    log(rec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="zimage,flux2klein,sdxl")
    ap.add_argument("--tests", default="logo-png,carousel,folder-icon")
    ap.add_argument("--svg-models", default="")
    ap.add_argument("--brief", default="")
    ap.add_argument("--max-seeds", type=int, default=0)
    a = ap.parse_args()
    FILT["brief"], FILT["seeds"] = a.brief, a.max_seeds
    ms, tests = a.models.split(","), a.tests.split(",")
    if "logo-png" in tests:
        logo_png(ms)
    if "carousel" in tests:
        carousel(ms)
    if "folder-icon" in tests:
        folder_icon(ms)
    if "logo-svg" in tests and a.svg_models:
        logo_svg(a.svg_models.split(","))


if __name__ == "__main__":
    main()
