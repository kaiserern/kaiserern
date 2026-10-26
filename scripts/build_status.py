#!/usr/bin/env python3
"""Generate the profile status card (dark + light SVG) from live GitHub data.

Every number on the card comes from the GitHub API at build time. If the API
call fails the script exits non-zero instead of writing a stale or invented
number.

Usage:
    GITHUB_TOKEN=$(gh auth token) python3 scripts/build_status.py
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

LOGIN = "kaiserern"
FLAGSHIP = "Kaiser.charon"

# Small repos worth naming on the card, in order.
EXTRA_REPOS = ["radar-loker"]

GRAPHQL = "https://api.github.com/graphql"
REST = "https://api.github.com"

MONO = ("ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,"
        "'Liberation Mono',monospace")

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "stroke": "#232a34",
        "name": "#e6edf3",
        "muted": "#8b949e",
        "label": "#6e7681",
        "value": "#c9d1d9",
        "accent": "#d29922",
    },
    "light": {
        "bg": "#ffffff",
        "stroke": "#d8dee4",
        "name": "#1f2328",
        "muted": "#59636e",
        "label": "#6e7781",
        "value": "#1f2328",
        "accent": "#9a6700",
    },
}

W = 880
PAD = 44
RULE_Y = 104


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        # local convenience: reuse the gh CLI session
        try:
            import subprocess
            tok = subprocess.check_output(["gh", "auth", "token"],
                                          text=True).strip()
        except Exception:
            tok = ""
    if not tok:
        sys.exit("GITHUB_TOKEN (or GH_TOKEN) is required")
    return tok


def api(url: str, tok: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data)
    req.add_header("Authorization", f"bearer {tok}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "kaiserern-profile-card")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def collect(tok: str) -> dict:
    user = api(f"{REST}/users/{LOGIN}", tok)
    repos = api(f"{REST}/users/{LOGIN}/repos?per_page=100&type=owner", tok)
    public = [r for r in repos if not r["private"]]

    q = """
    query($login:String!){ user(login:$login){ contributionsCollection{
      contributionCalendar{ totalContributions } } } }"""
    gql = api(GRAPHQL, tok, {"query": q, "variables": {"login": LOGIN}})
    contrib = gql["data"]["user"]["contributionsCollection"][
        "contributionCalendar"]["totalContributions"]

    flagship = next((r for r in public if r["name"] == FLAGSHIP), None)
    if flagship is None:
        sys.exit(f"{FLAGSHIP} not found among public repos")

    stars = sum(r["stargazers_count"] for r in public)
    forks = sum(r["forks_count"] for r in public)
    return {
        "name": (user.get("name") or LOGIN).upper(),
        "login": user["login"],
        "location": user.get("location") or "",
        "repos": len(public),
        "stars": stars,
        "forks": forks,
        "flagship": flagship["name"],
        "flagship_stars": flagship["stargazers_count"],
        "flagship_forks": flagship["forks_count"],
        "contrib": contrib,
        "languages": sorted(
            {r["language"] for r in public if r.get("language")}
        ),
    }


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;"))


def nfmt(n: int) -> str:
    return f"{n:,}"


def build_svg(d: dict, t: dict) -> str:
    label_x = PAD
    value_x = PAD + 104
    right_x = W - PAD

    now = f"{d['flagship']} — Solana execution bot · Shoal — Go orchestrator"
    stack = "Go · TypeScript · Python · PostgreSQL · SQLite · Solana"
    work = f"{d['repos']} public repos · most of the work sits in private ones"

    rows = [("NOW", now), ("STACK", stack), ("OPEN", work)]
    row_y = [148, 184, 220]
    height = 268

    # header stats, right aligned on the identity band
    head = (f"{nfmt(d['flagship_stars'])} stars · "
            f"{nfmt(d['flagship_forks'])} forks · "
            f"{nfmt(d['contrib'])} contributions (12 mo)")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" '
        f'height="{height}" viewBox="0 0 {W} {height}" '
        f'role="img" aria-labelledby="t">',
        f'<title id="t">{esc(d["name"])} — infrastructure, trading systems, '
        f'payment integrations</title>',
        f'<rect width="{W}" height="{height}" fill="{t["bg"]}"/>',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" '
        f'fill="none" stroke="{t["stroke"]}"/>',
        # identity
        f'<text x="{label_x}" y="54" font-family="{MONO}" font-size="25" '
        f'font-weight="600" letter-spacing="2.4" fill="{t["name"]}">'
        f'{esc(d["name"])}</text>',
        f'<text x="{right_x}" y="52" text-anchor="end" font-family="{MONO}" '
        f'font-size="11.5" letter-spacing="0.4" fill="{t["muted"]}">'
        f'{esc(head)}</text>',
        f'<circle cx="{label_x + 5}" cy="80" r="3.5" fill="{t["accent"]}"/>',
        f'<text x="{label_x + 18}" y="84" font-family="{MONO}" '
        f'font-size="12" letter-spacing="0.5" fill="{t["muted"]}">'
        f'@{esc(d["login"])} · {esc(d["location"])} · infrastructure, '
        f'trading systems, payment integrations</text>',
        f'<line x1="{PAD}" y1="{RULE_Y}" x2="{right_x}" y2="{RULE_Y}" '
        f'stroke="{t["stroke"]}"/>',
    ]

    for (label, value), y in zip(rows, row_y):
        parts.append(
            f'<text x="{label_x}" y="{y}" font-family="{MONO}" font-size="10.5" '
            f'letter-spacing="2" fill="{t["label"]}">{label}</text>'
        )
        parts.append(
            f'<text x="{value_x}" y="{y}" font-family="{MONO}" font-size="13" '
            f'fill="{t["value"]}">{esc(value)}</text>'
        )

    parts.append(
        f'<text x="{right_x}" y="{height - 20}" text-anchor="end" '
        f'font-family="{MONO}" font-size="9.5" letter-spacing="0.8" '
        f'fill="{t["label"]}">GENERATED FROM THE GITHUB API · REBUILT DAILY</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    tok = token()
    data = collect(tok)
    out = pathlib.Path(__file__).resolve().parent.parent / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for name, theme in THEMES.items():
        (out / f"status-{name}.svg").write_text(build_svg(data, theme))
    (out / "data.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote status-dark.svg / status-light.svg · "
          f"{data['flagship']} {data['flagship_stars']}★ "
          f"{data['flagship_forks']} forks · {data['contrib']} contributions")


if __name__ == "__main__":
    main()
