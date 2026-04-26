"""境界値テスト: pymasking.core.masker"""
import re
import pytest
from pymasking.core.masker import mask_text, unmask_text

_PIGPEN_SYMBOLS = set("⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭")


class TestMaskTextEmpty:
    def test_empty_string_blackout(self):
        assert mask_text("", mode="blackout") == ""

    def test_empty_string_unique(self):
        assert mask_text("", mode="unique") == ""

    def test_empty_string_pigpen(self):
        assert mask_text("", mode="pigpen") == ""


class TestMaskTextNoMatch:
    def test_plain_text_unchanged_blackout(self):
        text = "これは普通の文章です。"
        assert mask_text(text, mode="blackout") == text

    def test_plain_text_unchanged_unique(self):
        text = "これは普通の文章です。"
        assert mask_text(text, mode="unique") == text

    def test_plain_text_unchanged_pigpen(self):
        text = "これは普通の文章です。"
        assert mask_text(text, mode="pigpen") == text


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


class TestMaskTextPigpen:
    def test_email_wrapped_in_brackets(self):
        result = mask_text("user@example.com", mode="pigpen")
        assert "【" in result and "】" in result

    def test_output_contains_pigpen_symbols(self):
        result = mask_text("user@example.com", mode="pigpen")
        # extract content between 【 and 】
        m = re.search(r"【[^:]+:([^:]+):】", result)
        assert m is not None
        assert all(c in _PIGPEN_SYMBOLS for c in m.group(1))

    def test_category_label_in_output(self):
        result = mask_text("user@example.com", mode="pigpen")
        assert "メール" in result


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


# ── unmask_text ────────────────────────────────────────────────

class TestUnmaskTextEmpty:
    def test_empty_string(self):
        assert unmask_text("") == ""


class TestUnmaskTextNoMarkers:
    def test_plain_text_unchanged(self):
        text = "マスキングなしのテキスト"
        assert unmask_text(text) == text

    def test_partial_bracket_unchanged(self):
        text = "【incomplete"
        assert unmask_text(text) == text


class TestUnmaskTextRoundtrip:
    def test_pigpen_roundtrip_email(self):
        original = "user@example.com"
        masked = mask_text(original, mode="pigpen")
        restored = unmask_text(masked)
        assert restored == original

    def test_pigpen_roundtrip_japanese(self):
        original = "090-1234-5678"
        masked = mask_text(original, mode="pigpen")
        restored = unmask_text(masked)
        assert restored == original

    def test_pigpen_roundtrip_preserves_surrounding_text(self):
        original = "連絡先: user@example.com までご連絡ください。"
        masked = mask_text(original, mode="pigpen")
        restored = unmask_text(masked)
        assert restored == original

    def test_multiple_tokens_roundtrip(self):
        original = "email: a@x.com / tel: 090-1234-5678"
        masked = mask_text(original, mode="pigpen")
        restored = unmask_text(masked)
        assert restored == original


class TestUnmaskTextInvalidToken:
    def test_invalid_pigpen_token_kept_as_is(self):
        # 不正なシンボルが含まれていたらそのまま返す
        text = "【メール:INVALID:】"
        result = unmask_text(text)
        assert result == text
