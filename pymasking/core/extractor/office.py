"""Office ドキュメント（docx / xlsx / pptx）のマスキング処理。"""

import shutil
from pathlib import Path

from ..masker import mask_text, MaskMode
from . import make_output_path


def _mask_paragraph(para, mode: MaskMode) -> None:
    raw = para.text
    if not raw.strip():
        return
    masked = mask_text(raw, mode)
    if masked == raw:
        return
    for run in para.runs:
        run.text = ""
    if para.runs:
        para.runs[0].text = masked
    else:
        para.add_run(masked)


def process_docx(src: Path, mode: MaskMode) -> Path:
    from docx import Document

    out = make_output_path(src)
    shutil.copy2(src, out)
    doc = Document(out)

    for para in doc.paragraphs:
        _mask_paragraph(para, mode)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _mask_paragraph(para, mode)

    doc.save(out)
    return out


def process_xlsx(src: Path, mode: MaskMode) -> Path:
    from openpyxl import load_workbook

    out = make_output_path(src)
    shutil.copy2(src, out)
    wb = load_workbook(out)

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    cell.value = mask_text(cell.value, mode)

    wb.save(out)
    return out


def process_pptx(src: Path, mode: MaskMode) -> Path:
    from pptx import Presentation

    out = make_output_path(src)
    shutil.copy2(src, out)
    prs = Presentation(out)

    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if run.text:
                        run.text = mask_text(run.text, mode)

    prs.save(out)
    return out


def process_office(src: Path, mode: MaskMode) -> Path:
    ext = src.suffix.lower()
    if ext == ".docx":
        return process_docx(src, mode)
    elif ext == ".xlsx":
        return process_xlsx(src, mode)
    elif ext == ".pptx":
        return process_pptx(src, mode)
    raise ValueError(f"未対応の Office 形式: {ext}")
