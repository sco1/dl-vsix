import functools
import json
from enum import IntEnum

import httpx


class ExtensionQueryFlags(IntEnum):
    """
    Determine which set of information is retrieved when reading published extensions.

    See: https://github.com/microsoft/azure-devops-node-api/blob/master/api/interfaces/GalleryInterfaces.ts
    """

    NONE = 0
    IncludeVersions = 1
    IncludeFiles = 2
    IncludeCategoryAndTags = 4
    IncludeSharedAccounts = 8
    IncludeVersionProperties = 16
    ExcludeNonValidated = 32
    IncludeInstallationTargets = 64
    IncludeAssetUri = 128
    IncludeStatistics = 256
    IncludeLatestVersionOnly = 512
    UseFallbackAssetUri = 1024
    IncludeMetadata = 2048
    IncludeMinimalPayloadForVsIde = 4096
    IncludeLcids = 8192
    IncludeSharedOrganizations = 16384
    IncludeNameConflictInfo = 32768
    IncludeLatestPrereleaseAndStableVersionOnly = 65536
    AllAttributes = 16863


class ExtensionQueryFilterType(IntEnum):
    """
    Type of extension filters that are supported in the queries.

    See: https://github.com/microsoft/azure-devops-node-api/blob/master/api/interfaces/GalleryInterfaces.ts
    """

    Tag = 1
    DisplayName = 2
    Private = 3
    Id = 4
    Category = 5
    ContributionType = 6
    Name = 7
    InstallationTarget = 8
    Featured = 9
    SearchText = 10
    FeaturedInCategory = 11
    ExcludeWithFlags = 12
    IncludeWithFlags = 13
    Lcid = 14
    InstallationTargetVersion = 15
    InstallationTargetVersionRange = 16
    VsixMetadata = 17
    PublisherName = 18
    PublisherDisplayName = 19
    IncludeWithPublisherFlags = 20
    OrganizationSharedWith = 21
    ProductArchitecture = 22
    TargetPlatform = 23
    ExtensionName = 24


# Reversed engineered from: github.com/microsoft/vscode-vsce/blob/main/src/show.ts
BASE_URL = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
API_VERSION = "3.0-preview.1"
HEADER = {
    "Accept": f"application/json;api-version={API_VERSION}",
    "Content-Type": "application/json",
}
QUERY_FLAGS = [
    ExtensionQueryFlags.IncludeLatestVersionOnly,
]


@functools.lru_cache
def query_latest_version(extension_id: str) -> str:
    """Query Gallery API for the latest released verrsion of the specified extension."""
    # flags are OR masked
    ored_flags = 0
    for f in QUERY_FLAGS:
        ored_flags |= f

    data = {
        "filters": [
            {
                "pageNumber": 1,
                "pageSize": 1,
                "criteria": [{"filterType": ExtensionQueryFilterType.Name, "value": extension_id}],
            }
        ],
        "assetTypes": [],
        "flags": ored_flags,
    }

    with httpx.Client() as client:
        r = client.post(
            BASE_URL,
            # Doesn't seem to work without pre-stringify
            data=json.dumps(data),  # type: ignore[arg-type]
            headers=HEADER,
        )
        r.raise_for_status()
        returned = r.json()

    # If the extension has platform specific builds, it will have all of these versions separated
    # out, but all should have the same version info since we're only requesting the latest
    versions = returned["results"][0]["extensions"][0]["versions"]
    return versions[0]["version"]  # type: ignore[no-any-return]
