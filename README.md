# manjaro-fetch

A download manager for Manjaro images: official, community, and custom respins.

## Features

- **Multi-source**: GitHub Releases (`manjaro/release-review`, `manjaro/community-editions`), SourceForge (latest + RSS for all), Internet Archive (metadata API), Sway HTML index, and the legacy `file-info.json` (kept for when `gitlab.manjaro.org` returns).
- **Latest by default, all versions optional**: `list` shows only the latest per source; `--all` shows everything.
- **Extras hidden by default**: custom respins live in the `extras` category and only appear with `--extras` (CLI) or the "Show extras" checkbox (GUI).
- **Persistent download tracking**: SQLite records what you downloaded, even after you delete the file. `status` flags recorded entries whose file is missing.
- **Verification**: SHA1/SHA256/SHA512 sidecars plus optional GPG, on by default.
- **GUI follows your theme**: PySide6 with `colorScheme()` detection; no separate theme config.
- **Portable silent installer**: user-level, `-i`/`i` to install, `-r`/`r` to remove.

## Requirements

- Python ≥ 3.11
- PySide6 (`python-pyside6` in the Manjaro `extra` repo)

No other runtime dependencies. Optional: `gnupg` for signature verification.

## Install

```bash
./install.sh -i
```

Silent on success. Installs to `~/.local/bin`, `~/.local/share/applications`, `~/.local/share/icons/hicolor/`, and `pip install --user`s the package. Remove with:

```bash
./install.sh -r
```

## Usage

```bash
manjaro-fetch                                  # launch the GUI
manjaro-fetch list                             # latest official + community
manjaro-fetch list --all                       # every version
manjaro-fetch list --extras                    # include custom respins
manjaro-fetch list --json                      # machine readable
manjaro-fetch download <release-key>           # download a specific release
manjaro-fetch status                           # see what you have downloaded
manjaro-fetch sources                          # list configured sources
manjaro-fetch config                           # show paths and user config location
```

Release keys look like `release-review:manjaro-xfce-26.1.3-261108-linux618.iso`; copy them from `list` output.

## Adding your project

`manjaro-fetch` reads source definitions from TOML. To add a project you do **not** need to modify Python code:

1. Create `~/.config/manjaro-fetch/sources.toml` (or copy the bundled `manjaro_fetch/default_sources.toml`).
2. Add a `[[source]]` block. Entries with the same `name` replace the bundled one.

Example — a GitHub-hosted respin:

```toml
[[source]]
name = "my-respin"
type = "github"
category = "extras"
repo = "yourname/my-respin"
enabled = true
```

Example — an Internet Archive item:

```toml
[[source]]
name = "my-respin-ia"
type = "archive_org"
category = "extras"
identifier = "my-respin-2026"
enabled = true
```

Supported `type` values:

| type | required options | optional |
|---|---|---|
| `github` | `repo` | — |
| `sourceforge` | `project` | — |
| `archive_org` | `identifier` | — |
| `sway_html` | — | `url` |
| `gitlab` | `url` | — |

Categories: `official`, `community`, `extras`. Only `extras` is hidden by default.

### Submitting a project to the bundled sources

If you maintain a Manjaro-based project and want it listed out of the box, open an issue with:

- project name and one-line description,
- source type and required options (see table above),
- expected file layout (single ISO, folder-per-build, etc.).

## Status of upstream sources

- **`gitlab.manjaro.org/webpage/iso-info/.../file-info.json`** — returns HTTP 502 at the time of writing. Kept in `default_sources.toml` with a `NOTE` comment; will be replaced once Manjaro publishes a stable endpoint on `code.manjaro.org` (Forgejo).
- **GitHub Releases** (`manjaro/release-review`, `manjaro/community-editions`) — active.
- **Sway** (`sway.manjaro.download/iso/`) — active.
- **SourceForge** — only the two most recent builds are retained upstream; `--all` reflects that.
- **Internet Archive** — full file list via the metadata API.

## License

GPL-2.0-only.
