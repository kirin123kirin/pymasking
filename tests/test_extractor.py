"""境界値テスト: pymasking.core.extractor (make_output_path / unmask_file)"""
import pytest
from pathlib import Path
from pymasking.core.extractor import make_output_path, unmask_file


# ── make_output_path ───────────────────────────────────────────

class TestMakeOutputPathNormal:
    def test_simple_txt(self):
        p = Path("/tmp/report.txt")
        assert make_output_path(p) == Path("/tmp/report_masked.txt")

    def test_docx(self):
        p = Path("/tmp/doc.docx")
        assert make_output_path(p) == Path("/tmp/doc_masked.docx")

    def test_nested_directory(self):
        p = Path("/a/b/c/file.csv")
        result = make_output_path(p)
        assert result == Path("/a/b/c/file_masked.csv")
        assert result.parent == Path("/a/b/c")


class TestMakeOutputPathEdgeCases:
    def test_no_extension(self):
        p = Path("/tmp/noext")
        result = make_output_path(p)
        assert result == Path("/tmp/noext_masked")

    def test_hidden_file(self):
        # .hidden → stem=".hidden", suffix=""
        p = Path("/tmp/.hidden")
        result = make_output_path(p)
        assert result == Path("/tmp/.hidden_masked")

    def test_double_extension_tar_gz(self):
        # Path("archive.tar.gz") → stem="archive.tar", suffix=".gz"
        p = Path("/tmp/archive.tar.gz")
        result = make_output_path(p)
        assert result == Path("/tmp/archive.tar_masked.gz")

    def test_filename_only_no_parent(self):
        p = Path("report.txt")
        result = make_output_path(p)
        assert result.name == "report_masked.txt"

    def test_stem_with_dots(self):
        p = Path("/tmp/v1.2.3.txt")
        result = make_output_path(p)
        assert result == Path("/tmp/v1.2.3_masked.txt")


# ── unmask_file ────────────────────────────────────────────────

class TestUnmaskFileImageRejected:
    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png", ".bmp", ".pdf"])
    def test_image_pdf_raises(self, ext, tmp_path):
        f = tmp_path / f"file{ext}"
        f.touch()
        with pytest.raises(ValueError, match="画像・PDF"):
            unmask_file(f)


class TestUnmaskFilePlaintext:
    def test_plain_text_no_pigpen_unchanged(self, tmp_path):
        src = tmp_path / "plain.txt"
        src.write_text("マスキングなし", encoding="utf-8")
        out = unmask_file(src)
        assert out.exists()
        assert out.read_text(encoding="utf-8") == "マスキングなし"

    def test_output_path_has_unmasked_suffix(self, tmp_path):
        src = tmp_path / "data.txt"
        src.write_text("テキスト", encoding="utf-8")
        out = unmask_file(src)
        assert "_unmasked" in out.name

    def test_pigpen_roundtrip_via_file(self, tmp_path):
        from pymasking.core.masker import mask_text
        original = "user@example.com"
        masked = mask_text(original, mode="pigpen")
        src = tmp_path / "masked.txt"
        src.write_text(masked, encoding="utf-8")
        out = unmask_file(src)
        assert out.read_text(encoding="utf-8") == original

    def test_empty_file(self, tmp_path):
        src = tmp_path / "empty.txt"
        src.write_text("", encoding="utf-8")
        out = unmask_file(src)
        assert out.read_text(encoding="utf-8") == ""
