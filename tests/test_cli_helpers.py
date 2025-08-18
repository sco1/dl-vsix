import json
from pathlib import Path

import pytest

from dl_vsix.cli import _parse_extensions
from dl_vsix.dl import Extension


def test_no_spec_json_file_raises(tmp_path: Path) -> None:
    json_filepath = tmp_path / "extensions.json"
    with pytest.raises(ValueError, match="Source JSON"):
        _parse_extensions(json_filepath)


EXTENSION_JSON_CASES = (
    ({"extensions": ["ms-python.python"]}, [Extension.from_id("ms-python.python")]),
    (
        {"extensions": ["ms-python.python", "ms-python.vscode-pylance"]},
        [Extension.from_id("ms-python.python"), Extension.from_id("ms-python.vscode-pylance")],
    ),
)


@pytest.mark.parametrize(("base_dict", "truth_out"), EXTENSION_JSON_CASES)
def test_parse_extensions(
    base_dict: dict[str, list[str]], truth_out: list[Extension], tmp_path: Path
) -> None:
    json_filepath = tmp_path / "extensions.json"
    with json_filepath.open("w") as f:
        json.dump(base_dict, f)

    assert _parse_extensions(json_filepath) == truth_out
