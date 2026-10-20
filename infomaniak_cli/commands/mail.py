"""Mail hosting commands."""

import sys
from urllib.parse import quote

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

    headers = ["Email", "Type"]
    rows = []
    for m in mailboxes:
        email = m.get("mailbox", m.get("mailbox_idn", "?"))
        mtype = m.get("type") or dim("standard")
        if m.get("is_free_mail"):
            mtype = dim("free")

        rows.append([email, mtype])

    print(f"\n  {bold(f'Mailboxes ({len(rows)})')}\n")
    print_table(headers, rows)
    print()


def _mailbox_path(args, suffix=""):
    name = quote(args.mailbox_name, safe="")
    return f"/1/mail_hostings/{args.mail_hosting_id}/mailboxes/{name}{suffix}"


def _mailbox_get(args, suffix=""):
    token = get_token()
    return api_request("GET", _mailbox_path(args, suffix), token).get("data", {})


def _flag(value):
    # The API returns some flags as the strings "0" and "1".
    return "yes" if str(value).lower() in ("1", "true") else "no"


def cmd_mail_show(args):
    """Show details of one mailbox. Requires 'mail' scope."""
    data = _mailbox_get(args)

    if getattr(args, "json", False):
        output_json(data)

    rows = [
        ["Email", data.get("mailbox", "?")],
        ["Free mail", _flag(data.get("is_free_mail"))],
        ["Limited", _flag(data.get("is_limited"))],
        ["Note", data.get("note") or "-"],
    ]
    print(f"\n  {bold('Mailbox')}\n")
    print_table(["Field", "Value"], rows)
    print()


def cmd_mail_aliases(args):
    """List the aliases of one mailbox. Requires 'mail' scope."""
    data = _mailbox_get(args, "/aliases")

    if getattr(args, "json", False):
        output_json(data)

    aliases = data.get("aliases", [])
    if not aliases:
        print(f"  {dim('No aliases found.')}")
        return

    print(f"\n  {bold(f'Aliases ({len(aliases)})')}\n")
    print_table(["Alias"], [[a] for a in aliases])
    print()


def cmd_mail_forwarding(args):
    """Show forwarding settings of one mailbox. Requires 'mail' scope."""
    data = _mailbox_get(args, "/forwarding_addresses")

    if getattr(args, "json", False):
        output_json(data)

    rows = [
        ["Enabled", _flag(data.get("is_enabled"))],
        ["Keep no local copy", _flag(data.get("has_dont_deliver"))],
        ["Forward spam", _flag(data.get("has_forward_spam"))],
    ]
    # "redirect_adresses" is spelled this way in the API.
    for address in data.get("redirect_adresses", []):
        rows.append(["Forward to", address.get("email", "?")])

    print(f"\n  {bold('Forwarding')}\n")
    print_table(["Setting", "Value"], rows)
    print()


def _write(args, method, suffix, summary, body=None, confirm=None):
    """Preview, optionally confirm, then send one mailbox change."""
    dry_run = getattr(args, "dry_run", False)
    print(f"\n  {'Would ' + summary if dry_run else summary[0].upper() + summary[1:]}")
    if dry_run:
        print(f"  {dim('Dry run — no changes applied.')}\n")
        return
    if confirm and not getattr(args, "yes", False):
        try:
            answer = input(f"  {confirm} [y/N] ")
        except EOFError:
            print(f"\n  {red('✗')} No terminal to confirm on. Pass --yes to continue without asking.")
            sys.exit(1)
        if answer.lower() not in ("y", "yes"):
            print(f"  {dim('Aborted.')}")
            return
    api_request(method, _mailbox_path(args, suffix), get_token(), json_data=body)
    print(f"  {green('✓')} Done.\n")


def _local_part(args):
    if "@" in args.alias:
        print(f"  {red('✗')} Give the alias without the domain, e.g. 'support' for support@example.com.")
        sys.exit(1)
    return args.alias


def cmd_mail_alias_add(args):
    """Add an alias to a mailbox. Requires 'mail' scope."""
    alias = _local_part(args)
    _write(args, "POST", "/aliases", f"add alias {bold(alias)} to mailbox {args.mailbox_name}",
           body={"alias": alias})


def cmd_mail_alias_delete(args):
    """Remove an alias from a mailbox. Requires 'mail' scope."""
    alias = _local_part(args)
    _write(args, "DELETE", f"/aliases/{quote(alias, safe='')}",
           f"remove alias {bold(alias)} from mailbox {args.mailbox_name}",
           confirm=f"Remove alias {alias}?")


def cmd_mail_forward_add(args):
    """Forward a mailbox's mail to another address. Requires 'mail' scope."""
    if "@" not in args.address:
        print(f"  {red('✗')} Give a full email address to forward to.")
        sys.exit(1)
    _write(args, "POST", "/forwarding_addresses",
           f"forward mail for {args.mailbox_name} to {bold(args.address)}",
           body={"redirect_address": args.address},
           confirm=f"Forward all mail for {args.mailbox_name} to {args.address}?")


def cmd_mail_forward_delete(args):
    """Stop forwarding a mailbox's mail to an address. Requires 'mail' scope."""
    _write(args, "DELETE", f"/forwarding_addresses/{quote(args.address, safe='')}",
           f"stop forwarding mail for {args.mailbox_name} to {bold(args.address)}",
           confirm=f"Stop forwarding to {args.address}?")
