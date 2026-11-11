"""Inline site/results.json into site/template.html -> site/index.html (self-contained, no server needed)."""
from pathlib import Path
import json

S = Path(__file__).resolve().parent.parent / "site"
data = json.dumps(json.loads((S / "results.json").read_text(encoding="utf-8")))
html = (S / "template.html").read_text(encoding="utf-8").replace("/*DATA*/null", data)
(S / "index.html").write_text(html, encoding="utf-8")
print(f"wrote {S / 'index.html'} ({len(html)//1024} KB)")
