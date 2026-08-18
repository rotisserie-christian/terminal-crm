from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.utils.token_count import count_file_tokens, count_tokens, main


def test_count_tokens_uses_encode_without_special_tokens():
    tokenizer = MagicMock()
    tokenizer.encode.return_value = [1, 2, 3, 4]

    assert count_tokens("hello world", tokenizer) == 4
    tokenizer.encode.assert_called_once_with("hello world", add_special_tokens=False)


def test_count_file_tokens_reads_utf8(tmp_path: Path):
    path = tmp_path / "notes.md"
    path.write_text("alpha beta", encoding="utf-8")

    tokenizer = MagicMock()
    tokenizer.encode.return_value = [10, 20]

    assert count_file_tokens(path, tokenizer=tokenizer) == 2
    tokenizer.encode.assert_called_once_with("alpha beta", add_special_tokens=False)


def test_count_file_tokens_missing_file(tmp_path: Path):
    tokenizer = MagicMock()
    with pytest.raises(FileNotFoundError):
        count_file_tokens(tmp_path / "missing.txt", tokenizer=tokenizer)


@patch("src.utils.token_count.load_tokenizer")
def test_count_file_tokens_loads_tokenizer_when_omitted(mock_load, tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")

    tokenizer = MagicMock()
    tokenizer.encode.return_value = [7]
    mock_load.return_value = tokenizer

    assert count_file_tokens(path, model_name="some/model") == 1
    mock_load.assert_called_once_with("some/model")


def test_main_prints_count(tmp_path: Path, capsys):
    path = tmp_path / "a.txt"
    path.write_text("hi", encoding="utf-8")
    tokenizer = MagicMock()
    tokenizer.encode.return_value = [1, 2, 3]

    with patch("src.utils.token_count.load_tokenizer", return_value=tokenizer):
        assert main([str(path)]) == 0

    assert capsys.readouterr().out.strip() == "3"


def test_main_missing_file(tmp_path: Path):
    assert main([str(tmp_path / "nope.txt")]) == 1
