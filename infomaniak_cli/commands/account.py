"""Account overview command."""

import io
import sys

from infomaniak_cli.api import api_request, api_request_paginated
from infomaniak_cli.config import get_account_id, get_token
from infomaniak_cli.output import bold, cyan, dim, green, output_json, print_table


def cmd_account(args):
    """Show account overview with product summary."""
    token = get_token()
    account_id = get_account_id(token)

    # Try to get account info (needs 'accounts' scope)
    account = None
    try:
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()  # suppress error output from api_request
        data = api_request("GET", "/1/accounts", token)
        sys.stdout = old_stdout
        accounts = data.get("data", [])
        account = next((a for a in accounts if str(a.get("id")) == str(account_id)), None)
    except SystemExit:
        sys.stdout = old_stdout  # restore stdout

    # Get all products
    products = api_request_paginated(
        "/1/products", token,
        params={"account_id": account_id},
    )

    if getattr(args, "json", False):
        output_json({
            "account": account,
            "products": products,
            "summary": _build_summary(products),
        })

    print(f"\n  {bold('Account')}\n")

    if account:
        print(f"  {cyan('Name')}:  {account.get('name', '?')}")
        print(f"  {cyan('ID')}:    {account.get('id', '?')}")
    else:
        print(f"  {cyan('ID')}:    {account_id}")

    print(f"  {cyan('Total')}: {len(products)} products\n")

    # Group by service
    summary = _build_summary(products)
    if summary:
        headers = ["Service", "Count", "Examples"]
        rows = []
        for svc, info in sorted(summary.items()):
            names = info["names"]
            examples = ", ".join(names[:3])
            if len(names) > 3:
                extra = len(names) - 3
                examples += f" {dim(f'+{extra} more')}"
            rows.append([
                cyan(svc),
                info["count"],
                examples,
            ])
        print_table(headers, rows)
    print()


def _build_summary(products):
    """Group products by service name."""
    summary = {}
    for p in products:
        svc = p.get("service_name", "unknown")
        if svc not in summary:
            summary[svc] = {"count": 0, "names": []}
        summary[svc]["count"] += 1
        name = p.get("customer_name", p.get("internal_name", ""))
        if name and name not in summary[svc]["names"]:
            summary[svc]["names"].append(name)
    return summary
