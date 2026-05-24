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
abs-organize INPUT [--profile NAME] [--library PATH] [--dry-run] [--replace] [--allow-guess] [--json] [-v|--verbose]
```

- **INPUT** — path to a single audio file or a directory of tracks (`.mp3`, `.m4b`, `.m4a`, `.flac`, `.ogg`)
- **--profile** — named library profile from config (uses `default` when omitted)
- **--library** — library root for this run only (overrides config and env)
- **--dry-run** — print library root, destination, and planned copies; make no changes
- **--replace** — delete the entire existing destination title folder, then copy (destructive; use when re-organizing)
- **--allow-guess** — when author/title tags are missing, guess them from the book folder or file name (low confidence; see below)
- **--json** — on success, print minimal JSON to stdout (for scripting); errors stay on stderr as plain text
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

By default, missing author or title tags cause the command to exit with an error and make no library changes. Use **`--allow-guess`** to opt in to folder-name heuristics when tags are too sparse.

### Folder-name guessing (`--allow-guess`)

When tags do not provide author and title, `--allow-guess` parses the book folder name (or the file stem for a single-file input). Guesses are marked on stderr with `(confidence: low)`. CLI overrides (`--author`, `--title`, etc.) always win over guesses.

Supported patterns (first separator wins for titles that contain hyphens):

- `Author - Title`
- `Author – Title` / `Author — Title` (en dash or em dash)
- `Author - Title (YYYY)` — optional trailing year in parentheses

Example:

```bash
abs-organize ~/Downloads/inbox/"Jane Author - Great Book" --library ~/Audiobooks --allow-guess
```

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

## JSON output

With `--json`, a successful run prints a single JSON object to stdout (human-readable lines are omitted). Warnings are included in the payload, not duplicated on stderr. Failed runs print an error message on stderr and exit `1` or `2` without success JSON.

```json
{
  "destination": "/Users/you/Audiobooks/Jane Author/Book Title/",
  "files": ["book.mp3"],
  "warnings": ["album tag conflict: ..."]
}
```

- **destination** — absolute path to the title folder, with a trailing `/`
- **files** — paths relative to the title folder (audio, sidecars, cover when present)
- **warnings** — non-fatal notices (tag conflicts, collision hints on dry-run, etc.)

Additional top-level keys may be added in later versions (`profile`, `dry_run`, …) without breaking consumers that ignore unknown fields.

## Tests

```bash
pytest
```

## Roadmap

Covers and move are planned in later issues.
