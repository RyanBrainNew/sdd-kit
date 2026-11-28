"""Deprecated compatibility shim for ``python bootstrap.py``.

All initialization logic lives in ``sdd/bootstrap.py`` and is shared with
``sdd init``. This file only parses the historical entry point, prints a
deprecation notice, and delegates.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sdd.bootstrap import build_parser, init_repository, render_payload


KIT_ROOT = Path(__file__).resolve().parent


def bootstrap(args: argparse.Namespace) -> int:
    print(
        "[sdd] bootstrap.py is deprecated; use "
        "`python -m sdd init` instead",
        file=sys.stderr,
    )
    payload = init_repository(args)
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        render_payload(payload)
    if payload.get("ok"):
        return 0
    errors = payload.get("errors") or ["initialization failed"]
    raise SystemExit(errors[0])


def main(argv: list[str] | None = None) -> int:
    return bootstrap(build_parser(prog="bootstrap.py").parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
