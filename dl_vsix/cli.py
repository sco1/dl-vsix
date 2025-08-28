import json
import os
import shutil
from pathlib import Path

import typer

from dl_vsix.dl import Extension, download_extensions
from dl_vsix.extension_cache import DEFAULT_CACHE_MAXSIZE_MB, ExtensionCache

# Initialize package cache in the global scope so we have access to a single instance for the CLI
_cache_path_env = os.getenv("DL_VSIX_CACHE_DIR")
_cache_path_override: Path | None
if _cache_path_env is not None:
    _cache_path_override = Path(_cache_path_env)
else:
    _cache_path_override = None

_cache_maxsize_env = os.getenv("DL_VSIX_CACHE_DIR")
if _cache_maxsize_env is not None:
    _cache_maxsize_override = int(_cache_maxsize_env)
else:
    _cache_maxsize_override = DEFAULT_CACHE_MAXSIZE_MB

PACKAGE_CACHE = ExtensionCache(
    path_override=_cache_path_override, cache_maxsize_mb=_cache_maxsize_override
)


def _parse_extensions(spec_json: Path) -> list[Extension]:
    """
    Parse a list of extensions from the provided JSON file.

    Extension IDs are assumed to be provided by an `"extensions"` field as a list of strings, e.g.:

    ```
    {
        "extensions": [
            "ms-python.python",
            "ms-python.vscode-pylance"
        ]
    }
    ```
    """
    if not spec_json.exists():
        raise ValueError(f"Source JSON does not exist: '{spec_json}'")

    with spec_json.open("r") as f:
        spec = json.load(f)

    return [Extension.from_id(s) for s in spec.get("extensions", [])]


dl_vsix_cli = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Download VSIX bundles for offline extension installation.",
)


@dl_vsix_cli.command(no_args_is_help=True)
def download(
    extension_id: str = typer.Argument("", help="Single extension by ID"),
    spec_file: Path = typer.Option(
        None, "-s", "--spec_file", help="JSON-specified collection of extensions", dir_okay=False
    ),
    out_dir: Path = typer.Option(
        Path("./vsix"), "--out_dir", "-o", help="Download directory", file_okay=False
    ),
    follow_deps: bool = typer.Option(
        False, "--follow_deps", "-f", help="Trace extension's dependencies"
    ),
    zip_result: bool = typer.Option(False, "--zip", "-z", help="Zip the download extension(s)"),
) -> None:
    """
    Download VSIX extension packages.

    NOTE: `extension_id` and `spec_file` are mutually exclusive.
    """
    if (not extension_id) and (spec_file is None):
        raise ValueError("Either extension_id or spec_file must be specified.")

    if extension_id and spec_file:
        raise ValueError("Cannot specify both an extension_id and spec file.")

    if extension_id is not None:
        extensions = [Extension.from_id(extension_id)]
    else:
        extensions = _parse_extensions(spec_file)

    download_extensions(
        extensions, out_dir=out_dir, package_cache=PACKAGE_CACHE, follow_dependencies=follow_deps
    )
    if zip_result:
        zip_filepath = out_dir.parent / "zipped_extensions"
        shutil.make_archive(base_name=str(zip_filepath), format="zip", root_dir=out_dir)


cache_sub = typer.Typer(
    name="cache", no_args_is_help=True, add_completion=False, help="Package cache utilities"
)
dl_vsix_cli.add_typer(cache_sub)


@cache_sub.command("info")
def cache_info() -> None:
    """Show cache information."""
    PACKAGE_CACHE.info()


@cache_sub.command("list")
def cache_list() -> None:
    """List cache contents."""
    PACKAGE_CACHE.list()


@cache_sub.command("remove")
def cache_remove(extensions: list[str]) -> None:
    """Remove extension(s) from cache."""
    for e in extensions:
        PACKAGE_CACHE.remove(Extension.from_id(e))


@cache_sub.command("purge")
def cache_purge() -> None:
    """Clear package cache."""
    PACKAGE_CACHE.purge()


if __name__ == "__main__":
    dl_vsix_cli()
