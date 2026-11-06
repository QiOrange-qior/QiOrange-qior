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


def calendar():
    query = """query($login:String!) { user(login:$login) { contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    } } }"""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN required for contribution history")
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                 "User-Agent": "profile-dashboard"})
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError("Contribution API did not return a complete result")
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def summarize(cal):
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    if not days:
        raise ValueError("Missing contribution dates")
    counts, seen = Counter(), set()
    for day in days:
        date, value = day["date"], day["contributionCount"]
        datetime.strptime(date, "%Y-%m-%d")
        if date in seen or not isinstance(value, int) or value < 0:
            raise ValueError("Invalid contribution day")
        seen.add(date)
        counts[date[:7]] += value
    if sum(counts.values()) != cal["totalContributions"]:
        raise ValueError("Contribution totals do not reconcile")
    return sorted(counts.items()), sum(d["contributionCount"] > 0 for d in days), min(seen), max(seen)


def render(profile, repos, cal, stamp):
    months, active, first, last = summarize(cal)
    original = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in original)
    total = cal["totalContributions"]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="340" viewBox="0 0 960 340" role="img" aria-labelledby="title desc">',
      '<title id="title">Dylan — GitHub contribution timeline</title>',
      f'<desc id="desc">{first} to {last}: {total} contributions on {active} active days. Monthly totals; partial first and last months. Counts reflect GitHub API visibility.</desc>',
      '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;fill:#263e3b}.muted{fill:#697a75}.small{font-size:14px}.label{font-size:16px}.mono{font-family:ui-monospace,monospace;letter-spacing:1px}</style>',
      '<rect x="1" y="1" width="958" height="338" rx="20" fill="#f7faf8" stroke="#dce6df"/>',
      '<text x="28" y="38" class="label mono">THE MAKING LOG</text>',
      f'<text x="932" y="38" text-anchor="end" class="small muted">Updated {escape(stamp)} UTC</text>',
      f'<text x="28" y="125" font-size="64" font-weight="650">{total:,}</text>',
      '<text x="30" y="155" class="label">过去一年 · GitHub 贡献</text>',
      f'<text x="30" y="200" font-size="26" font-weight="600">{active}</text>',
      '<text x="85" y="200" class="label muted">个活跃日</text>',
      f'<text x="30" y="244" class="small muted">{len(original)} 非 Fork 公开仓库 · {stars} Stars</text>',
      '<path d="M268 76V264" stroke="#dce6df"/>']
    top = max(1, max(v for _, v in months))
    for ratio in (0, 0.5, 1):
        y = 252 - 140 * ratio
        parts.append(f'<path d="M306 {y}H930" stroke="#dce6df" stroke-dasharray="3 5"/>')
    step = 624 / len(months)
    for i, (month, value) in enumerate(months):
        x, width = 312 + step * i, step - 12
        height = 140 * value / top
        fill = "#d58165" if i == len(months)-1 else "#4f877c"
        parts += [f'<rect x="{x:.2f}" y="{252-height:.2f}" width="{width:.2f}" height="{height:.2f}" rx="4" fill="{fill}"><title>{month}: {value} contributions</title></rect>',
          f'<text x="{x+width/2:.2f}" y="{max(93,243-height):.2f}" text-anchor="middle" class="small">{value}</text>',
          f'<text x="{x+width/2:.2f}" y="275" text-anchor="middle" class="small muted">{month[5:]}</text>']
    parts += ['<text x="306" y="83" class="label">贡献记录 / 按月汇总</text>',
      f'<text x="30" y="311" class="small muted">{first} — {last} · 首尾月份为部分月份 · 来源：GitHub API</text>', '</svg>']
    return "\n".join(parts) + "\n"


def main():
    profile, repos = collect()
    svg = render(profile, repos, calendar(), datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
