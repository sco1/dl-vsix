# dl-vsix

[![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fsco1%2Fdl-vsix%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&logo=python&logoColor=FFD43B)](https://github.com/sco1/dl-vsix/blob/main/pyproject.toml)
[![GitHub Release](https://img.shields.io/github/v/release/sco1/dl-vsix)](https://github.com/sco1/dl-vsix/releases)
[![GitHub License](https://img.shields.io/github/license/sco1/dl-vsix?color=magenta)](https://github.com/sco1/dl-vsix/blob/main/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/dl-vsix/main.svg)](https://results.pre-commit.ci/latest/github/sco1/dl-vsix/main)

Download VSIX bundles for offline extension installation

## Installation

Wheels are built in CI for each released version; the latest release can be found at: <https://github.com/sco1/dl-vsix/releases/latest>

You can confirm proper installation via the `dl_vsix` CLI:
<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["dl_vsix", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"\n```text\n$ dl_vsix --help\n{out.stdout.rstrip()}\n```\n\n"
)
]]] -->

```text
$ dl_vsix --help
usage: dl_VSIX [-h] [-s SPEC_FILE] [-o OUT_DIR] [-f] [-z] [extension]

Download VSIX bundles for offline extension installation.

positional arguments:
  extension             Single extension by ID

options:
  -h, --help            show this help message and exit
  -s, --spec_file SPEC_FILE
                        JSON-specified collection of extensions
  -o, --out_dir OUT_DIR
                        Download directory (default: ./vsix)
  -f, --follow_deps     Trace extension's dependencies.
  -z, --zip             Zip the download extension(s)
```

<!-- [[[end]]] -->

## Usage

### Extension Specification

`dl-vsiz` provides two methods for identifying extension(s) to download. Note that these options are mutually exclusive.

#### Single Extension

A single extension may be specified as a positional argument using the form  `<publisher>.<package>`, e.g. `ms-python.python`

#### JSON List

Multiple packages may be specified using a JSON file. Extension IDs are assumed to be provided by an `"extensions"` field as a list of strings, e.g.:

```json
{
    "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance"
    ]
}
```
