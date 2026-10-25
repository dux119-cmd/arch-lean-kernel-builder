#!/usr/bin/env python3

"""Find the latest stable kernel on kernel.org."""

import json
from dataclasses import dataclass
from urllib.request import urlopen

RELEASES_URL: str = "https://www.kernel.org/releases.json"
REQUEST_TIMEOUT_S: int = 30


@dataclass(frozen=True)
class KernelRelease:
    version: str
    url: str


def latest_stable() -> KernelRelease:
    with urlopen(RELEASES_URL, timeout=REQUEST_TIMEOUT_S) as resp:
        releases = json.load(resp)["releases"]
    for release in releases:
        if release["moniker"] == "stable":
            return KernelRelease(version=release["version"], url=release["source"])
    raise RuntimeError("no stable release listed on kernel.org")
