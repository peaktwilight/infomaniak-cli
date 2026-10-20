"""Infomaniak API client."""

import os
import sys

import requests

from infomaniak_cli import API_BASE
from infomaniak_cli.output import red


def api_request(method, path, token, params=None, json_data=None):
    """Make an authenticated request to the Infomaniak API."""
    if os.environ.get("INFOMANIAK_READ_ONLY") and method.upper() not in ("GET", "HEAD"):
        print(f"  {red('✗')} INFOMANIAK_READ_ONLY is set: {method.upper()} {path} was not sent.")
        sys.exit(1)

    url = f"{API_BASE}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    resp = requests.request(
        method, url, headers=headers, params=params, json=json_data, timeout=30
    )

    if resp.status_code == 204:
        return {"result": "success", "data": None}

    try:
        data = resp.json()
    except ValueError:
        print(f"  {red('✗')} Non-JSON response (HTTP {resp.status_code})")
        print(f"  {resp.text[:500]}")
        sys.exit(1)

    if data.get("result") == "error":
        err = data.get("error", {})
        code = err.get("code", "unknown")
        desc = err.get("description", resp.text[:200])
        print(f"  {red('✗')} API error [{code}]: {desc}")
        sys.exit(1)

    if resp.status_code >= 400:
        print(f"  {red('✗')} HTTP {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)

    return data


def api_request_paginated(path, token, params=None):
    """Fetch all pages from a paginated Infomaniak API endpoint."""
    if params is None:
        params = {}
    params["items_per_page"] = 50
    params["page"] = 1

    all_data = []
    while True:
        data = api_request("GET", path, token, params=params)
        items = data.get("data", [])
        all_data.extend(items)
        total_pages = data.get("pages", 1)
        if params["page"] >= total_pages:
            break
        params["page"] += 1

    return all_data
