"""Generate a public-only GitHub profile dashboard. Standard library only."""
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import urllib.request

USER = "QiOrange-qior"
OUTPUT = Path("assets/github-dashboard.svg")


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-dashboard",
               "X-GitHub-Api-Version": "2026-03-10"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect():
    profile = api("/users/" + USER)
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{USER}/repos?type=owner&sort=full_name&per_page=100&page={page}")
        repos.extend(r for r in batch if not r["private"] and r["owner"]["login"].lower() == USER.lower())
        if len(batch) < 100:
            break
        page += 1
    return profile, repos


def render(profile, repos, stamp):
    original = [r for r in repos if not r["fork"]]
    languages = Counter(r["language"] for r in original if r.get("language"))
    recent = sorted((r for r in original if r["name"].lower() != USER.lower()),
                    key=lambda r: r.get("pushed_at") or "", reverse=True)[:3]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="410" viewBox="0 0 960 410" role="img" aria-labelledby="title desc">',
             '<title id="title">Dylan — GitHub public repository dashboard</title>',
             '<desc id="desc">Public repository counts, stars on non-fork repositories, followers, primary languages by repository count, and latest repository push dates.</desc>',
             '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:#24292f}.muted{fill:#57606a}.label{font-size:12px;letter-spacing:1px}.small{font-size:12px}.value{font-size:34px;font-weight:650}.name{font-size:14px;font-weight:600}</style>',
             '<rect x="1" y="1" width="958" height="408" rx="18" fill="#ffffff" stroke="#d8dee4"/>',
             '<text x="28" y="34" class="label">GITHUB / PUBLIC SNAPSHOT</text>',
             f'<text x="932" y="34" text-anchor="end" class="small muted">Updated {escape(stamp)} UTC</text>',
             '<path d="M28 54H932M28 164H932" stroke="#eaeef2"/>']
    metrics = [(len(original), "NON-FORK REPOS"),
               (len(repos)-len(original), "FORKS"),
               (sum(r["stargazers_count"] for r in original), "STARS · NON-FORK"),
               (profile["followers"], "FOLLOWERS")]
    for i, (value, label) in enumerate(metrics):
        x = 28 + i * 234
        parts += [f'<text x="{x}" y="108" class="value">{value:,}</text>',
                  f'<text x="{x}" y="137" class="label muted">{label}</text>']
    parts += ['<text x="28" y="198" class="label">PRIMARY LANGUAGES</text>',
              '<text x="496" y="198" class="label">RECENT REPOSITORY PUSHES</text>']
    top = languages.most_common(4)
    if not top:
        parts.append('<text x="28" y="234" class="small muted">No language data available.</text>')
    for i, (language, count) in enumerate(top):
        y = 230 + i * 31
        width = round(220 * count / max(languages.values()), 1)
        parts += [f'<text x="28" y="{y}" class="small">{escape(language)}</text>',
                  f'<rect x="150" y="{y-10}" width="220" height="8" rx="4" fill="#eaeef2"/>',
                  f'<rect x="150" y="{y-10}" width="{width}" height="8" rx="4" fill="#6e7781"/>',
                  f'<text x="410" y="{y}" text-anchor="end" class="small muted">{count}</text>']
    for i, repo in enumerate(recent):
        y = 230 + i * 44
        name = repo["name"]
        label = name if len(name) <= 44 else name[:41] + "..."
        date = (repo.get("pushed_at") or "unknown")[:10]
        parts += [f'<text x="496" y="{y}" class="name">{escape(label)}</text>',
                  f'<text x="496" y="{y+18}" class="small muted">{escape(date)} · {escape(repo.get("language") or "No primary language")}</text>']
    if not recent:
        parts.append('<text x="496" y="234" class="small muted">No repositories available.</text>')
    parts += ['<path d="M28 353H932" stroke="#eaeef2"/>',
              '<text x="28" y="378" class="small muted">Source: GitHub public API · Languages counted by non-fork repository, not code volume or skill.</text>',
              '<text x="28" y="395" class="small muted">Push dates describe repository updates, not personal contributions. Profile repository excluded from recent list.</text>',
              '</svg>']
    return "\n".join(parts) + "\n"


def main():
    profile, repos = collect()
    svg = render(profile, repos, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
