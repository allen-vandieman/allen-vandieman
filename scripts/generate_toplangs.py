#!/usr/bin/env python3
"""Generate a simple Top Languages SVG for a GitHub user.

Usage:
  python scripts/generate_toplangs.py --username allen-vandieman --output img/top-langs.svg

The script uses the GitHub REST API. It respects GITHUB_TOKEN if present to increase rate limits.
"""

from __future__ import annotations
import argparse
import os
import sys
import requests
from collections import defaultdict

LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#2b7489",
    "C": "#555555",
    "C++": "#f34b7d",
    "Java": "#b07219",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Go": "#00ADD8",
    "Shell": "#89e051",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
}
DEFAULT_COLOR = "#6c757d"

SESSION = requests.Session()

def get_repos(username: str):
    repos = []
    page = 1
    headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        r = SESSION.get(url, headers=headers)
        if r.status_code != 200:
            raise SystemExit(f"Error fetching repos: {r.status_code} {r.text}")
        data = r.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def aggregate_languages(repos):
    totals = defaultdict(int)
    headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    for repo in repos:
        # skip archived repositories
        if repo.get("archived"):
            continue
        languages_url = repo.get("languages_url")
        if not languages_url:
            continue
        r = SESSION.get(languages_url, headers=headers)
        if r.status_code != 200:
            # continue on language fetch errors
            continue
        for lang, bytes_count in r.json().items():
            totals[lang] += bytes_count
    return dict(totals)


def build_svg(lang_data, output_path, top_n=6):
    total_bytes = sum(lang_data.values())
    items = sorted(lang_data.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    # simple layout
    width = 500
    row_height = 22
    padding = 10
    height = padding * 2 + row_height * len(items)

    lines = [
        f"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\">",
        '<style>text{font-family:Arial, Helvetica, sans-serif; font-size:12px; fill:#333}</style>',
    ]

    y = padding
    x_label = 60
    bar_x = 160
    bar_w = width - bar_x - padding

    for lang, bytes_count in items:
        pct = (bytes_count / total_bytes * 100) if total_bytes else 0
        color = LANG_COLORS.get(lang, DEFAULT_COLOR)
        # label
        lines.append(f'<text x="{x_label}" y="{y + 14}">{lang}</text>')
        # percentage text
        pct_text = f"{pct:.1f}%"
        lines.append(f'<text x="{bar_x + bar_w + 6}" y="{y + 14}">{pct_text}</text>')
        # bar
        bar_len = int(bar_w * (pct / 100)) if pct else 0
        lines.append(f'<rect x="{bar_x}" y="{y}" width="{bar_len}" height="14" fill="{color}" rx="3"/>')
        y += row_height

    # footer
    lines.append('</svg>')
    svg = "\n".join(lines)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(svg)


def get_user_info(username: str):
    """Return user info JSON from GitHub API (may include public_repos)."""
    headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"https://api.github.com/users/{username}"
    r = SESSION.get(url, headers=headers)
    if r.status_code != 200:
        print(f"Warning: could not fetch user info: {r.status_code}")
        return {}
    return r.json()


def build_badge(label: str, value: str, output_path: str, left_color="#555", right_color="#007ec6"):
    """Create a simple two-part badge SVG similar to Shields style."""
    # estimate widths
    left_w = max(80, 8 * len(label) + 10)
    right_w = max(50, 8 * len(str(value)) + 10)
    width = left_w + right_w
    height = 20
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="{left_w}" height="{height}" fill="{left_color}" rx="3"/>
  <rect x="{left_w}" width="{right_w}" height="{height}" fill="{right_color}" rx="3"/>
  <style>text{{font-family:Arial, Helvetica, sans-serif; font-size:11px; fill:#fff}}</style>
  <text x="{left_w/2}" y="14" text-anchor="middle">{label}</text>
  <text x="{left_w + right_w/2}" y="14" text-anchor="middle">{value}</text>
</svg>'''
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(svg)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--username", default=os.environ.get("GITHUB_USER", "allen-vandieman"))
    p.add_argument("--output", default="img/top-langs.svg")
    p.add_argument("--top", type=int, default=6)
    args = p.parse_args()

    repos = get_repos(args.username)
    lang_totals = aggregate_languages(repos)
    if not lang_totals:
        print("No language data found; writing a placeholder SVG.")
        build_svg({}, args.output, top_n=args.top)
    else:
        build_svg(lang_totals, args.output, top_n=args.top)
        print(f"Wrote {args.output}")

    # create a local Public Repos badge from the user endpoint
    user = get_user_info(args.username)
    public_repos = user.get("public_repos") if user else None
    if public_repos is None:
        # fallback to counting fetched repos
        public_repos = len(repos)
    build_badge("Public Repos", str(public_repos), "img/public-repos.svg")
    print("Wrote img/public-repos.svg")


if __name__ == "__main__":
    main()
