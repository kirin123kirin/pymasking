"""境界値テスト: pymasking.core.masker"""
import re
import pytest
from pymasking.core.masker import mask_text


class TestMaskTextEmpty:
    def test_empty_string_blackout(self):
        assert mask_text("", mode="blackout") == ""

    def test_empty_string_unique(self):
        assert mask_text("", mode="unique") == ""


class TestMaskTextNoMatch:
    def test_plain_text_unchanged_blackout(self):
        text = "これは普通の文章です。"
        assert mask_text(text, mode="blackout") == text

    def test_plain_text_unchanged_unique(self):
        text = "これは普通の文章です。"
        assert mask_text(text, mode="unique") == text


class TestMaskTextBlackout:
    def test_email_replaced_with_bullets(self):
        result = mask_text("連絡: user@example.com", mode="blackout")
        assert "@" not in result
        assert "●" in result

    def test_phone_replaced_with_bullets(self):
        result = mask_text("電話: 090-1234-5678", mode="blackout")
        assert "●" in result

    def test_amount_replaced(self):
        result = mask_text("請求額は100,000円です。", mode="blackout")
        assert "●" in result

    def test_length_of_masked_matches_original_chars(self):
        original = "user@example.com"
        masked = mask_text(original, mode="blackout")
        # blackout replaces each char with ●, so lengths should match
        assert len(masked) == len(original)


class TestMaskTextUnique:
    def test_email_gets_sequential_label(self):
        result = mask_text("user@example.com", mode="unique")
        assert re.search(r"メール\d+", result)

    def test_two_different_values_get_different_numbers(self):
        result = mask_text("a@x.com と b@y.com", mode="unique")
        numbers = re.findall(r"メール(\d+)", result)
        assert len(numbers) == 2
        assert numbers[0] != numbers[1]

    def test_same_value_gets_same_label(self):
        # mask_text creates a fresh UniqueCounter each call,
        # but within a single call the same value should map to the same label
        result = mask_text("a@x.com と a@x.com", mode="unique")
        numbers = re.findall(r"メール(\d+)", result)
        assert len(numbers) == 2
        assert numbers[0] == numbers[1]


class TestMaskTextCategoryFilter:
    def test_only_email_masked_when_filtered(self):
        text = "user@example.com / 090-1234-5678"
        result = mask_text(text, mode="blackout", categories={"メール"})
        # email masked (no @), phone kept
        assert "@" not in result
        assert "090-1234-5678" in result

    def test_only_phone_masked_when_filtered(self):
        text = "user@example.com / 090-1234-5678"
        result = mask_text(text, mode="blackout", categories={"電話"})
        assert "@" in result
        assert "090-1234-5678" not in result
