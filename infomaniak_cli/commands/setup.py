"""Interactive setup wizard."""

import io
import sys
import getpass
import webbrowser

from infomaniak_cli.api import api_request
from infomaniak_cli.config import CONFIG_FILE, load_config, save_config
from infomaniak_cli.output import bold, cyan, dim, green, red, yellow


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
    print(f"    {bold('Required:')}")
    print(f"    {cyan('•')} accounts")
    print(f"    {cyan('•')} domain:read")
    print(f"    {cyan('•')} dns:read")
    print(f"    {cyan('•')} dns:write")
    print(f"\n    {bold('Optional')} {dim('(for additional features)')}:")
    print(f"    {cyan('•')} mail          {dim('— list mailboxes')}")
    print(f"    {cyan('•')} web           {dim('— web hosting details')}")
    print(f"    {cyan('•')} drive         {dim('— kDrive details')}\n")

    url = "https://manager.infomaniak.com/v3/infomaniak-api"
    choice = input(f"  Press {bold('Enter')} to open the token page, or {bold('s')} to skip: ")
    if choice.lower() != "s":
        webbrowser.open(url)
        print(f"  {dim(f'Opened {url}')}\n")
    else:
        print(f"  {dim(f'Go to: {url}')}\n")

    token_prompt = "  Paste your API token: "
    token_reader = getpass.getpass if sys.stdin.isatty() else input
    token = token_reader(token_prompt).strip()
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

    # Probe scopes
    print(f"\n  {bold('Checking scopes...')}\n")

    # Probe optional scopes by hitting endpoints that require them.
    # We check the response for scope errors specifically, not other failures.
    optional_scopes = [
        ("mail", f"/1/mail_hostings?account_id={account_id}", "list mailboxes"),
        ("web", f"/1/web_hostings?account_id={account_id}", "web hosting details"),
    ]

    import requests as req_lib
    for scope_name, path, desc in optional_scopes:
        resp = req_lib.get(
            f"https://api.infomaniak.com{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        try:
            body = resp.json()
        except ValueError:
            continue
        err = body.get("error", {})
        if err.get("code") == "all_scopes":
            print(f"    {dim('✗')} {scope_name:12} {dim('— not enabled')} {dim(f'({desc})')}")
        else:
            print(f"    {green('✓')} {scope_name:12} {dim(f'({desc})')}")

    # Save
    print()
    save_config(token, account_id)
    print(f"  {green('✓')} Saved to {dim(str(CONFIG_FILE))}\n")
    print(f"  You're all set! Try: {bold('infomaniak dns domains')}\n")
