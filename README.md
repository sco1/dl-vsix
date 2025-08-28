# dl-vsix

[![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fsco1%2Fdl-vsix%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&logo=python&logoColor=FFD43B)](https://github.com/sco1/dl-vsix/blob/main/pyproject.toml)
[![GitHub Release](https://img.shields.io/github/v/release/sco1/dl-vsix)](https://github.com/sco1/dl-vsix/releases)
[![GitHub License](https://img.shields.io/github/license/sco1/dl-vsix?color=magenta)](https://github.com/sco1/dl-vsix/blob/main/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/dl-vsix/main.svg)](https://results.pre-commit.ci/latest/github/sco1/dl-vsix/main)

Download VSIX bundles for offline extension installation.

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
Usage: dl_vsix [OPTIONS] COMMAND [ARGS]...

  Download VSIX bundles for offline extension installation.

Options:
  --help  Show this message and exit.

Commands:
  download  Download VSIX extension packages.
  cache     Package cache utilities
```

<!-- [[[end]]] -->

## Usage

Extension downloads are accomplished using the `dl_vsix download` command:
<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["dl_vsix", "download", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"\n```text\n$ dl_vsix download --help\n{out.stdout.rstrip()}\n```\n\n"
)
]]] -->

```text
$ dl_vsix download --help
Usage: dl_vsix download [OPTIONS] [EXTENSION_ID]

  Download VSIX extension packages.

  NOTE: `extension_id` and `spec_file` are mutually exclusive.

Arguments:
  [EXTENSION_ID]  Single extension by ID

Options:
  -s, --spec_file FILE     JSON-specified collection of extensions
  -o, --out_dir DIRECTORY  Download directory  [default: vsix]
  -f, --follow_deps        Trace extension's dependencies
  -z, --zip                Zip the download extension(s)
  --help                   Show this message and exit.
```

<!-- [[[end]]] -->

### Extension Specification

`dl-vsix` provides two methods for identifying extension(s) to download. Note that these options are mutually exclusive.

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

### Dependency Tracing

Each VSIX package should have an `extension/package.json` detailing extension information; if an extension has additional dependencies, they should be declared in an `"extensionDependencies"` field as a list of extension ID strings.

By default, `dl-vsix` will not trace these dependencies. To enable dependency tracing, use the `-f/--follow_deps` flag to trace the dependencies for each download extension & add them to the download queue if any are found.

## Download Caching

`dl-vsix` implements a simple download cache to help prevent repeated downloads of the latest version of an extension. The cache is FIFO based on file modification date, as creation date is not available on all platforms.

By default, this is located in the user's cache directory, as defined by [`platformdirs`](https://platformdirs.readthedocs.io/en/latest/). OS specific location information can be found under the [Platforms API documentation](https://platformdirs.readthedocs.io/en/latest/api.html#platforms). The cache directory can be overridden using the `DL_VSIX_CACHE_DIR` environment variable; note that changing this directory location does not erase existing contents, nor are existing contents transferred to this location.

Cache size defaults to `512` MB, and is configurable using the `DL_VSIX_CACHE_SIZE` environment variable. Cache pruning is only conducted either when the tool initializes, or a new download is inserted into the cache.

### CLI Interface

Cache utilities are accessible via the `dl_vsix cache` command:
<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["dl_vsix", "cache", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"\n```text\n$ dl_vsix cache --help\n{out.stdout.rstrip()}\n```\n\n"
)
]]] -->

```text
$ dl_vsix cache --help
Usage: dl_vsix cache [OPTIONS] COMMAND [ARGS]...

  Package cache utilities

Options:
  --help  Show this message and exit.

Commands:
  info    Show cache information.
  list    List cache contents.
  remove  Remove extension(s) from cache.
  purge   Clear package cache.
```

<!-- [[[end]]] -->
