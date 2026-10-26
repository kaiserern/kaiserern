#!/usr/bin/env python3
"""Render README.md the way GitHub does (markdown API + GitHub-like CSS) so the
result can be inspected in a browser before it goes public."""

import json
import os
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
md = (ROOT / "README.md").read_text()

token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
req = urllib.request.Request(
    "https://api.github.com/markdown",
    data=json.dumps({"text": md, "mode": "gfm",
                     "context": "kaiserern/kaiserern"}).encode(),
)
req.add_header("Authorization", f"bearer {token}")
req.add_header("Accept", "application/vnd.github+json")
body = urllib.request.urlopen(req, timeout=30).read().decode()

CSS = """
*{box-sizing:border-box}
body{margin:0;background:%(bg)s;color:%(fg)s;
 font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:1012px;margin:0 auto;padding:32px 24px 80px}
.markdown-body{word-wrap:break-word}
.markdown-body img{max-width:100%%;box-sizing:content-box}
.markdown-body h2{font-size:1.5em;font-weight:600;margin:24px 0 16px;
 padding-bottom:.3em;border-bottom:1px solid %(border)s}
.markdown-body h3{font-size:1.25em;font-weight:600;margin:24px 0 16px}
.markdown-body p{margin:0 0 16px}
.markdown-body a{color:%(link)s;text-decoration:none}
.markdown-body a:hover{text-decoration:underline}
.markdown-body strong{font-weight:600}
.markdown-body code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
 font-size:85%%;background:%(codebg)s;padding:.2em .4em;border-radius:6px}
.markdown-body pre{background:%(codebg)s;padding:16px;overflow:auto;border-radius:6px;
 font-size:85%%;line-height:1.45}
.markdown-body pre code{background:none;padding:0;font-size:100%%}
.markdown-body table{border-collapse:collapse;margin:0 0 16px;display:block;overflow:auto;width:max-content;max-width:100%%}
.markdown-body th,.markdown-body td{border:1px solid %(border)s;padding:6px 13px}
.markdown-body th{font-weight:600;background:%(thead)s}
.markdown-body tr:nth-child(2n){background:%(stripe)s}
.markdown-body hr{height:.25em;padding:0;margin:24px 0;background:%(border)s;border:0}
.markdown-body ul{padding-left:2em;margin:0 0 16px}
.markdown-body li{margin:.25em 0}
"""

THEME = {
    "dark": dict(bg="#0d1117", fg="#e6edf3", border="#30363d", link="#4493f8",
                 codebg="rgba(110,118,129,0.4)", thead="#161b22",
                 stripe="#151b23"),
    "light": dict(bg="#ffffff", fg="#1f2328", border="#d1d9e0", link="#0969da",
                  codebg="rgba(129,139,152,0.12)", thead="#f6f8fa",
                  stripe="#f6f8fa"),
}

for name, theme in THEME.items():
    # The headless browser reports a light color scheme, so <picture> would pick
    # the light card in both previews. Pin the card to the variant under test.
    import re
    rendered = re.sub(
        r"<picture>.*?</picture>",
        f'<img src="assets/status-{name}.svg" alt="status card" width="880">',
        body, flags=re.S)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>kaiserern profile README — {name} preview</title>
<style>{CSS % theme}</style></head><body><div class="wrap">
<div class="markdown-body">{rendered}</div></div></body></html>"""
    (ROOT / f"preview-{name}.html").write_text(html)
    print("wrote", f"preview-{name}.html")
