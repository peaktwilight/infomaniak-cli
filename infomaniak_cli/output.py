"""Terminal colors, table formatting, and output helpers."""

import json
import re
import sys


_COLOR = sys.stdout.isatty()
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _COLOR else str(text)


def bold(t):   return _c("1", t)
def green(t):  return _c("32", t)
def red(t):    return _c("31", t)
def yellow(t): return _c("33", t)
def cyan(t):   return _c("36", t)
def dim(t):    return _c("2", t)


def _visible_len(s):
    """Length of string excluding ANSI escape codes."""
    return len(_ANSI_RE.sub("", str(s)))


def _ljust(s, width):
    """Left-justify string accounting for ANSI escape codes."""
    return str(s) + " " * (width - _visible_len(str(s)))


def print_table(headers, rows):
    """Print a simple aligned table with colored headers."""
    if not rows:
        print(f"  {dim('(no results)')}")
        return

    col_widths = [_visible_len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], _visible_len(str(cell)))

    header_line = "  ".join(_ljust(bold(h), col_widths[i]) for i, h in enumerate(headers))
    separator = dim("  ".join("─" * col_widths[i] for i in range(len(headers))))
    print(f"  {header_line}")
    print(f"  {separator}")

    for row in rows:
        line = "  ".join(_ljust(re.sub(r"[\x00-\x1f\x7f]", lambda m: f"\\x{ord(m.group()):02x}", str(cell)), col_widths[i]) for i, cell in enumerate(row))
        print(f"  {line}")


def output_json(data):
    """Print data as formatted JSON and exit."""
    print(json.dumps(data, indent=2, ensure_ascii=False))
    sys.exit(0)
