# abs-organize

CLI to place downloaded audiobooks into an [Audiobookshelf](https://www.audiobookshelf.org/) library layout from embedded tags (and optional folder-name guesses). **Copy** is the default; use **`--move`** to clear the inbox after a successful run.

**Layout:** `{library}/{Author}/[{Series}/]{TitleFolder}/`

**Requirements:** Python 3.11+

## Quick start

```bash
pip install abs-organize

# One-off (no config file)
abs-organize ~/Downloads/book.m4b --library ~/Audiobooks --dry-run
abs-organize ~/Downloads/book.m4b --library ~/Audiobooks

# With config (see Configuration)
abs-organize ~/Downloads/inbox/MyBook.m4b
```

## Install

From PyPI (recommended):

```bash
pip install abs-organize
```

From a clone:

```bash
pip install -e .
```

For development and tests, see [Development](#development).

## Usage

```text
abs-organize INPUT [options]
```

**INPUT** — one audio file (`.mp3`, `.m4b`, `.m4a`, `.flac`, `.ogg`) or a folder of tracks.

| Option | Purpose |
|--------|---------|
| `--library PATH` | Library root for this run (overrides config and env) |
| `--profile NAME` | Named `[libraries.*]` profile (default profile when omitted) |
| `--dry-run` | Show library, destination, and planned ops; no writes |
| `--move` | Move into the library instead of copy (rename on same FS) |
| `--replace` | Delete existing destination title folder, then organize |
| `--allow-guess` | Guess author/title from folder or file name when tags are missing |
| `--batch` | Organize every detected book under INPUT (multi-book inbox) |
| `--continue-on-error` | With `--batch`, keep going after a failure (apply runs only) |
| `--json` | Success payload on stdout (scripting) |
| `-v`, `--verbose` | Path sanitization details on stderr |

**Metadata overrides** (single-book runs): `--author`, `--title`, `--year`, `--series`, `--sequence`, `--narrator`. With **`--batch`**, `--series`, `--narrator`, and `--year` may gap-fill empty fields per book; `--author`, `--title`, and `--sequence` are rejected.

### Preview, copy, and move

```bash
abs-organize ~/Downloads/inbox/SomeBook --dry-run --library ~/Audiobooks
abs-organize ~/Downloads/inbox/SomeBook --library ~/Audiobooks
abs-organize ~/Downloads/inbox/SomeBook --library ~/Audiobooks --move
```

`--dry-run` uses the same validation as a real run and prints warnings to stderr, but does not create library paths or transfer files.

### Batch inbox

If INPUT contains multiple book roots (e.g. several `.m4b` siblings), a plain run fails with a candidate list. Use **`--batch`** to organize all detected books:

```bash
abs-organize ~/Downloads/inbox --batch --library ~/Audiobooks --dry-run
abs-organize ~/Downloads/inbox --batch --library ~/Audiobooks --move
```

Dry-run always reports every book. On apply, batch stops at the first failure unless **`--continue-on-error`** is set.

**Discovery (summary):** each `.m4b`/`.m4a` sibling is its own book; `.mp3`/`.flac`/`.ogg` siblings in one folder are one book; `Disc`/`CD`/`Disk` subfolders roll up to one book at the parent.

### Metadata and guessing

Tags are read with [Mutagen](https://mutagen.readthedocs.io/):

| Folder segment | Tags |
|----------------|------|
| Author | `albumartist` or `artist` |
| Title folder | `album` or `title` (+ optional `subtitle` via config) |
| Series | `grouping`; sequence/year/narrator from tags, movement atoms (`.m4b`/`.m4a`), or OPF when present |

When **`album`** or **`title`** ends with a trailing narrator clause — ` (read by …)`, ` (narrated by …)`, or ` (performed by …)` (or the same phrases in square brackets) — that clause is removed from the title folder name. The extracted name becomes **narrator** only if the `composer` tag is empty; if `composer` is set, it wins for the `{Narrator}` segment and the suffix is still stripped from the title.

Missing **author** or **title** tags exit with an error unless **`--allow-guess`** is set. Guesses use patterns such as `Author - Title` or `Author - Title (YYYY)` on the book folder or file stem; stderr marks them `(confidence: low)`. CLI overrides always win.

**Example (series layout):**

```text
{library}/Terry Goodkind/Sword of Truth/Vol 1 - 1994 - Wizards First Rule {Sam Tsoutsouvas}/book.m4b
```

Sidecars (`desc.txt`, `reader.txt`, cover images) are copied when present.

## Configuration

File: `~/.config/abs-organize/config.toml`

```toml
include_subtitle_in_folder = false

[libraries.default]
path = "/Users/you/Audiobooks"

[libraries.fiction]
path = "/Users/you/Audiobooks/Fiction"
```

- **`[libraries.default]`** is required when you omit `--library`.
- `include_subtitle_in_folder` — append ` - {subtitle}` to the title folder name.

**Library path precedence**

| Priority | Source |
|----------|--------|
| 1 | `--library PATH` |
| 2 | `ABS_ORGANIZE_LIBRARY` (only when `--profile` is omitted) |
| 3 | `[libraries.{profile}].path` when `--profile NAME` is set |
| 4 | `[libraries.default].path` |

## Scripting (`--json`)

On success, stdout is JSON; errors stay on stderr (plain text). Warnings are in the JSON payload, not duplicated on stderr.

**Single book:**

```json
{
  "destination": "/Users/you/Audiobooks/Jane Author/Book Title/",
  "files": ["book.mp3"],
  "warnings": []
}
```

**Batch:**

```json
{
  "books": [
    {
      "source": "/inbox/Book A/",
      "ok": true,
      "destination": "/Audiobooks/Author/Title/",
      "files": ["book.m4b"],
      "warnings": []
    }
  ],
  "summary": { "ok": 1, "failed": 0 }
}
```

Unknown top-level keys may be added later; ignore fields you do not need.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User or metadata error (missing tags, invalid paths, config/profile errors) |
| 2 | I/O error (copy, move, or filesystem failure) |

Batch: `0` only if every book succeeded; partial failure uses `1` or `2` if any book hit I/O errors.

## Development

Release policy: see [`docs/RELEASE.md`](docs/RELEASE.md).

**CI:** GitHub Actions runs `pytest` on every push and pull request (`.github/workflows/ci.yml`). Require the **CI** status check to pass before merging to `main` (**Settings → Branches → Branch protection rules**).

| Path | Role |
|------|------|
| `src/abs_organize/cli.py` | Argument parsing and entry point |
| `src/abs_organize/organize.py` | Single-book copy/move pipeline |
| `src/abs_organize/batch.py` | Multi-book inbox orchestration |
| `src/abs_organize/discovery.py` | Book-root detection |
| `src/abs_organize/metadata.py` | Tag read, validation, overrides |
| `src/abs_organize/naming.py` | ABS-style path segments |
| `tests/` | Pytest suite (`test_data/` for fixtures) |

```bash
pip install -e ".[dev]"
pytest
abs-organize --help
```
