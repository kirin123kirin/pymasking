"""境界値テスト: pymasking.core.extractor (make_output_path)"""
import pytest
from pathlib import Path
from pymasking.core.extractor import make_output_path


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

