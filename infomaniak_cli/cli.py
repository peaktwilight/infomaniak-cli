"""CLI argument parsing and entry point."""

import argparse
import sys

from infomaniak_cli import __version__
from infomaniak_cli.commands.account import cmd_account
from infomaniak_cli.commands.config import cmd_config_show
from infomaniak_cli.commands.dns import (
    cmd_dns_add,
    cmd_dns_backup,
    cmd_dns_check,
    cmd_dns_clone,
    cmd_dns_delete,
    cmd_dns_diff,
    cmd_dns_domains,
    cmd_dns_export,
    cmd_dns_import,
    cmd_dns_records,
    cmd_dns_search,
    cmd_dns_sync,
    cmd_dns_update,
)
from infomaniak_cli.commands.drive import cmd_drive_list
from infomaniak_cli.commands.hosting import cmd_hosting_list
from infomaniak_cli.commands.mail import cmd_mail_list, cmd_mail_mailboxes
from infomaniak_cli.commands.products import cmd_products
from infomaniak_cli.commands.setup import cmd_setup
from infomaniak_cli.commands.status import cmd_status
from infomaniak_cli.config import load_env_file
from infomaniak_cli.output import bold


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
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.set_defaults(func=cmd_dns_domains)

    # dns records
    sp = dns_sub.add_parser("records", help="List DNS records for a domain")
    sp.add_argument("domain", help="Domain name (e.g. example.com)")
    sp.add_argument("--type", "-t", help="Filter by record type (A, AAAA, CNAME, MX, TXT, etc.)")
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.set_defaults(func=cmd_dns_records)

    # dns check
    sp = dns_sub.add_parser("check", help="Check if a DNS record resolves correctly")
    sp.add_argument("domain", help="Domain name")
    sp.add_argument("record_id", help="Record ID to check")
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.set_defaults(func=cmd_dns_check)

    # dns add
    sp = dns_sub.add_parser("add", help="Create a DNS record")
    sp.add_argument("domain", help="Domain name (e.g. example.com)")
    sp.add_argument("type", help="Record type (A, AAAA, CNAME, MX, TXT, SRV, NS)")
    sp.add_argument("source", help="Record name (e.g. 'www', 'api', '@' for root)")
    sp.add_argument("target", help="Record value (e.g. IP address, hostname)")
    sp.add_argument("--ttl", type=int, default=3600, help="TTL in seconds (default: 3600)")
    sp.add_argument("--json", action="store_true", help="Output as JSON")
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

    # dns export
    sp = dns_sub.add_parser("export", help="Export DNS records as JSON or CSV")
    sp.add_argument("domain", help="Domain name")
    sp.add_argument("--format", "-f", choices=["json", "csv"], default="json", help="Output format (default: json)")
    sp.add_argument("--output", "-o", help="Output file path (default: stdout)")
    sp.set_defaults(func=cmd_dns_export)

    # dns import
    sp = dns_sub.add_parser("import", help="Import DNS records from JSON or CSV file")
    sp.add_argument("domain", help="Domain name")
    sp.add_argument("file", help="Path to JSON or CSV file")
    sp.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    sp.set_defaults(func=cmd_dns_import)

    # dns diff
    sp = dns_sub.add_parser("diff", help="Compare live DNS records against a local file")
    sp.add_argument("domain", help="Domain name")
    sp.add_argument("file", help="Path to JSON or CSV file to compare against")
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.set_defaults(func=cmd_dns_diff)

    # dns clone
    sp = dns_sub.add_parser("clone", help="Clone DNS records from one domain to another")
    sp.add_argument("source_domain", help="Source domain to copy from")
    sp.add_argument("target_domain", help="Target domain to copy to")
    sp.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    sp.set_defaults(func=cmd_dns_clone)

    # dns search
    sp = dns_sub.add_parser("search", help="Search DNS records across all domains")
    sp.add_argument("query", help="Search term (matches name, target, or type)")
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.set_defaults(func=cmd_dns_search)

    # dns backup
    sp = dns_sub.add_parser("backup", help="Backup DNS records for all domains")
    sp.add_argument("--output", "-o", default="dns-backup", help="Output directory (default: dns-backup)")
    sp.add_argument("--format", "-f", choices=["json", "csv"], default="json", help="Output format (default: json)")
    sp.set_defaults(func=cmd_dns_backup)

    # dns sync
    sp = dns_sub.add_parser("sync", help="Sync DNS records from file to live (like terraform apply)")
    sp.add_argument("domain", help="Domain name")
    sp.add_argument("file", help="Path to JSON or CSV file with desired state")
    sp.add_argument("--dry-run", action="store_true", help="Show plan without applying changes")
    sp.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    sp.set_defaults(func=cmd_dns_sync)

    # ── config ─────────────────────────────────────────────────────────────
    config_parser = subparsers.add_parser("config", help="View configuration")
    config_sub = config_parser.add_subparsers(dest="command")

    sp = config_sub.add_parser("show", help="Show current configuration")
    sp.set_defaults(func=cmd_config_show)

    # ── account ────────────────────────────────────────────────────────────
    sp_account = subparsers.add_parser("account", help="Show account overview")
    sp_account.add_argument("--json", action="store_true", help="Output as JSON")
    sp_account.set_defaults(func=cmd_account)

    # ── products ───────────────────────────────────────────────────────────
    sp_products = subparsers.add_parser("products", help="List all products on your account")
    sp_products.add_argument("--type", "-t", dest="service_filter", help="Filter by service type (e.g. domain, email_hosting)")
    sp_products.add_argument("--json", action="store_true", help="Output as JSON")
    sp_products.set_defaults(func=cmd_products)

    # ── hosting ────────────────────────────────────────────────────────────
    hosting_parser = subparsers.add_parser("hosting", help="Manage web hosting services")
    hosting_sub = hosting_parser.add_subparsers(dest="command")

    sp = hosting_sub.add_parser("list", help="List web hosting services")
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.set_defaults(func=cmd_hosting_list)

    # ── drive ──────────────────────────────────────────────────────────────
    drive_parser = subparsers.add_parser("drive", help="Manage kDrive instances")
    drive_sub = drive_parser.add_subparsers(dest="command")

    sp = drive_sub.add_parser("list", help="List kDrive instances")
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.set_defaults(func=cmd_drive_list)

    # ── mail ───────────────────────────────────────────────────────────────
    mail_parser = subparsers.add_parser("mail", help="Manage mail services")
    mail_sub = mail_parser.add_subparsers(dest="command")

    sp = mail_sub.add_parser("list", help="List mail hosting services")
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.set_defaults(func=cmd_mail_list)

    sp = mail_sub.add_parser("mailboxes", help="List mailboxes (requires 'mail' scope)")
    sp.add_argument("mail_hosting_id", help="Mail hosting ID (from 'infomaniak mail list')")
    sp.add_argument("--json", action="store_true", help="Output as JSON")
    sp.set_defaults(func=cmd_mail_mailboxes)

    # ── status ─────────────────────────────────────────────────────────────
    sp_status = subparsers.add_parser("status", help="Service status overview")
    sp_status.add_argument("--json", action="store_true", help="Output as JSON")
    sp_status.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if not args.service:
        parser.print_help()
        sys.exit(1)

    if args.service == "dns" and not getattr(args, "command", None):
        dns_parser.print_help()
        sys.exit(1)

    if args.service == "hosting" and not getattr(args, "command", None):
        hosting_parser.print_help()
        sys.exit(1)

    if args.service == "drive" and not getattr(args, "command", None):
        drive_parser.print_help()
        sys.exit(1)

    if args.service == "mail" and not getattr(args, "command", None):
        mail_parser.print_help()
        sys.exit(1)

    if args.service == "config" and not getattr(args, "command", None):
        config_parser.print_help()
        sys.exit(1)

    args.func(args)
