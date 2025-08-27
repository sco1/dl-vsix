from __future__ import annotations

import json
import tempfile
import typing as t
import zipfile
from pathlib import Path

import httpx

from dl_vsix.extension_query import query_latest_version


class Extension(t.NamedTuple):  # noqa: D101
    publisher: str
    extension: str

    def __str__(self) -> str:
        return self.pID

    @property
    def pID(self) -> str:
        """Build the full extension ID, as `'<publisher>.<package>'`."""
        return f"{self.publisher}.{self.extension}"

    @classmethod
    def from_id(cls, extension_id: str) -> Extension:
        """
        Build an `Extension` instance from the provided extension ID.

        Extension IDs are assumed to be of the format `<publisher>.<package>`, e.g.
        `ms-python.python`.
        """
        publisher, extension = extension_id.split(".")
        return cls(publisher=publisher, extension=extension)

    def vsix_query(self, version: str = "latest") -> str:
        """Build query URL for the extension's latest VSIX package."""
        api_base = f"https://{self.publisher}.gallery.vsassets.io/_apis/public/gallery"
        publisher_comp = f"publisher/{self.publisher}"
        extension_comp = f"extension/{self.extension}"
        suffix = f"{version}/assetbyname/Microsoft.VisualStudio.Services.VSIXPackage"

        return f"{api_base}/{publisher_comp}/{extension_comp}/{suffix}"


def extract_dependencies(vsix_zip: Path, target: str = "extension/package.json") -> set[Extension]:
    """
    Check the provided VSIX for any additional dependencies.

    Each VSIX package should have an `extension/package.json` detailing extension information; if an
    extension has additional dependencies, they should be declared in an `"extensionDependencies"`
    field as a list of extension ID strings.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = ""
        with zipfile.ZipFile(vsix_zip, "r") as zp:
            if target in zp.namelist():
                spec_path = zp.extract(target, tmpdir)

        if not spec_path:
            return set()

        with open(spec_path, "r") as f:
            extension_spec = json.load(f)

        dependencies = extension_spec.get("extensionDependencies", [])
        return {Extension.from_id(s) for s in dependencies}


def download_extensions(
    extensions: list[Extension],
    out_dir: Path,
    follow_dependencies: bool = True,
) -> None:
    """
    Download VSIX packages for the specified extension(s) from the VS marketplace Gallery API.

    If `follow_dependencies` is `True`, the extension's metadata will be checked to see if it
    depends on any additional packages, which will be added to the queue if they haven't yet been
    downloaded.
    """
    # TODO: Incorporate package cache
    if not out_dir.exists():
        raise ValueError(f"Specified output directory does not exist: '{out_dir}'")

    # Track extensions already downloaded so we don't duplicate; mainly helpful when tracking
    # dependencies
    seen_extensions = set()
    with httpx.Client() as client:
        while extensions:
            ext = extensions.pop()

            latest_ver = query_latest_version(str(ext))
            out_filepath = out_dir / f"{ext}_{latest_ver}.vsix"

            with client.stream("GET", ext.vsix_query(version=latest_ver)) as r:
                if r.status_code == httpx.codes.OK:
                    with out_filepath.open("wb") as f:
                        for chunk in r.iter_bytes():
                            f.write(chunk)

                    seen_extensions.add(ext)
                    print(f"Successfully downloaded extension '{ext}', version: {latest_ver}")

                else:
                    print(f"Could not download extension '{ext}': {r.status_code}")
                    continue

            if follow_dependencies:
                dependencies = extract_dependencies(out_filepath)
                print(f"Found {len(dependencies)} additional dependencies")

                not_seen = dependencies - seen_extensions
                extensions.extend(not_seen)
