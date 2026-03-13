#!/usr/bin/env python3
"""
infomaniak — CLI for managing Infomaniak services.

Usage:
    infomaniak setup                                         # Configure your API token
    infomaniak dns domains                                   # List all domains
    infomaniak dns records <domain>                          # List DNS records
    infomaniak dns check <domain> <record_id>                # Check record health
    infomaniak dns add <domain> <type> <source> <target>     # Create record
    infomaniak dns update <domain> <record_id> --target X    # Update record
    infomaniak dns delete <domain> <record_id>               # Delete record

Configuration:
    Token lookup order: env var > config file > .env file
    Run 'infomaniak setup' to save your token to ~/.config/infomaniak/config.ini
    Or set INFOMANIAK_API_TOKEN as an environment variable.
"""

import argparse
import configparser
import json
import os
import re
import sys
import webbrowser
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' is required. Install it with: pip install requests")
    sys.exit(1)


__version__ = "0.3.0"
API_BASE = "https://api.infomaniak.com"
CONFIG_DIR = Path.home() / ".config" / "infomaniak"
CONFIG_FILE = CONFIG_DIR / "config.ini"


# ── Terminal colors ───────────────────────────────────────────────────────────


_COLOR = sys.stdout.isatty()
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _COLOR else str(text)


def bold(t):   return _c("1", t)
def green(t):  return _c("32", t)
def red(t):    return _c("31", t)
def yellow(t): return _c("33", t)
def cyan(t):   return _c("36", t)
def dim(t):    return _c("2", t)


def _visible_len(s):
    return len(_ANSI_RE.sub("", str(s)))


def _ljust(s, width):
    return str(s) + " " * (width - _visible_len(str(s)))


# ── Config ────────────────────────────────────────────────────────────────────


def load_config():
    """Load config from ~/.config/infomaniak/config.ini."""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    return config


def save_config(token, account_id=None):
    """Save config to ~/.config/infomaniak/config.ini."""
    config = configparser.ConfigParser()
    config["default"] = {"token": token}
    if account_id:
        config["default"]["account_id"] = str(account_id)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
    CONFIG_FILE.chmod(0o600)


def load_env_file():
    """Load variables from .env file if it exists."""
    for env_path in [Path(".env"), Path(__file__).parent / ".env"]:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip("'\"")
                        if key and key not in os.environ:
                            os.environ[key] = value


# ── Auth ──────────────────────────────────────────────────────────────────────


def get_token():
    """Get API token from env, config file, or .env file."""
    token = os.environ.get("INFOMANIAK_API_TOKEN")
    if token:
        return token

    config = load_config()
    token = config.get("default", "token", fallback=None)
    if token:
        return token

    print(f"\n  {red('✗')} No API token found.\n")
    print(f"  Run {bold('infomaniak setup')} to configure your token.")
    print(f"  Or set {bold('INFOMANIAK_API_TOKEN')} in your environment.\n")
    sys.exit(1)


def get_account_id(token):
    """Get account ID from env, config, or auto-discover it."""
    account_id = os.environ.get("INFOMANIAK_ACCOUNT_ID")
    if account_id:
        return account_id

    config = load_config()
    account_id = config.get("default", "account_id", fallback=None)
    if account_id:
        return account_id

    data = api_request("GET", "/1/accounts", token)
    accounts = data.get("data", [])
    if not accounts:
        print(f"  {red('✗')} No accounts found for this token.")
        sys.exit(1)
    if len(accounts) == 1:
        return accounts[0]["id"]

    print("  Multiple accounts found:\n")
    for i, acc in enumerate(accounts):
        print(f"    [{i+1}] {acc['name']} (ID: {acc['id']})")
    print()
    choice = input(f"  Select account [1-{len(accounts)}]: ")
    try:
        idx = int(choice) - 1
        return accounts[idx]["id"]
    except (ValueError, IndexError):
        print(f"  {red('✗')} Invalid choice.")
        sys.exit(1)


def api_request(method, path, token, params=None, json_data=None):
    """Make an authenticated request to the Infomaniak API."""
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


# ── Table formatting ──────────────────────────────────────────────────────────


def print_table(headers, rows):
    """Print a simple aligned table with colored headers."""
    if not rows:
        print(f"  {dim('(no results)')}")
        return

    col_widths = [_visible_len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], _visible_len(str(cell)))

    header_line = "  ".join(_ljust(bold(h), col_widths[i]) for i, h in enumerate(headers))
    separator = dim("  ".join("─" * col_widths[i] for i in range(len(headers))))
    print(f"  {header_line}")
    print(f"  {separator}")

    for row in rows:
        line = "  ".join(_ljust(str(cell), col_widths[i]) for i, cell in enumerate(row))
        print(f"  {line}")


# ── Setup Command ─────────────────────────────────────────────────────────────


def cmd_setup(args):
    """Interactive setup wizard for configuring the API token."""
    print(f"\n  {bold('Infomaniak CLI Setup')}")
    print(f"  {dim('───────────────────')}\n")

    # Check for existing config
    if CONFIG_FILE.exists():
        config = load_config()
        existing = config.get("default", "token", fallback=None)
        if existing:
            masked = existing[:6] + "..." + existing[-4:]
            print(f"  Existing token found: {dim(masked)}")
            confirm = input(f"  Overwrite? [y/N] ")
            if confirm.lower() not in ("y", "yes"):
                print(f"  {dim('Aborted.')}")
                return
            print()

    print("  You need an API token with these scopes:\n")
    print(f"    {cyan('•')} domain:read")
    print(f"    {cyan('•')} dns:read")
    print(f"    {cyan('•')} dns:write\n")

    url = "https://manager.infomaniak.com/v3/infomaniak-api"
    choice = input(f"  Press {bold('Enter')} to open the token page, or {bold('s')} to skip: ")
    if choice.lower() != "s":
        webbrowser.open(url)
        print(f"  {dim(f'Opened {url}')}\n")
    else:
        print(f"  {dim(f'Go to: {url}')}\n")

    token = input("  Paste your API token: ").strip()
    if not token:
        print(f"\n  {red('✗')} No token provided.")
        sys.exit(1)

    # Validate
    print(f"\n  Validating token...", end="", flush=True)
    try:
        data = api_request("GET", "/1/accounts", token)
    except SystemExit:
        print(f"\r  {red('✗')} Invalid token or API error.     ")
        sys.exit(1)

    accounts = data.get("data", [])
    if not accounts:
        print(f"\r  {red('✗')} No accounts found for this token.")
        sys.exit(1)

    # Select account
    if len(accounts) == 1:
        account = accounts[0]
    else:
        print(f"\r  {green('✓')} Token valid — {len(accounts)} accounts found.\n")
        for i, acc in enumerate(accounts):
            print(f"    [{i+1}] {acc['name']} (ID: {acc['id']})")
        print()
        choice = input(f"  Select account [1-{len(accounts)}]: ")
        try:
            idx = int(choice) - 1
            account = accounts[idx]
        except (ValueError, IndexError):
            print(f"  {red('✗')} Invalid choice.")
            sys.exit(1)

    account_name = account.get("name", "Unknown")
    account_id = account["id"]

    print(f"\r  {green('✓')} Token valid — account: {bold(account_name)} (ID: {account_id})")

    # Save
    save_config(token, account_id)
    print(f"  {green('✓')} Saved to {dim(str(CONFIG_FILE))}\n")
    print(f"  You're all set! Try: {bold('infomaniak dns domains')}\n")


# ── DNS Commands ──────────────────────────────────────────────────────────────


def cmd_dns_domains(args):
    """List all domains on the account."""
    token = get_token()
    account_id = get_account_id(token)

    data = api_request("GET", f"/1/domain/account/{account_id}", token)
    domains = data.get("data", [])

    if not domains:
        print(f"  {dim('No domains found.')}")
        return

    headers = ["ID", "Domain", "DNSSEC", "DNS@IK"]
    rows = []
    for d in domains:
        dnssec = green("yes") if d.get("has_dnssec") else dim("no")
        dns_ik = green("yes") if d.get("is_dns_managed_by_infomaniak") else dim("no")
        rows.append([
            d.get("id", "?"),
            d.get("customer_name", "?"),
            dnssec,
            dns_ik,
        ])

    print(f"\n  {bold(f'Domains ({len(rows)})')}\n")
    print_table(headers, rows)
    print()


def cmd_dns_records(args):
    """List DNS records for a domain."""
    token = get_token()
    domain = args.domain

    data = api_request("GET", f"/2/zones/{domain}/records", token)
    records = data.get("data", [])

    if not records:
        print(f"  {dim(f'No DNS records found for {domain}.')}")
        return

    if args.type:
        filter_type = args.type.upper()
        records = [r for r in records if r.get("type") == filter_type]

    records.sort(key=lambda r: (r.get("type", ""), r.get("source", "")))

    headers = ["ID", "Type", "Name", "Target", "TTL"]
    rows = []
    for r in records:
        source = r.get("source", "@")
        if source == ".":
            source = "@"
        target = r.get("target", "?")
        if len(str(target)) > 60:
            target = str(target)[:57] + "..."
        rows.append([
            r.get("id", "?"),
            cyan(r.get("type", "?")),
            source,
            target,
            r.get("ttl", "?"),
        ])

    type_note = f" type={args.type.upper()}" if args.type else ""
    print(f"\n  {bold(f'DNS records for {domain}')}{dim(type_note)} — {len(rows)} records\n")
    print_table(headers, rows)
    print()


def cmd_dns_check(args):
    """Check if a DNS record resolves correctly."""
    token = get_token()
    data = api_request("GET", f"/2/zones/{args.domain}/records/{args.record_id}/check", token)
    result = data.get("data", {})

    print(f"\n  {bold(f'DNS check for record {args.record_id} in {args.domain}')}\n")
    print(json.dumps(result, indent=2))
    print()


def cmd_dns_add(args):
    """Create a new DNS record."""
    token = get_token()

    source = args.source
    if source == "@":
        source = ""

    body = {
        "type": args.type.upper(),
        "source": source,
        "target": args.target,
        "ttl": args.ttl,
    }

    display_name = args.source if args.source != "@" else args.domain
    print(f"\n  Creating {cyan(body['type'])} record: {display_name}.{args.domain} → {body['target']} (TTL: {body['ttl']})")
    data = api_request("POST", f"/2/zones/{args.domain}/records", token, json_data=body)

    record = data.get("data", {})
    print(f"  {green('✓')} Created record ID: {bold(str(record.get('id')))}\n")


def cmd_dns_update(args):
    """Update an existing DNS record."""
    token = get_token()

    body = {}
    if args.target:
        body["target"] = args.target
    if args.ttl:
        body["ttl"] = args.ttl

    if not body:
        print(f"  {red('✗')} Specify at least one of --target or --ttl to update.")
        sys.exit(1)

    changes = ", ".join(f"{k}={v}" for k, v in body.items())
    print(f"\n  Updating record {args.record_id} in {args.domain}: {changes}")
    api_request("PUT", f"/2/zones/{args.domain}/records/{args.record_id}", token, json_data=body)
    print(f"  {green('✓')} Record {bold(str(args.record_id))} updated.\n")


def cmd_dns_delete(args):
    """Delete a DNS record."""
    token = get_token()

    if not args.yes:
        data = api_request("GET", f"/2/zones/{args.domain}/records", token)
        records = data.get("data", [])
        target_rec = next((r for r in records if str(r.get("id")) == str(args.record_id)), None)
        if target_rec:
            source = target_rec.get("source", "@")
            if source == ".":
                source = "@"
            print(f"\n  Record: {cyan(target_rec.get('type'))} {source} → {target_rec.get('target')}")

        confirm = input(f"  Delete record {args.record_id} from {args.domain}? [y/N] ")
        if confirm.lower() not in ("y", "yes"):
            print(f"  {dim('Aborted.')}")
            return

    api_request("DELETE", f"/2/zones/{args.domain}/records/{args.record_id}", token)
    print(f"  {green('✓')} Record {bold(str(args.record_id))} deleted from {args.domain}.\n")


# ── CLI setup ─────────────────────────────────────────────────────────────────


def main():
    load_env_file()

    parser = argparse.ArgumentParser(
        prog="infomaniak",
        description="Manage Infomaniak services from the command line.",
        epilog=f"Get started: {bold('infomaniak setup')}",
    )
    parser.add_argument("--version", "-V", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="service", help="Service to manage")

    # ── setup ──────────────────────────────────────────────────────────────
    sp_setup = subparsers.add_parser("setup", help="Configure your API token")
    sp_setup.set_defaults(func=cmd_setup)

    # ── dns ────────────────────────────────────────────────────────────────
    dns_parser = subparsers.add_parser("dns", help="Manage DNS records and domains")
    dns_sub = dns_parser.add_subparsers(dest="command")

    # dns domains
    sp = dns_sub.add_parser("domains", help="List all domains on your account")
    sp.set_defaults(func=cmd_dns_domains)

    # dns records
    sp = dns_sub.add_parser("records", help="List DNS records for a domain")
    sp.add_argument("domain", help="Domain name (e.g. example.com)")
    sp.add_argument("--type", "-t", help="Filter by record type (A, AAAA, CNAME, MX, TXT, etc.)")
    sp.set_defaults(func=cmd_dns_records)

    # dns check
    sp = dns_sub.add_parser("check", help="Check if a DNS record resolves correctly")
    sp.add_argument("domain", help="Domain name")
    sp.add_argument("record_id", help="Record ID to check")
    sp.set_defaults(func=cmd_dns_check)

    # dns add
    sp = dns_sub.add_parser("add", help="Create a DNS record")
    sp.add_argument("domain", help="Domain name (e.g. example.com)")
    sp.add_argument("type", help="Record type (A, AAAA, CNAME, MX, TXT, SRV, NS)")
    sp.add_argument("source", help="Record name (e.g. 'www', 'api', '@' for root)")
    sp.add_argument("target", help="Record value (e.g. IP address, hostname)")
    sp.add_argument("--ttl", type=int, default=3600, help="TTL in seconds (default: 3600)")
    sp.set_defaults(func=cmd_dns_add)

    # dns update
    sp = dns_sub.add_parser("update", help="Update a DNS record")
    sp.add_argument("domain", help="Domain name")
    sp.add_argument("record_id", help="Record ID to update")
    sp.add_argument("--target", help="New target value")
    sp.add_argument("--ttl", type=int, help="New TTL in seconds")
    sp.set_defaults(func=cmd_dns_update)

    # dns delete
    sp = dns_sub.add_parser("delete", help="Delete a DNS record")
    sp.add_argument("domain", help="Domain name")
    sp.add_argument("record_id", help="Record ID to delete")
    sp.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    sp.set_defaults(func=cmd_dns_delete)

    args = parser.parse_args()

    if not args.service:
        parser.print_help()
        sys.exit(1)

    if args.service == "dns" and not args.command:
        dns_parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
