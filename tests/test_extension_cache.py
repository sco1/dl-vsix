import datetime as dt
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from dl_vsix.dl import Extension
from dl_vsix.extension_cache import CachedExtension, ExtensionCache, bytes2megabytes

DUMMY_EXTENSION = Extension.from_id("ms-python.python")
DUMMY_PACKAGE = CachedExtension(
    extension=DUMMY_EXTENSION,
    version="1.0",
    # Remaining values are irrelevant for this test
    created_at=dt.datetime.now(),
    cache_path=Path(),
    byte_size=1_000_000,
)


def test_bytes2megabytes() -> None:
    assert bytes2megabytes(1_000_000) == pytest.approx(0.95, abs=1e-2)


def test_cached_extension_str() -> None:
    assert str(DUMMY_PACKAGE) == "ms-python.python_1.0 (0.95 MB)"


def test_cached_extension_from_path_no_exist_raises() -> None:
    filepath = Path() / "asdf.vsix"

    with pytest.raises(ValueError, match="does not exist"):
        CachedExtension.from_vsix_path(filepath)


def test_cached_extension_from_path_not_vsix_raises(tmp_path: Path) -> None:
    filepath = tmp_path / "asdf.foo"
    filepath.touch()  # Needs to at least exist

    with pytest.raises(ValueError, match="VSIX package"):
        CachedExtension.from_vsix_path(filepath)


def test_cached_extension_from_path(tmp_path: Path) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist

    # Pull file stats to create our truth output
    stats = filepath.stat()
    truth_obj = CachedExtension(
        extension=Extension.from_id("ms-python.python"),
        version="1.0",
        created_at=dt.datetime.fromtimestamp(stats.st_mtime),
        cache_path=filepath,
        byte_size=stats.st_size,
    )

    assert CachedExtension.from_vsix_path(filepath) == truth_obj


def test_extension_cache_default_loc(tmp_path: Path, mocker: MockerFixture) -> None:
    user_cache = tmp_path / "fake" / "user_cache"
    patched = mocker.patch(
        "dl_vsix.extension_cache.platformdirs.user_cache_path", return_value=user_cache
    )

    ec = ExtensionCache()

    patched.assert_called()
    assert ec._cache_dir == user_cache
    assert user_cache.exists()


def test_extension_cache_loc_override(tmp_path: Path, mocker: MockerFixture) -> None:
    # Mock a user cache so we can ensure that platformdirs isn't called
    user_cache = tmp_path / "fake" / "user_cache"
    patched = mocker.patch(
        "dl_vsix.extension_cache.platformdirs.user_cache_path", return_value=user_cache
    )

    cache_override = tmp_path / "cache" / "override"
    ec = ExtensionCache(path_override=cache_override)

    patched.assert_not_called()
    assert ec._cache_dir == cache_override
    assert cache_override.exists()


def test_cache_size(tmp_path: Path) -> None:
    ec = ExtensionCache(path_override=tmp_path)
    ec._package_cache = {DUMMY_EXTENSION: DUMMY_PACKAGE}

    assert ec.cache_size == pytest.approx(0.95, abs=1e-2)


def test_get_cached_version(tmp_path: Path) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()
    ec = ExtensionCache(path_override=tmp_path)

    assert ec.cached_version(DUMMY_EXTENSION) == "1.0"
    assert ec.cached_version(Extension.from_id("fake.package")) is None


CONTAINS_CASES = (
    (DUMMY_EXTENSION, True),
    (DUMMY_PACKAGE, True),
    ("ms-python.python", False),
    (Extension.from_id("abcd.efg"), False),
    ("abcd.efg", False),
    (12, False),
)


@pytest.mark.parametrize(("query_obj", "truth_contains"), CONTAINS_CASES)
def test_cache_contain(query_obj: object, truth_contains: bool, tmp_path: Path) -> None:
    ec = ExtensionCache(path_override=tmp_path)
    ec._package_cache = {DUMMY_EXTENSION: DUMMY_PACKAGE}

    assert (query_obj in ec) == truth_contains


def test_nonempty_cache_init(tmp_path: Path) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vSiX"  # Checking case insensitive
    filepath.touch()  # Needs to exist

    ec = ExtensionCache(path_override=tmp_path)
    assert len(ec._package_cache) == 1


def test_prune_cache_noop(tmp_path: Path) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist
    ec = ExtensionCache(path_override=tmp_path)
    assert len(ec._package_cache) == 1

    ec._prune_cache()
    assert len(ec._package_cache) == 1


def test_prune_cache(tmp_path: Path) -> None:
    # Initial creation order irrelevant, since we're going to be manually setting the package cache
    # after initialization
    small_ext = Extension.from_id("small.extension")
    small_filepath = tmp_path / "small.extension_1.0.vsix"
    small_filepath.touch()
    medium_ext = Extension.from_id("medium.extension")
    medium_filepath = tmp_path / "medium.extension_1.0.vsix"
    medium_filepath.touch()
    large_ext = Extension.from_id("large.extension")
    large_filepath = tmp_path / "large.extension_1.0.vsix"
    large_filepath.touch()

    ec = ExtensionCache(path_override=tmp_path)
    assert len(ec._package_cache) == 3

    # Update internals now that we're initialized & force a purge
    ec._maxsize_mb = 1  # Size so large extension should survive

    # Creation order is medium, small, large
    # Purge order should be the same
    start_time = dt.datetime.now()
    ec._package_cache = {
        medium_ext: CachedExtension(
            extension=medium_ext,
            version="1.0",
            created_at=start_time,
            cache_path=medium_filepath,
            byte_size=700_000,
        ),
        small_ext: CachedExtension(
            extension=small_ext,
            version="1.0",
            created_at=start_time + dt.timedelta(seconds=1),
            cache_path=small_filepath,
            byte_size=300_000,
        ),
        large_ext: CachedExtension(
            extension=large_ext,
            version="1.0",
            created_at=start_time + dt.timedelta(seconds=2),
            cache_path=large_filepath,
            byte_size=1_000_000,
        ),
    }

    ec._prune_cache()
    assert len(ec._package_cache) == 1
    assert large_ext in ec._package_cache
    assert len(list(tmp_path.glob("*.vsix"))) == 1


def test_print_cache_info(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist

    ec = ExtensionCache(path_override=tmp_path)
    ec.info()

    truth_out = (
        f"Cache Location: {tmp_path}\n"
        "Cached Extensions: 1\n"
        "Cache Size:  0.00 /  512.00 MB\n\n"  # Extra newline for print statement
    )
    all_out = capsys.readouterr().out
    assert all_out == truth_out


def test_list_cache_contents_empty_cache(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    ec = ExtensionCache(path_override=tmp_path)
    ec.list()

    truth_out = "No cached extensions.\n"
    all_out = capsys.readouterr().out
    assert all_out == truth_out


def test_list_cache_contents(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist

    ec = ExtensionCache(path_override=tmp_path)
    ec.list()

    truth_out = "Cache contents:\n\n - ms-python.python_1.0 (0.00 MB)\n"
    all_out = capsys.readouterr().out
    assert all_out == truth_out


def test_cache_insert_no_exist(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    ec = ExtensionCache(path_override=cache_dir)
    assert len(ec._package_cache) == 0

    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()
    ec.insert(filepath)

    assert len(ec._package_cache) == 1


def test_cache_insert_exist_older(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    filepath = cache_dir / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist
    ec = ExtensionCache(path_override=cache_dir)
    assert len(ec._package_cache) == 1

    new_ver = tmp_path / "ms-python.python_2.0.vsix"
    new_ver.touch()
    ec.insert(new_ver)

    assert len(ec._package_cache) == 1
    assert ec._package_cache[DUMMY_EXTENSION].version == "2.0"


def test_cache_insert_same_ver(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    filepath = cache_dir / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist
    ec = ExtensionCache(path_override=cache_dir)
    assert len(ec._package_cache) == 1

    old_timestamp = ec._package_cache[DUMMY_EXTENSION].created_at
    ec.insert(filepath)

    assert len(ec._package_cache) == 1
    assert ec._package_cache[DUMMY_EXTENSION].created_at == old_timestamp


def test_cache_insert_same_ver_force(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    filepath = cache_dir / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist
    ec = ExtensionCache(path_override=cache_dir)
    assert len(ec._package_cache) == 1

    old_timestamp = ec._package_cache[DUMMY_EXTENSION].created_at
    same_ver = tmp_path / "ms-python.python_1.0.vsix"
    same_ver.touch()
    ec.insert(same_ver, force=True)

    assert len(ec._package_cache) == 1
    assert ec._package_cache[DUMMY_EXTENSION].created_at >= old_timestamp


def test_remove_extension(tmp_path: Path) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist

    ec = ExtensionCache(path_override=tmp_path)
    assert len(ec._package_cache) == 1

    ec.remove(DUMMY_EXTENSION)
    assert len(ec._package_cache) == 0
    assert len(list(tmp_path.glob("*.vsix"))) == 0


def test_remove_extension_not_in_cache(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    ec = ExtensionCache(path_override=tmp_path)

    ec.remove(DUMMY_EXTENSION)
    truth_out = "Extension not in cache: 'ms-python.python'\n"
    all_out = capsys.readouterr().out
    assert all_out == truth_out


def test_cache_purge(tmp_path: Path) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist

    ec = ExtensionCache(path_override=tmp_path)
    assert len(ec._package_cache) == 1

    ec.purge()
    assert len(ec._package_cache) == 0
    assert len(list(tmp_path.glob("*.vsix"))) == 0


def test_cache_copy_dest_not_dir_raises(tmp_path: Path) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist
    ec = ExtensionCache(path_override=tmp_path)

    dest_not_exist = tmp_path / "asdf"
    with pytest.raises(ValueError, match="not a directory or does not exist"):
        ec.copy_to(DUMMY_EXTENSION, dest_not_exist)

    dest_not_dir = tmp_path / "foo.txt"
    with pytest.raises(ValueError, match="not a directory or does not exist"):
        ec.copy_to(DUMMY_EXTENSION, dest_not_dir)


def test_cache_copy_package_not_in_cache_raises(tmp_path: Path) -> None:
    ec = ExtensionCache(path_override=tmp_path)
    with pytest.raises(ValueError, match="not available in cache"):
        ec.copy_to(Extension.from_id("missing.extension"), tmp_path)


def test_cache_copy_package(tmp_path: Path) -> None:
    filepath = tmp_path / "ms-python.python_1.0.vsix"
    filepath.touch()  # Needs to exist

    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    ec = ExtensionCache(path_override=tmp_path)
    copied = ec.copy_to(DUMMY_EXTENSION, dest_dir)
    assert copied.exists()
