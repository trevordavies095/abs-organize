"""Console entry point for abs-organize.

Exit codes:
  0 — success
  1 — user or metadata error
  2 — I/O error
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from abs_organize.config import (
    ENV_LIBRARY,
    ConfigError,
    load_config,
    resolve_library_path,
)
from abs_organize.metadata import MetadataError, MetadataOverrides, ValidationError
from abs_organize.organize import OrganizeIOError, OrganizeResult, organize


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="abs-organize",
        description=(
            "Copy a tagged audiobook file or track folder into an Audiobookshelf "
            "library layout ({library}/{Author}/[{Series}/]{TitleFolder}/)."
        ),
    )
    parser.add_argument(
        "input",
        metavar="INPUT",
        type=Path,
        help="path to an audio file or directory of tracks (.mp3, .m4b, .m4a, .flac, .ogg)",
    )
    parser.add_argument(
        "--library",
        type=Path,
        metavar="PATH",
        default=None,
        help=(
            f"library root directory for this run (overrides config and {ENV_LIBRARY})"
        ),
    )
    parser.add_argument(
        "--profile",
        metavar="NAME",
        default=None,
        help="named library profile from config (default profile when omitted)",
    )
    parser.add_argument("--author", metavar="TEXT", default=None, help="override author")
    parser.add_argument("--title", metavar="TEXT", default=None, help="override title")
    parser.add_argument("--year", metavar="INT", type=int, default=None, help="override year")
    parser.add_argument("--series", metavar="TEXT", default=None, help="override series")
    parser.add_argument(
        "--sequence",
        metavar="FLOAT",
        type=float,
        default=None,
        help="override series sequence / volume number",
    )
    parser.add_argument(
        "--narrator",
        metavar="TEXT",
        default=None,
        help="override narrator",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="log path segment sanitization details to stderr",
    )
    return parser


def _load_include_subtitle_in_folder() -> bool:
    try:
        return load_config().include_subtitle_in_folder
    except ConfigError:
        return False


def _metadata_overrides_from_args(args: argparse.Namespace) -> MetadataOverrides | None:
    overrides = MetadataOverrides(
        author=args.author,
        title=args.title,
        year=args.year,
        series=args.series,
        sequence=args.sequence,
        narrator=args.narrator,
    )
    if any(
        getattr(overrides, field) is not None
        for field in ("author", "title", "year", "series", "sequence", "narrator")
    ):
        return overrides
    return None


def _print_result(result: OrganizeResult) -> None:
    print(f"Source: {result.source}")
    print(f"Destination: {result.dest_dir}/")
    print("Copied:")
    for name in result.copied_files:
        print(f"  {name}")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    on_log: Callable[[str], None] | None = None
    if args.verbose:
        on_log = lambda message: print(message, file=sys.stderr)

    try:
        library = resolve_library_path(
            library_flag=args.library,
            profile=args.profile,
        )
        result, warnings = organize(
            args.input,
            library,
            overrides=_metadata_overrides_from_args(args),
            include_subtitle_in_folder=_load_include_subtitle_in_folder(),
            on_log=on_log,
        )
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    except MetadataError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    except OrganizeIOError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(2) from exc

    for warning in warnings:
        print(warning, file=sys.stderr)

    _print_result(result)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
