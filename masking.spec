# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for masking.exe
Build: pyinstaller masking.spec
"""

from pathlib import Path

ROOT = Path(SPECPATH)
ICON = str(ROOT / "pymasking" / "web" / "static" / "favicon.ico")

a = Analysis(
    [str(ROOT / "pymasking" / "cli" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "pymasking" / "web" / "templates"), "pymasking/web/templates"),
        (str(ROOT / "pymasking" / "web" / "static"),    "pymasking/web/static"),
        (str(ROOT / "pymasking" / "data" / "dict"),     "pymasking/data/dict"),
    ],
    hiddenimports=[
        "pymasking.core.extractor.plaintext",
        "pymasking.core.extractor.office",
        "pymasking.core.extractor.image",
        "pymasking.core.extractor.pdf_handler",
        "pymasking.core.cipher.blackout",
        "pymasking.core.cipher.unique",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="masking",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=ICON,
)
