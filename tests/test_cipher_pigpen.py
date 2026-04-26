"""境界値テスト: pymasking.core.cipher.pigpen"""
import pytest
from pymasking.core.cipher.pigpen import encrypt

SYMBOLS = set("⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭")


class TestEncryptEmpty:
    def test_empty_string(self):
        assert encrypt("") == ""


class TestEncryptOutput:
    def test_output_only_symbols(self):
        result = encrypt("hello")
        assert all(c in SYMBOLS for c in result)

    def test_single_ascii(self):
        result = encrypt("a")
        assert len(result) == 2          # 1バイト = 2 hex 文字 = 2 シンボル
        assert all(c in SYMBOLS for c in result)

    def test_single_japanese(self):
        result = encrypt("田")
        assert len(result) == 6          # UTF-8 3バイト = 6 hex 文字
        assert all(c in SYMBOLS for c in result)

    def test_emoji(self):
        result = encrypt("😀")
        assert len(result) == 8          # UTF-8 4バイト
        assert all(c in SYMBOLS for c in result)

    def test_whitespace(self):
        result = encrypt(" ")
        assert len(result) == 2
        assert all(c in SYMBOLS for c in result)

    def test_special_chars(self):
        result = encrypt("@#$%")
        assert all(c in SYMBOLS for c in result)

    @pytest.mark.parametrize("text", [
        "hello",
        "田中太郎",
        "Hello, World!",
        "090-1234-5678",
        "tanaka@example.com",
        "😀🎉",
        "  空白を含む  ",
        "a" * 500,
        "特殊文字: !@#$%^&*()",
        "\n",
        "\t",
    ])
    def test_output_all_symbols(self, text):
        result = encrypt(text)
        assert all(c in SYMBOLS for c in result)
