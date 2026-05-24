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
abs-organize INPUT [--profile NAME] [--library PATH]
```

- **INPUT** — path to a single `.mp3`, `.m4b`, or `.m4a` file
- **--profile** — named library profile from config (uses `default` when omitted)
- **--library** — library root for this run only (overrides config and env)

When `[libraries.default]` is configured, you can omit `--library`:

```bash
abs-organize ~/Downloads/book.m4b
```

Example with an explicit library path (no config required):

```bash
abs-organize ~/Downloads/book.m4b --library ~/Audiobooks
```

Metadata is read from embedded tags (Mutagen). Author comes from `albumartist` or `artist`; title from `album` or `title`. The file is **copied** (not moved), keeping its original basename.

## Configuration

Config file: `~/.config/abs-organize/config.toml`

```toml
include_subtitle_in_folder = false

[libraries.default]
path = "/Users/you/Audiobooks"

[libraries.fiction]
path = "/Users/you/Audiobooks/Fiction"
```

- **`[libraries.default]`** is required.
- Additional profiles (e.g. `[libraries.fiction]`) are optional.
- `include_subtitle_in_folder` is parsed for future naming behavior; it has no effect yet.

### Library path precedence

| Priority | Source |
|----------|--------|
| 1 | `--library PATH` |
| 2 | `ABS_ORGANIZE_LIBRARY` (only when `--profile` is omitted) |
| 3 | `[libraries.{profile}].path` when `--profile NAME` is set |
| 4 | `[libraries.default].path` |

Set `ABS_ORGANIZE_LIBRARY` to override the default profile path without editing config.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User or metadata error (missing tags, invalid paths, config/profile errors) |
| 2 | I/O error (copy or filesystem failure) |

## Tests

```bash
pytest
```

## Roadmap

Dry-run, multi-file folders, series folders, covers, and move/replace options are planned in later issues.
