"""Downloading a service's pinned data: HTTPS only, the final URL included after any redirect.

The caller checks what arrives against its pin. Network and HTTP errors are `OSError`s, as
`urllib` raises them.
"""

import shutil
import urllib.parse
import urllib.request
from pathlib import Path
from typing import IO, cast

from panther_engine.core.manifest import CHUNK

DOWNLOAD_TIMEOUT = 60.0


class DownloadError(Exception):
    """A URL, or the URL a redirect led to, that isn't HTTPS."""


def download(url: str, target: Path) -> Path:
    """Download `url` to `target` over HTTPS only, redirects included."""
    if urllib.parse.urlsplit(url).scheme != "https":
        raise DownloadError(f"refusing to download {url}: only https is allowed")
    # S310 flags opening a URL, for its file: and other schemes. The URL is https, checked
    # above, and where a redirect led is checked below.
    request = urllib.request.Request(url, headers={"User-Agent": "panther-engine"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:  # noqa: S310
        final = cast(str, response.geturl())
        if urllib.parse.urlsplit(final).scheme != "https":
            raise DownloadError(f"refusing to download {final}: only https is allowed")
        with target.open("wb") as out:
            shutil.copyfileobj(cast(IO[bytes], response), out, CHUNK)
    return target
