"""Regenerates README.md (terminal-style profile) from live GitHub data."""
import os
from collections import Counter
from pathlib import Path

import requests

USER = "bassam-alaraby"
API = "https://api.github.com"
TOKEN = os.environ.get("GH_TOKEN", "")
HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

BAR_WIDTH = 20
TOP_LANGS = 6
TOP_PROJECTS = 5
README = Path(__file__).resolve().parent.parent / "README.md"

WHOAMI = """\
bassam tarek alaraby — computer science student @ menoufia university (2025 - 2029)
location    shibin el-kom, egypt
site        bassamalaraby.me
github      github.com/bassam-alaraby"""

CONTACT = """\
Website: [bassamalaraby.me](https://bassamalaraby.me) <br>
LinkedIN: [linkedin.com/in/bsam-alaraby](https://www.linkedin.com/in/bsam-alaraby/) <br>
Email: [bassamalarabii@gmail.com](mailto:bassamalarabii@gmail.com)"""


def get(url, **params):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_repos():
    repos, page = [], 1
    while True:
        batch = get(f"{API}/users/{USER}/repos", per_page=100, page=page,
                    type="owner", sort="pushed")
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1


def fetch_contributions():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          contributionCalendar { totalContributions }
        }
      }
    }"""
    r = requests.post(f"{API}/graphql", headers=HEADERS, timeout=30,
                      json={"query": query, "variables": {"login": USER}})
    r.raise_for_status()
    return r.json()["data"]["user"]["contributionsCollection"]


def build_stack(repos):
    totals = Counter()
    for repo in repos:
        if repo["fork"]:
            continue
        totals.update(get(repo["languages_url"]))
    total = sum(totals.values()) or 1
    top = totals.most_common(TOP_LANGS)
    top_pct = top[0][1] / total * 100 if top else 1
    lines = []
    for name, size in top:
        pct = size / total * 100
        filled = max(1, round(pct / top_pct * BAR_WIDTH))
        lines.append(f"{name.lower():<12}{'█' * filled:<{BAR_WIDTH}} {round(pct):>3}%")
    return "\n".join(lines)


def build_projects(repos):
    own = [r for r in repos if not r["fork"] and r["name"].lower() != USER.lower()]
    own.sort(key=lambda r: r["pushed_at"], reverse=True)
    return "\n".join(f"{r['pushed_at'][:10]}  {r['name']}" for r in own[:TOP_PROJECTS])


def build_stats(user, repos, contrib):
    own = [r for r in repos if not r["fork"]]
    rows = [
        ("repositories", user["public_repos"]),
        ("stars", sum(r["stargazers_count"] for r in own)),
        ("forks", sum(r["forks_count"] for r in own)),
        ("followers", user["followers"]),
        ("commits", f"{contrib['totalCommitContributions']:,}"),
        ("PRs", contrib["totalPullRequestContributions"]),
        ("issues", contrib["totalIssueContributions"]),
        ("contributions",
         f"{contrib['contributionCalendar']['totalContributions']:,} (last 12 months)"),
    ]
    return "\n".join(f"{k:<15}{v}" for k, v in rows)


def block(title, body):
    return f"### `~ $ {title}`\n\n```text\n{body}\n```\n"


def main():
    user = get(f"{API}/users/{USER}")
    repos = fetch_repos()
    contrib = fetch_contributions()

    parts = [
        block("whoami", WHOAMI),
        block("cat stack.txt", build_stack(repos)),
        block("ls -t projects | head -5", build_projects(repos)),
        block("stats", build_stats(user, repos, contrib)),
        f"### `~ $ contact`\n\n{CONTACT}\n",
    ]
    
    # No timestamps on purpose: unchanged data => identical file => no commit.
    README.write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()