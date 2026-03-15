"""kDrive commands."""

from infomaniak_cli.api import api_request_paginated
from infomaniak_cli.config import get_account_id, get_token
from infomaniak_cli.output import bold, cyan, dim, green, output_json, print_table, red, yellow


def cmd_drive_list(args):
    """List kDrive instances."""
    token = get_token()
    account_id = get_account_id(token)

    products = api_request_paginated(
        "/1/products", token,
        params={"account_id": account_id, "service_name": "drive"},
    )

    if getattr(args, "json", False):
        output_json(products)

    if not products:
        print(f"  {dim('No kDrive instances found.')}")
        return

    headers = ["ID", "Name", "Free", "Status"]
    rows = []
    for p in products:
        if p.get("has_maintenance"):
            status = yellow("maintenance")
        elif p.get("is_locked"):
            status = red("locked")
        elif p.get("has_operation_in_progress"):
            status = yellow("in progress")
        else:
            status = green("active")

        is_free = dim("free") if p.get("is_free") or p.get("is_zero_price") else cyan("paid")

        rows.append([
            p.get("id", "?"),
            p.get("customer_name", p.get("internal_name", "?")),
            is_free,
            status,
        ])

    print(f"\n  {bold(f'kDrive ({len(rows)})')}\n")
    print_table(headers, rows)
    print()
