#!/usr/bin/env python3
"""
Counts live business site folders in the private final-website-files repo
and writes:
  - stats.json        (raw data, for your own records)
  - stats-badge.json  (shields.io endpoint format, consumed by the README badge)

Why this approach: the deployment pipeline puts every business site in its
own subfolder inside ONE Cloudflare Pages project (final-website-files),
organized by city:
    Pittsburgh/scott-mechanical-services-example-website/
    Cleveland/some-other-business-example-website/
    ...
Custom subdomains (like b-j-z-repairz-example-website.alexweber.org) are
routed to these folders via Cloudflare rules, not via separate Pages
projects or custom domains — so the Cloudflare API has no clean "count"
for this. The real source of truth is the folder structure itself, read
via the GitHub API's Git Trees endpoint (one call, works even on a
private repo, no pagination headaches).

Auth: reads GH_PAT, GH_OWNER, GH_REPO, GH_BRANCH from environment variables.
Set GH_PAT as a repo secret — a fine-grained PAT with read-only "Contents"
access to the final-website-files repo is enough.
"""

import os
import sys
import json
import re
import datetime
import urllib.request
import urllib.error

GH_PAT = os.environ.get("GH_PAT")
GH_OWNER = os.environ.get("GH_OWNER", "AlexWeber64")
GH_REPO = os.environ.get("GH_REPO", "final-website-files")
GH_BRANCH = os.environ.get("GH_BRANCH", "main")

# Matches paths like "Pittsburgh/scott-mechanical-services-example-website"
# i.e. exactly one city folder deep, ending in "-example-website".
SITE_FOLDER_RE = re.compile(r"^[^/]+/[^/]+-example-website$")

TREE_URL = (
    f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/git/trees/"
    f"{GH_BRANCH}?recursive=1"
)


def fetch_tree():
    req = urllib.request.Request(
        TREE_URL,
        headers={
            "Authorization": f"Bearer {GH_PAT}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"GitHub API error: {e.code} {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    if body.get("truncated"):
        print(
            "Warning: GitHub truncated the tree response (repo is very large). "
            "Count below may be a undercount.",
            file=sys.stderr,
        )

    return body.get("tree", [])


def main():
    if not GH_PAT:
        print("Missing GH_PAT environment variable.", file=sys.stderr)
        sys.exit(1)

    tree = fetch_tree()

    site_folders = [
        item["path"]
        for item in tree
        if item.get("type") == "tree" and SITE_FOLDER_RE.match(item.get("path", ""))
    ]

    count = len(site_folders)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    stats = {
        "sites_deployed": count,
        "last_updated_utc": now,
    }
    with open("stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    badge = {
        "schemaVersion": 1,
        "label": "live sites deployed",
        "message": f"{count:,}",
        "color": "0969da",
        "cacheSeconds": 3600,
    }
    with open("stats-badge.json", "w") as f:
        json.dump(badge, f, indent=2)

    print(f"Updated stats: {count} live site folders found.")


if __name__ == "__main__":
    main()
