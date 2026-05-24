# Install Guide

`cls-cli` can be run from source. Package-manager commands become available after publishing the package to PyPI or an internal package index.

## Requirements

- Python compatible with the version declared in `pyproject.toml`.
- `uv` for local development and source execution.
- Tencent Cloud credentials provided through environment variables.

## Run from source

```bash
git clone <repository-url> cls-cli
cd cls-cli
uv sync
uv run cls --help
```

Verify credentials:

```bash
export TENCENTCLOUD_SECRET_ID='<set-locally>'
export TENCENTCLOUD_SECRET_KEY='<set-locally>'
uv run cls logset list --region ap-guangzhou
```

## Install after package publication

After the package is published to PyPI or an internal package index, use one of these methods.

### pipx

```bash
pipx install cls-cli
cls --help
```

Upgrade:

```bash
pipx upgrade cls-cli
```

Uninstall:

```bash
pipx uninstall cls-cli
```

### uv tool

```bash
uv tool install cls-cli
cls --help
```

Upgrade by reinstalling the desired version from the configured index.

### pip

```bash
python -m pip install cls-cli
cls --help
```

For isolated command-line use, prefer `pipx` or `uv tool` over installing into a shared Python environment.

## Development install

```bash
cd cls-cli
uv sync
uv run pytest -q
uv run ruff check src tests examples/simple_webhook_receiver.py
uv run mypy src/cls_cli --show-error-codes
```

## Build package locally

```bash
uv build
```

Expected outputs:

```text
dist/cls_cli-<version>.tar.gz
dist/cls_cli-<version>-py3-none-any.whl
```

`dist/` is ignored by Git.

## Configuration directory

Default profile configuration lives at:

```text
~/.cls-cli/config.toml
```

Override with:

```bash
export CLS_CLI_CONFIG_DIR=/path/to/config-dir
```

Profiles store environment variable names and default region, not raw credentials.

## Versioning and release note

Before publishing a new package version:

- update `pyproject.toml` version;
- ensure the Git tag matches the version;
- run the full test/lint/type/build verification;
- never reuse an already-published PyPI version.
