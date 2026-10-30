from pathlib import Path

import pytest

from panther_engine.core.data import DataFolderError, data_root, service_folder


def test_the_folder_comes_from_panther_data_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", "/data")

    assert service_folder("csnp", "9") == Path("/data/csnp/9")


def test_an_explicit_folder_wins_over_the_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", "/data")

    assert service_folder("csnp", "9", tmp_path) == tmp_path / "csnp" / "9"


@pytest.mark.parametrize("value", [None, ""])
def test_without_a_folder_the_error_names_the_variable(
    value: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    if value is None:
        monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)
    else:
        monkeypatch.setenv("PANTHER_DATA_DIR", value)

    with pytest.raises(DataFolderError, match="PANTHER_DATA_DIR"):
        data_root()
