"""Shared environment/power capture for all benchmark scripts."""
import hashlib, json, re, subprocess, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HW_ID = "win-rtx3060-12g"
HARNESS_VERSION = "2"  # bump when checkers or runners change
_digests = {}


def _smi(fields):
    try:
        out = subprocess.run(["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
        return [x.strip() for x in out.strip().split(",")]
    except Exception:
        return []


def gpu_now():
    v = _smi("power.draw,power.limit,temperature.gpu,clocks.gr,memory.used")
    try:
        return {"power_w": float(v[0]), "power_limit_w": float(v[1]), "temp_c": float(v[2]), "clock_mhz": float(v[3]), "vram_mib": float(v[4])}
    except Exception:
        return {}


def gpu_procs():
    """Other processes holding GPU memory (detects STT apps, browsers, etc. that skew results)."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"], capture_output=True, text=True, timeout=10).stdout
        return [x.strip() for x in out.strip().splitlines() if x.strip() and "ollama" not in x.lower()]
    except Exception:
        return []


def throttle_counters():
    """Cumulative microseconds spent in each throttle reason (diff two reads to get a run's share)."""
    try:
        out = subprocess.run(["nvidia-smi", "-q", "-d", "PERFORMANCE"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return {}
    res = {}
    for name in ("SW Power Capping", "SW Thermal Slowdown", "HW Thermal Slowdown", "HW Power Brake Slowdown"):
        m = re.search(name + r"\s*:\s*(\d+) us", out)
        if m:
            res[name] = int(m.group(1))
    return res


def ollama_version():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/version", timeout=5) as r:
            return json.load(r)["version"]
    except Exception:
        return None


def digest(model):
    if not _digests:
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
                for m in json.load(r)["models"]:
                    _digests[m["name"]] = (m["digest"][:12], m.get("details", {}).get("quantization_level"), m.get("details", {}).get("parameter_size"))
        except Exception:
            pass
    return _digests.get(model, (None, None, None))


def prompts_hash():
    p = ROOT / "prompts" / "prompts.json"
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else None


def ollama_ram_mb():
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-Process ollama* -ErrorAction SilentlyContinue | Measure-Object WorkingSet64 -Sum).Sum"], capture_output=True, text=True, timeout=20).stdout.strip()
        return round(int(out) / 1048576) if out else None
    except Exception:
        return None


def ps_split(model):
    """CPU/GPU split from `ollama ps`, matching the exact model name only."""
    try:
        out = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return None
    for line in out.splitlines():
        if line.split() and line.split()[0] == model:
            m = re.search(r"(\d+)%/(\d+)% CPU/GPU", line)
            size = re.search(r"(\d+(?:\.\d+)?) (GB|MB)", line)
            gb = (float(size.group(1)) / (1 if size.group(2) == "GB" else 1024)) if size else None
            if m:
                return {"cpu": int(m.group(1)), "gpu": int(m.group(2)), "size_gb": gb}
            if "100% GPU" in line:
                return {"cpu": 0, "gpu": 100, "size_gb": gb}
            if "100% CPU" in line:
                return {"cpu": 100, "gpu": 0, "size_gb": gb}
    return None


def static_env(model=None):
    g = gpu_now()
    d = digest(model) if model else (None, None, None)
    return {"hw": HW_ID, "power_limit_w": g.get("power_limit_w"), "ollama": ollama_version(), "harness": HARNESS_VERSION,
            "prompts_hash": prompts_hash(), "digest": d[0], "quant": d[1], "params": d[2], "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}


class PowerSampler:
    """Background sampler of GPU power/clock/temp/VRAM while a request runs."""
    def __init__(self, interval=0.5):
        import threading
        self.interval, self.samples, self._stop = interval, [], threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            s = gpu_now()
            if s:
                self.samples.append(s)
            self._stop.wait(self.interval)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        self._t.join(timeout=5)

    def summary(self):
        if not self.samples:
            return {}
        pw = [s["power_w"] for s in self.samples]
        return {"power_avg_w": round(sum(pw) / len(pw), 1), "power_max_w": max(pw), "clock_avg_mhz": round(sum(s["clock_mhz"] for s in self.samples) / len(self.samples)),
                "temp_max_c": max(s["temp_c"] for s in self.samples), "vram_peak_mib": max(s["vram_mib"] for s in self.samples), "n_samples": len(self.samples)}
