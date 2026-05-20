"""Tests for archived MagicMock cleanup helper."""

from scripts._archive.clean_magicmocks import clean_magicmocks


def test_clean_magicmocks_preserves_unrelated_numeric_directories(tmp_path):
    legitimate = tmp_path / "2024"
    legitimate.mkdir()
    (legitimate / "data.txt").write_text("keep", encoding="utf-8")

    mock_child = tmp_path / "MagicMock" / "123"
    mock_child.mkdir(parents=True)
    (mock_child / "mock.txt").write_text("remove", encoding="utf-8")

    removed = clean_magicmocks(tmp_path)

    assert removed >= 1
    assert legitimate.exists()
    assert (legitimate / "data.txt").exists()
    assert not (tmp_path / "MagicMock").exists()
