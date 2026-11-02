"""Configuration management — token storage, env loading, auth."""

import configparser
import os
import sys
from pathlib import Path

from infomaniak_cli.api import api_request
from infomaniak_cli.output import bold, red


CONFIG_DIR = Path.home() / ".config" / "infomaniak"
CONFIG_FILE = CONFIG_DIR / "config.ini"


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
    fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        os.fchmod(f.fileno(), 0o600)
        config.write(f)


def load_env_file():
    """Load variables from .env file if it exists."""
    for env_path in [Path(".env"), Path(__file__).resolve().parent.parent / ".env"]:
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
