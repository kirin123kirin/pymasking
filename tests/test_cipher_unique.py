"""境界値テスト: pymasking.core.cipher.unique"""
import pytest
from pymasking.core.cipher.unique import UniqueCounter


class TestDefaultPad:
    def setup_method(self):
        self.uc = UniqueCounter()

    def test_first_occurrence(self):
        result = self.uc.encode("人物", "田中太郎")
        assert result == "人物001"

    def test_second_distinct_text(self):
        self.uc.encode("人物", "田中太郎")
        result = self.uc.encode("人物", "鈴木花子")
        assert result == "人物002"

    def test_same_text_returns_cached(self):
        first  = self.uc.encode("人物", "田中太郎")
        second = self.uc.encode("人物", "田中太郎")
        assert first == second == "人物001"

    def test_different_categories_independent(self):
        r1 = self.uc.encode("人物", "田中太郎")
        r2 = self.uc.encode("組織", "株式会社A")
        assert r1 == "人物001"
        assert r2 == "組織001"

    def test_counter_increments(self):
        for i in range(1, 6):
            result = self.uc.encode("日付", f"2024-01-{i:02d}")
            assert result == f"日付{i:03d}"


class TestPadVariants:
    def test_pad_zero(self):
        uc = UniqueCounter(pad=0)
        assert uc.encode("人物", "田中") == "人物1"

    def test_pad_one(self):
        uc = UniqueCounter(pad=1)
        assert uc.encode("人物", "田中") == "人物1"

    def test_pad_two(self):
        uc = UniqueCounter(pad=2)
        assert uc.encode("人物", "田中") == "人物01"

    def test_pad_five(self):
        uc = UniqueCounter(pad=5)
        assert uc.encode("人物", "田中") == "人物00001"


class TestOverflow:
    def test_counter_exceeds_pad(self):
        uc = UniqueCounter(pad=1)
        for i in range(9):
            uc.encode("X", f"text{i}")
        result = uc.encode("X", "text_new")
        assert result == "X10"   # pad=1 を超えても zfill で拡張される


class TestEdgeCases:
    def test_empty_category(self):
        uc = UniqueCounter()
        result = uc.encode("", "田中太郎")
        assert result == "001"

    def test_empty_text(self):
        uc = UniqueCounter()
        r1 = uc.encode("人物", "")
        r2 = uc.encode("人物", "")
        assert r1 == r2    # 空文字列もキャッシュされる
