import argparse
import json
import shutil
from pathlib import Path

from dl_vsix.dl import Extension, download_extensions


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


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser(
        "dl_vsix", description="Download VSIX bundles for offline extension installation."
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("extension", nargs="?", type=str, help="Single extension by ID")
    source_group.add_argument(
        "-s", "--spec_file", type=Path, help="JSON-specified collection of extensions"
    )
    parser.add_argument(
        "-o",
        "--out_dir",
        type=Path,
        default=Path("./vsix"),
        help="Download directory (default: ./vsix)",
    )
    parser.add_argument(
        "-f", "--follow_deps", action="store_false", help="Trace extension's dependencies."
    )
    parser.add_argument("-z", "--zip", action="store_true", help="Zip the download extension(s)")
    args = parser.parse_args()

    # Since we have a mutually exclusive group, only one of these can be specified
    if args.extension is not None:
        extensions = [Extension.from_id(args.extension)]
    else:
        extensions = _parse_extensions(args.spec_file)

    download_extensions(extensions, out_dir=args.out_dir, follow_dependencies=args.follow_deps)
    if args.zip:
        zip_filepath = args.out_dir.parent / "zipped_extensions"
        shutil.make_archive(base_name=zip_filepath, format="zip", root_dir=args.out_dir)


if __name__ == "__main__":
    main()
