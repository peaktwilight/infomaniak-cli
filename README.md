# infomaniak

[![PyPI version](https://img.shields.io/pypi/v/infomaniak)](https://pypi.org/project/infomaniak/)
[![Tests](https://github.com/peaktwilight/infomaniak-cli/actions/workflows/test.yml/badge.svg)](https://github.com/peaktwilight/infomaniak-cli/actions/workflows/test.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/infomaniak)](https://pypi.org/project/infomaniak/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

CLI tool for managing your [Infomaniak](https://www.infomaniak.com) services from the terminal.

Manage **DNS**, **mail**, **hosting**, **kDrive**, **products**, and more — all from one command.

## Install

### With pipx (recommended)

```bash
pipx install infomaniak
```

### With pip

```bash
pip install infomaniak
```

### From source

```bash
git clone https://github.com/peaktwilight/infomaniak-cli.git
cd infomaniak-cli
pip install .
```

## Getting started

```bash
infomaniak setup
```

The setup wizard will:

1. Open the Infomaniak token page in your browser
2. Prompt you to paste your API token
3. Validate it against the API
4. Check which optional scopes are enabled
5. Save it to `~/.config/infomaniak/config.ini`

**Required scopes:** `accounts`, `domain:read`, `dns:read`, `dns:write`

**Optional scopes:** `mail` (mailboxes), `web` (hosting details), `drive` (kDrive details)

### Alternative configuration

```bash
# Environment variable
export INFOMANIAK_API_TOKEN=your-token-here
```

Token lookup order: environment variable → config file → `.env` file.

## Commands

### DNS

```bash
infomaniak dns domains                                    # List all domains
infomaniak dns records example.com                        # List DNS records
infomaniak dns records example.com --type CNAME           # Filter by type
infomaniak dns check example.com 12345                    # Check record health
infomaniak dns add example.com A blog 93.184.216.34       # Create record
infomaniak dns update example.com 12345 --target 1.2.3.4  # Update record
infomaniak dns delete example.com 12345                   # Delete record
infomaniak dns export example.com                         # Export as JSON
infomaniak dns export example.com -f csv -o records.csv   # Export as CSV
infomaniak dns import example.com records.json            # Import from file
infomaniak dns diff example.com records.json              # Compare live vs file
infomaniak dns sync example.com desired.json --dry-run    # Sync (terraform-style)
infomaniak dns clone source.com target.com                # Clone between domains
infomaniak dns search "76.76.21"                          # Search across all domains
infomaniak dns backup                                     # Backup all domains
infomaniak dns audit                                      # Audit all domains (SPF/DMARC/DKIM)
infomaniak dns audit example.com                          # Audit single domain
infomaniak dns zone example.com                           # Generate BIND zone file
infomaniak dns propagation example.com                    # Check global DNS propagation
infomaniak dns propagation example.com -n www -t CNAME    # Check specific record
```

`dns sync` updates changed records in place, then deletes records that are no longer
in the file. It stops at the first failed request and is not atomic, so run it with
`--dry-run` first and keep a `dns export` backup.

### Domains

```bash
infomaniak domains                                        # List all domains with expiry dates
infomaniak domains --warn 60                              # Warn if expiring within 60 days
```

### Account & Products

```bash
infomaniak account                                        # Account overview
infomaniak products                                       # List all products
infomaniak products --type email_hosting                  # Filter by service
infomaniak status                                         # Service status overview
```

### Mail

```bash
infomaniak mail list                                      # List mail hostings
infomaniak mail mailboxes <id>                            # List mailboxes (needs 'mail' scope)
```

### Hosting & kDrive

```bash
infomaniak hosting list                                   # List web hostings
infomaniak drive list                                     # List kDrive instances
```

### Configuration

```bash
infomaniak config show                                    # Show token, source, scopes
infomaniak setup                                          # Interactive setup wizard
```

### JSON output

Add `--json` to any read command for machine-readable output:

```bash
infomaniak dns domains --json
infomaniak dns records example.com --json
infomaniak dns search vercel --json
infomaniak products --json
infomaniak account --json
infomaniak status --json
```

## Example output

```
$ infomaniak account

  Account

  Name:  John Doe
  ID:    12345
  Total: 5 products

  Service          Count  Examples
  ───────────────  ─────  ─────────────────────────
  domain           2      example.com, example.org
  email_hosting    2      example.com, example.org
  drive            1      example.com

$ infomaniak dns search vercel

  Search: "vercel" — 3 matches across 10 domains

  Domain         ID      Type   Name  Target                   TTL
  ─────────────  ──────  ─────  ────  ───────────────────────  ────
  example.com    200001  CNAME  @     cname.vercel-dns.com     300
  example.com    200002  CNAME  www   cname.vercel-dns.com     300
  example.org    300001  CNAME  @     cname.vercel-dns.com     300

$ infomaniak dns sync example.com desired.json --dry-run

  DNS sync plan for example.com

  File: desired.json
  + 1 to create  - 2 to delete  8 unchanged

  Create:
    + A  new-app → 198.51.100.1

  Delete:
    - CNAME  old-cdn → old.cdn.example.net
    - TXT  _old-verify → verify=abc123

  Dry run — no changes applied.

$ infomaniak dns audit

  DNS Audit
  ────────

  Scanning 10 domain(s)...

  ! No SPF record found — Email spoofing protection
    → legacy-site.com

  ! No DMARC record found — Email authentication policy
    → legacy-site.com
    → staging.org

  Summary: 10 domains scanned
    8 clean
    2 with issues (3 total findings)

$ infomaniak dns propagation example.com

  DNS Propagation: A example.com

  Resolver    IP              Result
  ──────────  ──────────────  ───────────
  Google      8.8.8.8         93.184.216.34
  Cloudflare  1.1.1.1         93.184.216.34
  Quad9       9.9.9.9         93.184.216.34
  OpenDNS     208.67.222.222  93.184.216.34

  All resolvers agree. DNS is fully propagated.

$ infomaniak domains

  Domains (3)

  Domain           Expires     Days Left  Status
  ───────────────  ──────────  ─────────  ────────
  expiring.com     2026-04-01  17         expiring
  example.com      2027-01-15  306        active
  example.org      2027-06-20  462        active

  Warning: 1 domain(s) expiring within 30 days:

    ! expiring.com — 17 days remaining

$ infomaniak status

  Service Status — 5 products

  Service          Total  Active  Issues
  ───────────────  ─────  ──────  ──────
  domain           2      2       none
  email_hosting    2      2       none
  drive            1      1       none

  ✓ All services operational.
```

## API reference

Built on the [Infomaniak API](https://developer.infomaniak.com/docs/api):

| Endpoint | Description |
|---|---|
| `GET /1/accounts` | Account info |
| `GET /1/products` | List all products |
| `GET /1/domain/account/{id}` | List domains |
| `GET /2/zones/{zone}/records` | List DNS records |
| `POST /2/zones/{zone}/records` | Create record |
| `PUT /2/zones/{zone}/records/{id}` | Update record |
| `DELETE /2/zones/{zone}/records/{id}` | Delete record |
| `GET /2/zones/{zone}/records/{id}/check` | Check record health |
| `GET /1/mail_hostings/{id}/mailboxes` | List mailboxes |

## License

MIT
