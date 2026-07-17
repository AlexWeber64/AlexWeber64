#!/usr/bin/env python3
"""
Pulls the current count of live Cloudflare Pages deployments and writes:
  - stats.json        (raw data, for your own records)
  - stats-badge.json  (shields.io endpoint format, consumed by the README badge)

Auth: reads CF_API_TOKEN and CF_ACCOUNT_ID from environment variables.
Set these as repo secrets, not hardcoded values.

Counting logic: counts Pages projects that have a custom domain attached
matching the "-example-website.alexweber.org" pattern. Adjust MATCH_PATTERN
below if the naming convention changes.
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.error

CF_API_TOKEN = os.environ.get("CF_API_TOKEN")
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
MATCH_PATTERN = "-example-website.alexweber.org"  # matches your live custom domain pattern

API_BASE = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/pages/projects"


def fetch_all_projects():
    # Note: the Pages "list projects" endpoint does NOT support page/per_page
    # query params (unlike most other Cloudflare API endpoints) — it returns
    # the full project list in a single response. Passing those params
    # triggers error 8000024 ("Invalid list options provided").
    req = urllib.request.Request(
        API_BASE,
        headers={
            "Authorization": f"Bearer {CF_API_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Cloudflare API error: {e.code} {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    if not body.get("success"):
        print(f"Cloudflare API returned failure: {body.get('errors')}", file=sys.stderr)
        sys.exit(1)

    return body.get("result", [])


def main():
    if not CF_API_TOKEN or not CF_ACCOUNT_ID:
        print("Missing CF_API_TOKEN or CF_ACCOUNT_ID environment variables.", file=sys.stderr)
        sys.exit(1)

    all_projects = fetch_all_projects()

    def has_matching_domain(project):
        domains = project.get("domains", []) or []
        return any(MATCH_PATTERN in d for d in domains)

    live_sites = [p for p in all_projects if has_matching_domain(p)]

    count = len(live_sites)
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    # Raw stats, for your own reference / future dashboard use
    stats = {
        "sites_deployed": count,
        "total_pages_projects": len(all_projects),
        "last_updated_utc": now,
    }
    with open("stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    # shields.io endpoint badge format
    # https://shields.io/badges/endpoint-badge
    badge = {
        "schemaVersion": 1,
        "label": "live sites deployed",
        "message": f"{count:,}",
        "color": "0969da",
        "cacheSeconds": 3600,
    }
    with open("stats-badge.json", "w") as f:
        json.dump(badge, f, indent=2)

    print(f"Updated stats: {count} live sites out of {len(all_projects)} total Pages projects.")


if __name__ == "__main__":
    main()