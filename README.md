# abs-organize

A Python CLI that copies a tagged audiobook file into an [Audiobookshelf](https://www.audiobookshelf.org/) library layout (`{library}/{Author}/{Title}/`).

## Install

```bash
pip install -e .
```

For development and tests:

```bash
pip install -e ".[dev]"
```

## Usage

```bash
abs-organize INPUT --library PATH
```

- **INPUT** — path to a single `.mp3`, `.m4b`, or `.m4a` file
- **--library** — library root directory (author/title folders are created under it)

Example:

```bash
abs-organize ~/Downloads/book.m4b --library ~/Audiobooks
```

Metadata is read from embedded tags (Mutagen). Author comes from `albumartist` or `artist`; title from `album` or `title`. The file is **copied** (not moved), keeping its original basename.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User or metadata error (missing tags, invalid paths, unsupported file) |
| 2 | I/O error (copy or filesystem failure) |

## Tests

```bash
pytest
```

## Roadmap

Config profiles, dry-run, multi-file folders, series folders, covers, and move/replace options are planned in later issues.
