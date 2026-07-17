#!/usr/bin/env python3
"""
Pulls the current count of live Cloudflare Pages deployments and writes:
  - stats.json        (raw data, for your own records)
  - stats-badge.json  (shields.io endpoint format, consumed by the README badge)

Auth: reads CF_API_TOKEN and CF_ACCOUNT_ID from environment variables.
Set these as repo secrets, not hardcoded values.

Counting logic: counts Pages projects whose subdomain matches the
"-example-website" naming convention used by the deployment pipeline.
Adjust MATCH_SUFFIX below if the naming convention changes.
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.error

CF_API_TOKEN = os.environ.get("CF_API_TOKEN")
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID")
MATCH_SUFFIX = "-example-website"  # only count real client deployments

API_BASE = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/pages/projects"


def fetch_all_projects():
    projects = []
    page = 1
    per_page = 50

    while True:
        url = f"{API_BASE}?page={page}&per_page={per_page}"
        req = urllib.request.Request(
            url,
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

        result = body.get("result", [])
        projects.extend(result)

        info = body.get("result_info", {})
        if page >= info.get("total_pages", 1):
            break
        page += 1

    return projects


def main():
    if not CF_API_TOKEN or not CF_ACCOUNT_ID:
        print("Missing CF_API_TOKEN or CF_ACCOUNT_ID environment variables.", file=sys.stderr)
        sys.exit(1)

    all_projects = fetch_all_projects()
    live_sites = [p for p in all_projects if MATCH_SUFFIX in p.get("name", "")]

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
