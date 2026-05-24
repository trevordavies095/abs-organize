# abs-organize

A Python CLI that copies a tagged audiobook file into an [Audiobookshelf](https://www.audiobookshelf.org/) library layout (`{library}/{Author}/[{Series}/]{TitleFolder}/`).

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
abs-organize INPUT [--profile NAME] [--library PATH] [--dry-run] [--replace] [-v|--verbose]
```

- **INPUT** — path to a single audio file or a directory of tracks (`.mp3`, `.m4b`, `.m4a`, `.flac`, `.ogg`)
- **--profile** — named library profile from config (uses `default` when omitted)
- **--library** — library root for this run only (overrides config and env)
- **--dry-run** — print library root, destination, and planned copies; make no changes
- **--replace** — delete the entire existing destination title folder, then copy (destructive; use when re-organizing)
- **-v / --verbose** — log path segment sanitization details to stderr

When `[libraries.default]` is configured, you can omit `--library`:

```bash
abs-organize ~/Downloads/book.m4b
```

Example with an explicit library path (no config required):

```bash
abs-organize ~/Downloads/book.m4b --library ~/Audiobooks
```

### Preview first

Use `--dry-run` to verify naming before writing. It runs the same metadata validation as a real organize and prints warnings to stderr, but does not create directories or copy files under the library. Omit the flag to apply (copy) into the library.

```bash
abs-organize ~/Downloads/inbox/SomeBook --dry-run --library ~/Audiobooks
abs-organize ~/Downloads/inbox/SomeBook --library ~/Audiobooks
```

Metadata is read from embedded tags (Mutagen). Author comes from `albumartist` or `artist`; title from `album` or `title`. Optional tags drive ABS-style folders: `grouping` (series), `date` (year), `composer` (narrator), and on `.m4b`/`.m4a` iTunes movement atoms when present.

**Example layout (series):**

```text
{library}/Terry Goodkind/Sword of Truth/Vol 1 - 1994 - Wizards First Rule {Sam Tsoutsouvas}/book.m4b
```

The file is **copied** (not moved), keeping its original basename.

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
- `include_subtitle_in_folder` — when `true`, appends ` - {subtitle}` to the title folder name (from the `subtitle` tag).

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

Covers and move are planned in later issues.
