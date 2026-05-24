# Release policy

Human decisions and publishing setup for `abs-organize` on PyPI. Application packaging and workflows are tracked in GitHub issues #21–#24.

## License

**MIT** (SPDX identifier: `MIT`).

The `LICENSE` file (MIT) and `pyproject.toml` `license` / `license-files` metadata declare this choice for PyPI.

## Versioning

- **`pyproject.toml` `version`** is the source of truth for releases.
- **Git tags** use the form `v{version}` (e.g. tag `v0.1.0` matches version `0.1.0`).
- Bump the version only on the commit that will be tagged for release.
- Keep `src/abs_organize/__init__.py` `__version__` in sync when present.

### 0.x SemVer policy

During `0.x`, follow [SemVer 2.0](https://semver.org/) pre-1.0 rules: **minor releases may include breaking CLI changes**. Treat `1.0.0` as the point where CLI behavior is expected to remain backward compatible across minor releases.

## First published version

**`0.1.0`** — matches the current codebase (batch inbox, JSON output, config profiles, move/replace, etc.). No version bump before the first PyPI upload.

Production PyPI release follows a successful TestPyPI publish (issues #23 → #24).

## Trusted publishing

Publishing uses [PyPI trusted publishers](https://docs.pypi.org/trusted-publishers/) (OIDC from GitHub Actions). No long-lived PyPI API tokens are stored in this repository.

Workflows in #23/#24 **must** match these settings exactly:

| Field | Production PyPI | TestPyPI |
|-------|-----------------|----------|
| Project name | `abs-organize` | `abs-organize` |
| GitHub owner | `trevordavies095` | `trevordavies095` |
| Repository | `abs-organize` | `abs-organize` |
| Workflow filename | `release.yml` | `release.yml` |
| GitHub environment | `pypi` | `testpypi` |

### Setup references

- [Adding a trusted publisher to an existing project](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [Creating a project with a pending trusted publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) (first upload creates the PyPI project)

### GitHub environments

Repository **Settings → Environments** on [`trevordavies095/abs-organize`](https://github.com/trevordavies095/abs-organize):

- **`testpypi`** — TestPyPI uploads (#23)
- **`pypi`** — production PyPI uploads (#24); consider required reviewers before production publish

Both environments are configured on the repository.

### Account setup checklist

Complete once while logged into [pypi.org](https://pypi.org) and [test.pypi.org](https://test.pypi.org) (separate accounts). Use **Account → Publishing → Add pending publisher** on each site:

| Field | Production PyPI | TestPyPI |
|-------|-----------------|----------|
| PyPI project name | `abs-organize` | `abs-organize` |
| Owner | `trevordavies095` | `trevordavies095` |
| Repository name | `abs-organize` | `abs-organize` |
| Workflow name | `release.yml` | `release.yml` |
| Environment name | `pypi` | `testpypi` |

After saving, confirm each account lists the pending publisher. The project is created on first successful upload from the release workflow (#23/#24).

## Local verification (before first publish)

Run from the repository root after packaging metadata changes:

```bash
pip install build twine
python -m build
twine check dist/*
```

Expect `python -m build` to produce `dist/abs-organize-0.1.0.tar.gz` and `dist/abs_organize-0.1.0-py3-none-any.whl`. `twine check` should report both artifacts as valid with no errors.
