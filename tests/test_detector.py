"""境界値テスト: pymasking.core.detector"""
import pytest
from pymasking.core.detector import (
    Detection,
    _valid_date,
    resolve_overlaps,
    detect_emails,
    detect_phones,
    detect_amounts,
    detect_dates,
    detect_all,
)


# ── _valid_date ────────────────────────────────────────────────

class TestValidDateBoundaries:
    def test_year_lower_bound(self):
        assert _valid_date(1900, 1, 1) is True

    def test_year_below_lower_bound(self):
        assert _valid_date(1899, 12, 31) is False

    def test_year_upper_bound(self):
        assert _valid_date(2100, 12, 31) is True

    def test_year_above_upper_bound(self):
        assert _valid_date(2101, 1, 1) is False

    def test_leap_day_valid(self):
        assert _valid_date(2024, 2, 29) is True

    def test_leap_day_invalid_non_leap(self):
        assert _valid_date(2023, 2, 29) is False

    def test_feb_28_always_valid(self):
        assert _valid_date(2023, 2, 28) is True

    def test_month_lower_bound(self):
        assert _valid_date(2000, 1, 1) is True

    def test_month_zero_invalid(self):
        assert _valid_date(2000, 0, 1) is False

    def test_month_upper_bound(self):
        assert _valid_date(2000, 12, 31) is True

    def test_month_above_upper_bound(self):
        assert _valid_date(2000, 13, 1) is False

    def test_day_zero_invalid(self):
        assert _valid_date(2000, 1, 0) is False

    def test_day_31_jan_valid(self):
        assert _valid_date(2000, 1, 31) is True

    def test_day_32_invalid(self):
        assert _valid_date(2000, 1, 32) is False

    def test_april_30_valid(self):
        assert _valid_date(2000, 4, 30) is True

    def test_april_31_invalid(self):
        assert _valid_date(2000, 4, 31) is False


# ── resolve_overlaps ───────────────────────────────────────────

def _det(start, end, cat="テスト", text="x"):
    return Detection(start, end, cat, text)


class TestResolveOverlapsEmpty:
    def test_empty_list(self):
        assert resolve_overlaps([]) == []


class TestResolveOverlapsNoOverlap:
    def test_adjacent(self):
        a = _det(0, 3)
        b = _det(3, 6)
        result = resolve_overlaps([a, b])
        assert len(result) == 2

    def test_gap(self):
        a = _det(0, 2)
        b = _det(5, 8)
        result = resolve_overlaps([a, b])
        assert len(result) == 2


class TestResolveOverlapsWithOverlap:
    def test_exact_overlap_keeps_first(self):
        a = _det(0, 5)
        b = _det(0, 5)
        result = resolve_overlaps([a, b])
        assert len(result) == 1
        assert result[0].start == 0 and result[0].end == 5

    def test_contained_shorter_discarded(self):
        outer = _det(0, 10)
        inner = _det(2, 6)
        result = resolve_overlaps([outer, inner])
        assert len(result) == 1
        assert result[0].end == 10

    def test_partial_overlap_keeps_earlier(self):
        a = _det(0, 5)
        b = _det(3, 8)
        result = resolve_overlaps([a, b])
        assert len(result) == 1
        assert result[0].start == 0

    def test_three_detections_middle_overlaps(self):
        a = _det(0, 4)
        b = _det(3, 7)
        c = _det(8, 12)
        result = resolve_overlaps([a, b, c])
        assert len(result) == 2
        assert result[0].start == 0
        assert result[1].start == 8

    def test_longer_wins_when_same_start(self):
        short = _det(0, 3)
        long_ = _det(0, 8)
        result = resolve_overlaps([short, long_])
        assert len(result) == 1
        assert result[0].end == 8


# ── detect_emails ──────────────────────────────────────────────

class TestDetectEmailsEmpty:
    def test_empty_string(self):
        assert detect_emails("") == []


class TestDetectEmailsValid:
    def test_simple_email(self):
        results = detect_emails("tanaka@example.com")
        assert len(results) == 1
        assert results[0].text == "tanaka@example.com"

    def test_minimal_email(self):
        results = detect_emails("a@b.co")
        assert len(results) == 1

    def test_plus_in_local(self):
        results = detect_emails("user+tag@example.com")
        assert len(results) == 1

    def test_email_in_sentence(self):
        results = detect_emails("連絡先: info@company.co.jp をご利用ください。")
        assert len(results) == 1
        assert "info@company.co.jp" in results[0].text

    def test_multiple_emails(self):
        results = detect_emails("a@x.com b@y.org")
        assert len(results) == 2

    def test_no_at_sign(self):
        assert detect_emails("notanemail.com") == []

    def test_no_domain(self):
        assert detect_emails("user@") == []

    def test_category(self):
        results = detect_emails("a@b.com")
        assert results[0].category == "メール"


# ── detect_phones ──────────────────────────────────────────────

class TestDetectPhonesEmpty:
    def test_empty_string(self):
        assert detect_phones("") == []


class TestDetectPhonesValid:
    def test_mobile_hyphen(self):
        results = detect_phones("090-1234-5678")
        assert len(results) >= 1

    def test_mobile_no_hyphen(self):
        results = detect_phones("09012345678")
        assert len(results) >= 1

    def test_toll_free(self):
        results = detect_phones("0120-123-456")
        assert len(results) >= 1

    def test_international(self):
        results = detect_phones("+81-90-1234-5678")
        assert len(results) >= 1

    def test_no_phone_in_plain_text(self):
        assert detect_phones("これは普通の文章です。") == []

    def test_category(self):
        results = detect_phones("090-1234-5678")
        assert all(r.category == "電話" for r in results)


# ── detect_amounts ─────────────────────────────────────────────

class TestDetectAmountsEmpty:
    def test_empty_string(self):
        assert detect_amounts("") == []


class TestDetectAmountsValid:
    def test_simple_yen(self):
        results = detect_amounts("5000円")
        assert len(results) == 1
        assert results[0].text == "5000円"

    def test_comma_separated(self):
        results = detect_amounts("1,000,000円")
        assert len(results) == 1

    def test_oku(self):
        # regex requires 2+ digits before 億: "30億円" matches \d{2,}(?:億)?円
        results = detect_amounts("30億円")
        assert len(results) == 1

    def test_decimal(self):
        results = detect_amounts("1234.56円")
        assert len(results) == 1

    def test_single_digit_not_detected(self):
        # 1桁のみは検出しない（2桁以上 or カンマ付き）
        results = detect_amounts("5円")
        assert len(results) == 0

    def test_category(self):
        results = detect_amounts("10000円")
        assert results[0].category == "金額"


# ── detect_dates ───────────────────────────────────────────────

class TestDetectDatesEmpty:
    def test_empty_string(self):
        assert detect_dates("") == []


class TestDetectDatesValid:
    def test_iso_date(self):
        results = detect_dates("2024-01-15")
        assert len(results) == 1
        assert results[0].category == "日付"

    def test_slash_date(self):
        results = detect_dates("2024/1/15")
        assert len(results) == 1

    def test_japanese_date(self):
        # detect_dates may return both the full date and the 月日 sub-pattern;
        # verify at least the full date is detected with the right category
        results = detect_dates("2024年1月15日")
        assert len(results) >= 1
        texts = [r.text for r in results]
        assert "2024年1月15日" in texts

    def test_reiwa(self):
        results = detect_dates("令和6年1月15日")
        assert len(results) >= 1
        texts = [r.text for r in results]
        assert "令和6年1月15日" in texts

    def test_invalid_date_rejected(self):
        # 2月30日は実在しない
        results = detect_dates("2024-02-30")
        assert len(results) == 0

    def test_invalid_month_rejected(self):
        results = detect_dates("2024-13-01")
        assert len(results) == 0

    def test_year_boundary_1900(self):
        results = detect_dates("1900-01-01")
        assert len(results) == 1

    def test_year_boundary_2100(self):
        results = detect_dates("2100-12-31")
        assert len(results) == 1

    def test_year_below_boundary(self):
        results = detect_dates("1899-12-31")
        assert len(results) == 0

    def test_no_date_in_text(self):
        assert detect_dates("これは普通の文章です。") == []


# ── detect_all ─────────────────────────────────────────────────

class TestDetectAll:
    def test_empty_string(self):
        results = detect_all("")
        assert results == []

    def test_no_sensitive_info(self):
        results = detect_all("これは普通の文章です。")
        assert isinstance(results, list)

    def test_email_detected(self):
        results = detect_all("連絡先: user@example.com")
        cats = {r.category for r in results}
        assert "メール" in cats

    def test_phone_detected(self):
        results = detect_all("電話: 090-1234-5678")
        cats = {r.category for r in results}
        assert "電話" in cats

    def test_categories_filter(self):
        text = "email@example.com / 090-1234-5678"
        results = detect_all(text, categories={"メール"})
        assert all(r.category == "メール" for r in results)
        assert any(r.category == "メール" for r in results)

    def test_categories_filter_excludes(self):
        text = "090-1234-5678"
        results = detect_all(text, categories={"メール"})
        assert results == []

    def test_categories_none_returns_all(self):
        text = "email@example.com / 090-1234-5678"
        all_results = detect_all(text, categories=None)
        filtered = detect_all(text, categories={"メール"})
        assert len(all_results) >= len(filtered)
