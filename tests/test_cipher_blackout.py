"""境界値テスト: pymasking.core.cipher.blackout"""
import pytest
from pymasking.core.cipher.blackout import encode


class TestEncodeEmpty:
    def test_empty_string(self):
        assert encode("") == ""


class TestEncodeSingleChar:
    def test_ascii(self):
        assert encode("a") == "●"

    def test_space(self):
        assert encode(" ") == "●"

    def test_tab(self):
        assert encode("\t") == "●"

    def test_newline(self):
        assert encode("\n") == "●"

    def test_japanese_single(self):
        assert encode("田") == "●"

    def test_emoji(self):
        assert encode("😀") == "●"

    def test_symbol(self):
        assert encode("@") == "●"


class TestEncodeLength:
    def test_length_preserved_ascii(self):
        text = "abc"
        assert encode(text) == "●" * len(text)

    def test_length_preserved_japanese(self):
        text = "田中太郎"
        assert encode(text) == "●" * len(text)

    def test_length_preserved_mixed(self):
        text = "田中a@1"
        assert encode(text) == "●" * len(text)

    def test_already_masked(self):
        assert encode("●●●") == "●●●"

    def test_whitespace_only(self):
        text = "   "
        assert encode(text) == "●" * len(text)

    def test_long_string(self):
        text = "a" * 10_000
        assert encode(text) == "●" * 10_000
