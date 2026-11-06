import io
from pathlib import Path
from types import TracebackType
from typing import Self

import pytest

from panther_engine.core import download as module
from panther_engine.core.download import DOWNLOAD_TIMEOUT, DownloadError, download


class Response(io.BytesIO):
    """A stand-in for urlopen's response: the body, and the URL a redirect led to."""

    def __init__(self, body: bytes, final: str) -> None:
        super().__init__(body)
        self.final = final

    def geturl(self) -> str:
        return self.final

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def __enter__(self) -> Self:
        return self


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list[tuple[object, float]]:
    """Each request urlopen was given, with its timeout. The response redirects to `final`."""
    calls: list[tuple[object, float]] = []

    def urlopen(request: object, timeout: float) -> Response:
        calls.append((request, timeout))
        url = getattr(request, "full_url", "")
        final = "http://elsewhere/file" if url.endswith("redirect-to-http") else url
        return Response(b"payload\n", final)

    monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
    return calls


def test_an_https_url_is_written_to_the_target(
    opened: list[tuple[object, float]], tmp_path: Path
) -> None:
    target = tmp_path / "file"

    assert download("https://example.org/file", target) == target

    assert target.read_bytes() == b"payload\n"
    request, timeout = opened[0]
    assert getattr(request, "full_url", None) == "https://example.org/file"
    assert getattr(request, "headers", {}) == {"User-agent": "panther-engine"}
    assert timeout == DOWNLOAD_TIMEOUT == 60.0


@pytest.mark.parametrize("url", ["http://example.org/file", "file:///etc/passwd", "ftp://x/y"])
def test_a_url_that_isnt_https_is_refused_before_any_request(
    url: str, opened: list[tuple[object, float]], tmp_path: Path
) -> None:
    with pytest.raises(DownloadError, match="only https"):
        download(url, tmp_path / "file")

    assert opened == []
    assert not (tmp_path / "file").exists()


def test_a_redirect_to_http_is_refused(opened: list[tuple[object, float]], tmp_path: Path) -> None:
    with pytest.raises(DownloadError, match="refusing to download http://elsewhere"):
        download("https://example.org/redirect-to-http", tmp_path / "file")

    assert not (tmp_path / "file").exists()
