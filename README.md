# infomaniak

[![PyPI version](https://img.shields.io/pypi/v/infomaniak)](https://pypi.org/project/infomaniak/)
[![Python versions](https://img.shields.io/pypi/pyversions/infomaniak)](https://pypi.org/project/infomaniak/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

CLI tool for managing your [Infomaniak](https://www.infomaniak.com) services from the terminal.

Currently supports **DNS management** — more services planned.

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
infomaniak dns update example.com 12345 --ttl 300

# Delete a record (with confirmation)
infomaniak dns delete example.com 12345

# Delete without confirmation
infomaniak dns delete example.com 12345 --yes

# Show version
infomaniak --version
```

### Example output

```
$ infomaniak dns domains

  Domains (2)

  ID       Domain           DNSSEC  DNS@IK
  ───────  ───────────────  ──────  ──────
  100001   example.com      yes     yes
  100002   example.org      yes     yes

$ infomaniak dns records example.com --type A

  DNS records for example.com — 2 records

  ID      Type  Name  Target          TTL
  ──────  ────  ────  ──────────────  ────
  200001  A     @     93.184.216.34   3600
  200002  A     www   93.184.216.34   3600
```

## Why not OAuth?

Infomaniak's OAuth2 apps only support `openid`, `profile`, `email`, and `phone` scopes. The DNS management scopes (`accounts`, `domain:read`, `dns:read`, `dns:write`) are only available through API tokens — so there's no way to implement a browser-based login flow.

## API reference

Built on the [Infomaniak API](https://developer.infomaniak.com/docs/api):

| Endpoint | Description |
|---|---|
| `GET /1/domain/account/{id}` | List domains |
| `GET /2/zones/{zone}/records` | List DNS records |
| `POST /2/zones/{zone}/records` | Create record |
| `PUT /2/zones/{zone}/records/{id}` | Update record |
| `DELETE /2/zones/{zone}/records/{id}` | Delete record |
| `GET /2/zones/{zone}/records/{id}/check` | Check record health |

## License

MIT
