"""Console entry point for abs-organize.

Exit codes:
  0 — success
  1 — user or metadata error
  2 — I/O error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from abs_organize.metadata import MetadataError, ValidationError
from abs_organize.organize import OrganizeIOError, OrganizeResult, organize_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="abs-organize",
        description=(
            "Copy a tagged audiobook file into an Audiobookshelf library layout "
            "({library}/{Author}/{Title}/)."
        ),
    )
    parser.add_argument(
        "input",
        metavar="INPUT",
        type=Path,
        help="path to a single audio file (.mp3, .m4b, .m4a)",
    )
    parser.add_argument(
        "--library",
        required=True,
        type=Path,
        metavar="PATH",
        help="library root directory for this run",
    )
    return parser


def _print_result(result: OrganizeResult) -> None:
    print(f"Source: {result.source}")
    print(f"Destination: {result.dest_dir}/")
    print("Copied:")
    for name in result.copied_files:
        print(f"  {name}")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        result = organize_file(args.input, args.library)
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    except MetadataError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    except OrganizeIOError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc

    _print_result(result)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
