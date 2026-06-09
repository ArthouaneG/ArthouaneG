"""
update_readme.py
----------------
Updates README.md with:
  - Exact age calculated from birthdate (13/07/2005)
  - Total commit count for the current year via GitHub GraphQL API

Usage:
  python update_readme.py

Requires GITHUB_TOKEN environment variable (automatically set in GitHub Actions).
"""

import os
import re
import sys
from datetime import date

try:
    import requests
except ImportError:
    print("Missing dependency: pip install requests")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────

BIRTH_DATE      = date(2005, 7, 13)
GITHUB_USERNAME = "ArthouaneG"
README_PATH     = "README.md"

# ── Age ───────────────────────────────────────────────────────────────────────

def get_age() -> int:
    today = date.today()
    age = today.year - BIRTH_DATE.year
    if (today.month, today.day) < (BIRTH_DATE.month, BIRTH_DATE.day):
        age -= 1
    return age

# ── Commit count ──────────────────────────────────────────────────────────────

def get_commits_this_year(token: str | None) -> int:
    """
    Uses GitHub GraphQL to fetch total commits contributed this year.
    Falls back to counting PushEvents from the REST events API (last ~90 days)
    if no token is provided.
    """
    year = date.today().year

    if token:
        query = """
        query($login: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
              totalCommitContributions
            }
          }
        }
        """
        variables = {
            "login": GITHUB_USERNAME,
            "from":  f"{year}-01-01T00:00:00Z",
            "to":    f"{year}-12-31T23:59:59Z",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }
        resp = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            try:
                return data["data"]["user"]["contributionsCollection"]["totalCommitContributions"]
            except (KeyError, TypeError):
                print(f"GraphQL parse error: {data}")

    # ── Fallback: REST events (public, no token needed, ~90 days) ────────────
    print("No token or GraphQL failed — counting PushEvents from REST API (last 90 days).")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    count = 0
    for page in range(1, 11):
        resp = requests.get(
            f"https://api.github.com/users/{GITHUB_USERNAME}/events/public",
            headers=headers,
            params={"per_page": 100, "page": page},
            timeout=15,
        )
        if resp.status_code != 200 or not resp.json():
            break
        for event in resp.json():
            if event.get("type") == "PushEvent":
                count += event.get("payload", {}).get("distinct_size", 0)

    return count

# ── README update ─────────────────────────────────────────────────────────────

def update_readme(age: int, commits: int) -> None:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(r"<!-- AGE -->.*? ans", f"<!-- AGE --> {age} ans", content)
    content = re.sub(r"<!-- COMMITS -->.*? commits", f"<!-- COMMITS --> {commits} commits", content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"README updated — age: {age} ans, commits this year: {commits}")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token   = os.environ.get("GITHUB_TOKEN")
    age     = get_age()
    commits = get_commits_this_year(token)
    update_readme(age, commits)
