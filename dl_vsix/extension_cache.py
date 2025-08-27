from __future__ import annotations

import datetime as dt
import shutil
import typing as t
from pathlib import Path

import platformdirs

from dl_vsix import APPNAME, dl


def bytes2megabytes(n_bytes: int) -> float:  # noqa: D103
    return n_bytes / (1 << 20)


class CachedExtension(t.NamedTuple):  # noqa: D101
    extension: dl.Extension
    version: str
    created_at: dt.datetime
    cache_path: Path
    byte_size: int

    def __str__(self) -> str:
        mb_size = bytes2megabytes(self.byte_size)
        return f"{self.extension}_{self.version} ({mb_size:.2f} MB)"

    @classmethod
    def from_vsix_path(cls, vsix_filepath: Path) -> CachedExtension:
        """
        Build a `CachedExtension` instance from the provided VSIX filepath.

        NOTE: It is assumed that the provided filepath is already located in the cache directory.
        """
        if not vsix_filepath.exists():
            raise ValueError(f"File does not exist: '{vsix_filepath}'")

        if vsix_filepath.suffix.lower() != ".vsix":
            raise ValueError(f"`{vsix_filepath.name}` does not appear to be a VSIX package.")

        extension_id, version = vsix_filepath.stem.split("_")
        stats = vsix_filepath.stat()

        return cls(
            extension=dl.Extension.from_id(extension_id),
            version=version,
            created_at=dt.datetime.fromtimestamp(stats.st_mtime),
            cache_path=vsix_filepath,
            byte_size=stats.st_size,
        )


class ExtensionCache:
    """VSIX extension cache manager."""

    _package_cache: set[CachedExtension]

    def __init__(self, path_override: Path | None = None, cache_maxsize_mb: int = 512) -> None:
        """
        Initialize the extension cache.

        If `path_override` is not specified, the cache location is located at the user cache
        directory determined by `platformdirs`. Cache initialization creates the cache directory &
        its parents if they do not already exist.

        See: https://platformdirs.readthedocs.io/en/latest/api.html#platforms for OS-specific cache
        directory location information.

        Maximum cache size, in megabytes, can be specified using `cache_maxsize_mb`. Once the cache
        size is exceeded, VSIX packages are removed from the cache until the total cache size falls
        below the threshold. Packages are removed in reverse chronological order based on the file
        modification date.

        NOTE: Pruning will be performed on initialization if the existing cache size exceeds the
        specified threshold.
        """
        self._maxsize_mb = cache_maxsize_mb

        if path_override is None:
            self._cache_dir = platformdirs.user_cache_path(
                appname=APPNAME, appauthor=False, ensure_exists=False
            )
        else:
            self._cache_dir = path_override

        self._init_cache()

    def __contains__(self, item: object) -> bool:
        if not isinstance(item, dl.Extension):
            return False

        raise NotImplementedError

    @property
    def cache_size(self) -> float:
        """Calculate the current cache size, as MB."""
        total_bytes = sum(p.byte_size for p in self._package_cache)
        return bytes2megabytes(total_bytes)

    def _init_cache(self) -> None:
        """
        Initialize the extension cache.

        If the cache directory exists, parse the existing files into an instance cache.

        If the cache directory does not exist, an empty directory is created.
        """
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.vsix", case_sensitive=False):
                self._package_cache.add(CachedExtension.from_vsix_path(f))
        else:
            self._cache_dir.mkdir(parents=True)
            self._package_cache = set()

        # TODO: Check if cache needs to be pruned

    def _prune_cache(self, bytes_needed: int) -> None:
        """
        Prune extensions until the necessary number of bytes have been recovered.

        Packages are removed in reverse chronological order based on the file modification date.
        """
        raise NotImplementedError

    def info(self) -> None:
        """
        Print summary info for the current cache.

        Information provided:
            * Cache location
            * Cached extension count
            * Current cache size
            * Maximum cache size
        """
        print(
            (
                f"Cache Location: {self._cache_dir}"
                f"Cached Extensions: {len(self._package_cache)}"
                f"Cache Size: {self.cache_size: 0.2f} / {self._maxsize_mb: 0.2f} MB"
            )
        )

    def list(self) -> None:
        """List the VSIX extension packages currently available in the cache."""
        if not self._package_cache:
            print("No cached extensions.")
        else:
            print("Cache contents:\n")
            for p in self._package_cache:  # TODO: Sort this output by extension ID
                print(f" - {p}")

    def insert(self, vsix_filepath: Path) -> None:
        """Copy the provided VSIX package into the cache."""
        dest = self._cache_dir / vsix_filepath.name
        shutil.copy2(vsix_filepath, dest)

        # TODO: Check cache size
        self._package_cache.add(CachedExtension.from_vsix_path(dest))

    def remove(self, extension: dl.Extension) -> None:
        """Remove the specified extension from the VSIX package cache."""
        # TODO: Lookup extension from ID
        # TODO: Delete extension from disk
        # TODO: Delete extension from cache
        raise NotImplementedError

    def purge(self) -> None:
        """Remove all VSIX packages from the cache."""
        for p in self._package_cache:
            p.cache_path.unlink()

        self._package_cache = set()
        print("Extension cache purged.")

    def copy_to(self, extension: dl.Extension, dest: Path) -> Path:
        """Copy a cached VSIX package to the specified directory."""
        # TODO: Lookup extension from ID
        # TODO: Move extension to destination
        raise NotImplementedError
