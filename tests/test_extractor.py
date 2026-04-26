"""境界値テスト: pymasking.core.extractor (make_output_path)"""
import pytest
from pathlib import Path
from pymasking.core.extractor import make_output_path


# ── make_output_path ───────────────────────────────────────────

class TestMakeOutputPathNormal:
    def test_simple_txt(self):
        p = Path("/tmp/report.txt")
        assert make_output_path(p) == Path("/tmp/report_変換後.txt")

    def test_docx(self):
        p = Path("/tmp/doc.docx")
        assert make_output_path(p) == Path("/tmp/doc_変換後.docx")

    def test_nested_directory(self):
        p = Path("/a/b/c/file.csv")
        result = make_output_path(p)
        assert result == Path("/a/b/c/file_変換後.csv")
        assert result.parent == Path("/a/b/c")


class TestMakeOutputPathEdgeCases:
    def test_no_extension(self):
        p = Path("/tmp/noext")
        result = make_output_path(p)
        assert result == Path("/tmp/noext_変換後")

    def test_hidden_file(self):
        # .hidden → stem=".hidden", suffix=""
        p = Path("/tmp/.hidden")
        result = make_output_path(p)
        assert result == Path("/tmp/.hidden_変換後")

    def test_double_extension_tar_gz(self):
        # Path("archive.tar.gz") → stem="archive.tar", suffix=".gz"
        p = Path("/tmp/archive.tar.gz")
        result = make_output_path(p)
        assert result == Path("/tmp/archive.tar_変換後.gz")

    def test_filename_only_no_parent(self):
        p = Path("report.txt")
        result = make_output_path(p)
        assert result.name == "report_変換後.txt"

    def test_stem_with_dots(self):
        p = Path("/tmp/v1.2.3.txt")
        result = make_output_path(p)
        assert result == Path("/tmp/v1.2.3_変換後.txt")

