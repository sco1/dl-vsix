from __future__ import annotations

import datetime as dt
import operator
import shutil
import typing as t
from pathlib import Path

import platformdirs

from dl_vsix import APPNAME, dl

DEFAULT_CACHE_MAXSIZE_MB = 512


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

    _package_cache: dict[dl.Extension, CachedExtension]

    def __init__(
        self, path_override: Path | None = None, cache_maxsize_mb: int = DEFAULT_CACHE_MAXSIZE_MB
    ) -> None:
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
        if isinstance(item, dl.Extension):
            return item in self._package_cache
        elif isinstance(item, CachedExtension):
            return item.extension in self._package_cache
        else:
            return False

    @property
    def cache_size(self) -> float:
        """Calculate the current cache size, as MB."""
        total_bytes = sum(p.byte_size for p in self._package_cache.values())
        return bytes2megabytes(total_bytes)

    def cached_version(self, extension: dl.Extension) -> str | None:
        """Return the cached version of the query extension, or `None` if it is not in the cache."""
        query = self._package_cache.get(extension, None)
        if query is None:
            return None
        else:
            return query.version

    def _init_cache(self) -> None:
        """
        Initialize the extension cache.

        If the cache directory exists, parse the existing files into an instance cache.

        If the cache directory does not exist, an empty directory is created.
        """
        self._package_cache = {}
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.vsix", case_sensitive=False):
                ext = CachedExtension.from_vsix_path(f)
                self._package_cache[ext.extension] = ext
        else:
            self._cache_dir.mkdir(parents=True)

    def _prune_cache(self) -> None:
        """
        Prune extensions if total cache size exceeds the configured threshold.

        Packages are removed in reverse chronological order based on the file modification date.
        """
        if self.cache_size <= self._maxsize_mb:
            return

        print(f"Cache size exceeded: ({self.cache_size:0.2f} MB > {self._maxsize_mb:0.2f} MB)")
        bytes_needed = (self.cache_size - self._maxsize_mb) * (1 << 20)
        # Probably should have a more efficient way to maintain this, but fine for now
        size_sorted = sorted(
            self._package_cache.values(), key=operator.attrgetter("created_at"), reverse=True
        )

        to_purge = []
        freed_bytes = 0
        while freed_bytes < bytes_needed:
            ext = size_sorted.pop()
            freed_bytes += ext.byte_size
            to_purge.append(ext)

        for p in to_purge:
            self.remove(p.extension)

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
                f"Cache Location: {self._cache_dir}\n"
                f"Cached Extensions: {len(self._package_cache)}\n"
                f"Cache Size: {self.cache_size: 0.2f} / {self._maxsize_mb: 0.2f} MB\n"
            )
        )

    def list(self) -> None:
        """List the VSIX extension packages currently available in the cache."""
        if not self._package_cache:
            print("No cached extensions.")
        else:
            print("Cache contents:\n")
            name_sorted = sorted(self._package_cache.values(), key=operator.attrgetter("extension"))
            for p in name_sorted:
                print(f" - {p}")

    def insert(self, vsix_filepath: Path, force: bool = False) -> None:
        """
        Copy the provided VSIX package into the cache.

        Copying is skipped if the VSIX package of the same version is already in the cache, unless
        `force` is `True`.
        """
        pre = CachedExtension.from_vsix_path(vsix_filepath)  # To get version info
        chk = self._package_cache.get(pre.extension, None)
        if chk is not None:
            if (chk.version == pre.version) and not force:
                # Short circuit on same version
                return

            # Otherwise, assume we have downloaded a more recent version, or are forcing
            # Upstream we are only downloading the most recent release, so not going to bother
            # considering that we've downloaded an older version that what's in the cache
            self.remove(pre.extension)

        dest = self._cache_dir / vsix_filepath.name
        shutil.copy2(vsix_filepath, dest)

        ext = CachedExtension.from_vsix_path(dest)
        self._package_cache[ext.extension] = ext

        self._prune_cache()

    def remove(self, extension: dl.Extension) -> None:
        """Remove the specified extension from the VSIX package cache."""
        ext = self._package_cache.pop(extension, None)
        if ext is None:
            # Package not in cache
            print(f"Extension not in cache: '{extension}'")
            return

        ext.cache_path.unlink()
        print(f"Extension removed from cache: {ext.cache_path.stem}")

    def purge(self) -> None:
        """Remove all VSIX packages from the cache."""
        for p in self._package_cache.values():
            p.cache_path.unlink()

        self._package_cache = {}
        print("Extension cache purged.")

    def copy_to(self, extension: dl.Extension, dest: Path) -> Path:
        """Copy a cached VSIX package to the specified directory."""
        if not dest.is_dir():
            raise ValueError("Destination is not a directory or does not exist.")

        ext = self._package_cache.get(extension, None)
        if ext is None:
            raise ValueError(f"Extension not available in cache: '{extension}'")

        dest_filepath = dest / f"{ext.extension}_{ext.version}.vsix"
        shutil.copy2(ext.cache_path, dest_filepath)
        return dest_filepath
