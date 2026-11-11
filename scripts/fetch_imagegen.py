"""Download the image-generation tools and models into .local/imagegen (git-ignored), verifying SHA-256.

Sources: Hugging Face (hash from the repo's LFS metadata) and the stable-diffusion.cpp GitHub release (hash from the
release asset digest). Resumable. Writes models/image-gen-files.json with what was fetched.
Gated repos are not used: where a VAE lives in a gated repo, an identical ungated mirror is used (same SHA-256).
"""
import hashlib, json, sys, time, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / ".local" / "imagegen"
UA = {"User-Agent": "local-lm-bench"}

HF = [
    ("leejet/Z-Image-Turbo-GGUF", "z_image_turbo-Q8_0.gguf", "models/diffusion"),
    ("Comfy-Org/z_image_turbo", "split_files/vae/ae.safetensors", "models/vae/z_image_ae.safetensors"),
    ("unsloth/Qwen3-4B-Instruct-2507-GGUF", "Qwen3-4B-Instruct-2507-Q4_K_M.gguf", "models/llm"),
    ("leejet/FLUX.2-klein-4B-GGUF", "flux-2-klein-4b-Q8_0.gguf", "models/diffusion"),
    ("Comfy-Org/flux2-klein-4B", "split_files/vae/flux2-vae.safetensors", "models/vae/flux2_ae.safetensors"),
    ("unsloth/Qwen3-4B-GGUF", "Qwen3-4B-Q4_K_M.gguf", "models/llm"),
    ("stabilityai/stable-diffusion-xl-base-1.0", "sd_xl_base_1.0.safetensors", "models/checkpoints"),
]


def get_json(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, size, sha):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == size and sha256_of(dest) == sha:
        print("  already present, hash ok", flush=True)
        return
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(url, headers={**UA, **({"Range": f"bytes={have}-"} if have else {})})
    with urllib.request.urlopen(req, timeout=120) as r, open(part, "ab" if have else "wb") as f:
        done, t0, last = have, time.time(), 0
        while True:
            chunk = r.read(8 * 1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if time.time() - last > 30:
                last = time.time()
                print(f"  {done/1e9:.2f}/{size/1e9:.2f} GB", flush=True)
    got = sha256_of(part)
    if got != sha:
        raise SystemExit(f"HASH MISMATCH for {dest.name}: expected {sha[:12]} got {got[:12]}")
    part.replace(dest)
    print("  verified", sha[:12], flush=True)


def main():
    manifest = []
    rel = get_json("https://api.github.com/repos/leejet/stable-diffusion.cpp/releases/latest")
    for a in rel["assets"]:
        if a["name"].startswith("sd-master") and "win-cuda12-x64" in a["name"] or a["name"].startswith("cudart-sd-bin-win-cu12"):
            print("GitHub:", a["name"], flush=True)
            dest = BASE / "downloads" / a["name"]
            sha = a["digest"].split(":", 1)[1]
            download(a["browser_download_url"], dest, a["size"], sha)
            with zipfile.ZipFile(dest) as z:
                z.extractall(BASE / "bin")
            manifest.append({"source": f"github.com/leejet/stable-diffusion.cpp {rel['tag_name']}", "file": a["name"], "size": a["size"], "sha256": sha})
    for repo, file, dest_rel in HF:
        info = get_json(f"https://huggingface.co/api/models/{repo}?blobs=true")
        if info.get("gated"):
            raise SystemExit(f"{repo} is gated; refusing")
        s = next(x for x in info["siblings"] if x["rfilename"] == file)
        sha, size = s["lfs"]["sha256"], s["size"]
        dest = BASE / dest_rel
        if dest_rel.startswith("models/") and "." not in Path(dest_rel).name:
            dest = dest / Path(file).name
        print(f"HF: {repo}/{file} ({size/1e9:.2f} GB)", flush=True)
        download(f"https://huggingface.co/{repo}/resolve/main/{file}", dest, size, sha)
        manifest.append({"source": f"huggingface.co/{repo}", "file": file, "size": size, "sha256": sha, "license": (info.get("cardData") or {}).get("license")})
    (ROOT / "models" / "image-gen-files.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
