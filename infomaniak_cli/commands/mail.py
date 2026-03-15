"""Mail hosting commands."""

import sys

from infomaniak_cli.api import api_request, api_request_paginated
from infomaniak_cli.config import get_account_id, get_token
from infomaniak_cli.output import bold, cyan, dim, green, output_json, print_table, red, yellow


def cmd_mail_list(args):
    """List mail hosting services."""
    token = get_token()
    account_id = get_account_id(token)

    products = api_request_paginated(
        "/1/products", token,
        params={"account_id": account_id, "service_name": "email_hosting"},
    )

    if getattr(args, "json", False):
        output_json(products)

    if not products:
        print(f"  {dim('No mail hostings found.')}")
        return

    headers = ["ID", "Domain", "Status"]
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

        rows.append([
            p.get("id", "?"),
            p.get("customer_name", "?"),
            status,
        ])

    print(f"\n  {bold(f'Mail Hostings ({len(rows)})')}\n")
    print_table(headers, rows)
    print()


def cmd_mail_mailboxes(args):
    """List mailboxes for a mail hosting. Requires 'mail' scope."""
    token = get_token()
    mail_hosting_id = args.mail_hosting_id

    try:
        data = api_request("GET", f"/1/mail_hostings/{mail_hosting_id}/mailboxes", token)
    except SystemExit:
        print(f"\n  {yellow('Hint')}: This command requires the {bold('mail')} scope on your API token.")
        print(f"  Regenerate your token at https://manager.infomaniak.com/v3/infomaniak-api\n")
        sys.exit(1)

    mailboxes = data.get("data", [])

    if getattr(args, "json", False):
        output_json(mailboxes)

    if not mailboxes:
        print(f"  {dim('No mailboxes found.')}")
        return

    headers = ["ID", "Email", "Size"]
    rows = []
    for m in mailboxes:
        email = m.get("mailbox_name", "?")
        domain = m.get("mailbox_domain", "")
        if domain:
            email = f"{email}@{domain}"
        size_mb = m.get("size_used", 0)
        if size_mb:
            size_display = f"{size_mb / 1024 / 1024:.0f} MB" if size_mb > 1024 * 1024 else f"{size_mb / 1024:.0f} KB"
        else:
            size_display = dim("0")

        rows.append([
            m.get("id", "?"),
            email,
            size_display,
        ])

    print(f"\n  {bold(f'Mailboxes ({len(rows)})')}\n")
    print_table(headers, rows)
    print()
