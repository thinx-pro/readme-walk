#!/usr/bin/env python3
"""Render real readme_check output on examples/bad-README.md as a terminal-window HTML page
(for the README screenshot, captured with headless Chrome)."""
import html
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = subprocess.run(
    [sys.executable, "skills/readme-walk/readme_check.py", "examples/bad-README.md", "--color", "--no-which"],
    cwd=ROOT, capture_output=True, text=True).stdout

STYLE = {"1": "font-weight:700", "31;1": "color:#ff7b72;font-weight:700", "33": "color:#e3b341",
         "36": "color:#56d4dd", "90": "color:#8b949e"}


def ansi(s):
    s = html.escape(s)
    s = re.sub(r"\x1b\[([\d;]+)m(.*?)\x1b\[0m", lambda m: f'<span style="{STYLE.get(m.group(1), "")}">{m.group(2)}</span>', s)
    return s


page = f"""<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#0d1117}}
.win{{margin:24px;border-radius:10px;background:#161b22;box-shadow:0 8px 30px rgba(0,0,0,.5);overflow:hidden;width:max-content}}
.bar{{height:30px;background:#21262d;display:flex;align-items:center;gap:8px;padding:0 12px}}
.dot{{width:12px;height:12px;border-radius:50%}}
pre{{margin:0;padding:18px 22px 22px;color:#c9d1d9;font:14px/1.5 "SF Mono",Menlo,Consolas,monospace}}
</style><div class="win"><div class="bar"><span class="dot" style="background:#ff5f56"></span>
<span class="dot" style="background:#ffbd2e"></span><span class="dot" style="background:#27c93f"></span></div>
<pre><span style="color:#8b949e">$ python3 readme_check.py examples/bad-README.md</span>
{ansi(out.rstrip())}</pre></div>"""
dest = os.path.join(ROOT, "assets", "check.html")
os.makedirs(os.path.dirname(dest), exist_ok=True)
with open(dest, "w", encoding="utf-8") as fh:
    fh.write(page)
print(dest)
