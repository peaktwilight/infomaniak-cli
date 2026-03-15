# infomaniak

[![PyPI version](https://img.shields.io/pypi/v/infomaniak)](https://pypi.org/project/infomaniak/)
[![Tests](https://github.com/peaktwilight/infomaniak-cli/actions/workflows/test.yml/badge.svg)](https://github.com/peaktwilight/infomaniak-cli/actions/workflows/test.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/infomaniak)](https://pypi.org/project/infomaniak/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

CLI tool for managing your [Infomaniak](https://www.infomaniak.com) services from the terminal.

Supports **DNS management**, **mail hosting**, **product listing**, **service status**, and more.

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
4. Save it to `~/.config/infomaniak/config.ini`

You'll need a token with these scopes: `accounts`, `domain:read`, `dns:read`, `dns:write`.

### Alternative configuration

You can also set the token manually:

```bash
# Environment variable
export INFOMANIAK_API_TOKEN=your-token-here

# Or .env file
cp .env.example .env
```

Token lookup order: environment variable → config file → `.env` file.

## Usage

### DNS

```bash
# List all domains
infomaniak dns domains

# List DNS records for a domain
infomaniak dns records example.com

# Filter by record type
infomaniak dns records example.com --type CNAME

# Check if a record resolves correctly
infomaniak dns check example.com 12345

# Create a new record
infomaniak dns add example.com A blog 93.184.216.34
infomaniak dns add example.com CNAME app target.example.net --ttl 300

# Update a record
infomaniak dns update example.com 12345 --target 93.184.216.35

# Delete a record (with confirmation)
infomaniak dns delete example.com 12345

# Export records as JSON or CSV
infomaniak dns export example.com
infomaniak dns export example.com --format csv --output records.csv

# Import records from a file
infomaniak dns import example.com records.json
infomaniak dns import example.com records.csv --yes

# Compare live records against a local file
infomaniak dns diff example.com records.json

# Clone records from one domain to another (skips NS/SOA)
infomaniak dns clone source.com target.com

# Search for a record across all domains
infomaniak dns search "76.76.21"
infomaniak dns search vercel

# Backup all domains to a directory
infomaniak dns backup
infomaniak dns backup --output my-backup --format csv

# Sync live DNS to match a file (like terraform apply)
infomaniak dns sync example.com desired-state.json --dry-run
infomaniak dns sync example.com desired-state.json --yes
```

### Account

```bash
# Show account overview with product summary
infomaniak account
```

### Products

```bash
# List all products on your account
infomaniak products

# Filter by service type
infomaniak products --type domain
infomaniak products --type email_hosting
```

### Hosting

```bash
# List web hosting services
infomaniak hosting list
```

### kDrive

```bash
# List kDrive instances
infomaniak drive list
```

### Mail

```bash
# List all mail hosting services
infomaniak mail list

# List mailboxes (requires 'mail' scope on your token)
infomaniak mail mailboxes <mail_hosting_id>
```

### Status

```bash
# Service status overview — shows all products grouped by service
infomaniak status
```

### Configuration

```bash
# Show current configuration (token source, account ID, config file path)
infomaniak config show
```

### JSON output

Add `--json` to any read command for machine-readable output:

```bash
infomaniak dns domains --json
infomaniak dns records example.com --json
infomaniak dns diff example.com records.json --json
infomaniak products --json
infomaniak account --json
infomaniak status --json
```

### Example output

```
$ infomaniak dns domains

  Domains (2)

  ID       Domain           DNSSEC  DNS@IK
  ───────  ───────────────  ──────  ──────
  100001   example.com      yes     yes
  100002   example.org      yes     yes

$ infomaniak dns diff example.com backup.json

  DNS diff for example.com

  File: backup.json
  Live: 12 records, File: 10 records

  In file but not live (1):

    + A  old-server → 93.184.216.34  (TTL: 3600)

  Live but not in file (3):

    - A  new-app → 198.51.100.1  (TTL: 300)
    - CNAME  cdn → cdn.example.net  (TTL: 300)
    - TXT  _verify → site-verification=abc123  (TTL: 3600)

  9 records match.

$ infomaniak status

  Service Status — 5 products

  Service          Total  Active  Issues
  ───────────────  ─────  ──────  ──────
  domain           2      2       none
  email_hosting    2      2       none
  drive            1      1       none

  ✓ All services operational.
```

## Why not OAuth?

Infomaniak's OAuth2 apps only support `openid`, `profile`, `email`, and `phone` scopes. The DNS management scopes (`accounts`, `domain:read`, `dns:read`, `dns:write`) are only available through API tokens — so there's no way to implement a browser-based login flow.

## API reference

Built on the [Infomaniak API](https://developer.infomaniak.com/docs/api):

| Endpoint | Description |
|---|---|
| `GET /1/products` | List all products |
| `GET /1/domain/account/{id}` | List domains |
| `GET /2/zones/{zone}/records` | List DNS records |
| `POST /2/zones/{zone}/records` | Create record |
| `PUT /2/zones/{zone}/records/{id}` | Update record |
| `DELETE /2/zones/{zone}/records/{id}` | Delete record |
| `GET /2/zones/{zone}/records/{id}/check` | Check record health |

## License

MIT
