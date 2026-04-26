"""CLI エントリーポイント。

使用例:
  masking                           (Web UI 起動)
  masking-download                  (OCR モデル事前ダウンロード)
  masking-shortcut                  (デスクトップにショートカット作成)
  python -m pymasking.cli.main mask report.docx
  python -m pymasking.cli.main mask report.docx --mode unique
"""

import click
from pathlib import Path


@click.group()
def cli():
    """pymasking: 個人情報マスキングツール"""


# ── mask コマンド ──────────────────────────────────────────────

@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--mode", "-m",
    type=click.Choice(["blackout", "unique"]),
    default="blackout",
    show_default=True,
    help="マスキング方式（画像・PDF は常に視覚的塗りつぶし）",
)
def mask(file, mode):
    """FILE のセンシティブ情報をマスキングする。"""
    from pymasking.core.extractor import process_file
    path = Path(file)
    click.echo(f"処理中: {path}")
    out = process_file(path, mode)
    click.echo(f"完了 → {out}")


# ── web コマンド ───────────────────────────────────────────────

@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=59631, show_default=True)
@click.option("--debug", is_flag=True, hidden=True)
def web(host, port, debug):
    """Web インターフェースを起動する。"""
    import threading
    import webbrowser
    from pymasking.web.app import create_app
    app = create_app()
    url = f"http://{host}:{port}"
    click.echo(f"Web UI: {url}")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=debug)


# ── masking コマンド（PyPI エントリーポイント） ────────────────

def launch() -> None:
    """pip install pymasking 後の `masking` コマンド。
    ポート 55963 で Web UI を起動し、ブラウザを自動で開く。
    """
    import threading
    import webbrowser
    from pymasking.web.app import create_app

    host, port = "127.0.0.1", 55963
    app = create_app()
    url = f"http://{host}:{port}"
    click.echo(f"pymasking  →  {url}")
    click.echo("終了するには Ctrl+C を押してください。")
    click.echo("")
    click.echo("ヒント: 画像マスキングを初めて使う場合は先に `masking-download` を実行してください。")
    click.echo("")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)


# ── masking-download コマンド（PyPI エントリーポイント） ─────────

_OCR_MODELS = [
    {
        "label": "テキスト検出モデル  craft_mlt_25k.pth",
        "filename": "craft_mlt_25k.pth",
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip",
        "md5sum": "2f8227d2def4037cdb3b34389dcf9ec1",
    },
    {
        "label": "日本語認識モデル   japanese_g2.pth",
        "filename": "japanese_g2.pth",
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/japanese_g2.zip",
        "md5sum": "bad5146990ccb1272cb0908440fbe15e",
    },
    {
        "label": "英語認識モデル     english_g2.pth",
        "filename": "english_g2.pth",
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip",
        "md5sum": "5864788e1821be9e454ec108d61b887d",
    },
]


def _download_file(url: str, dest: Path, verify_ssl: bool) -> None:
    """URL からファイルをダウンロードして dest に保存する。zip は自動展開する。"""
    import io
    import zipfile
    import requests

    resp = requests.get(url, stream=True, timeout=120, verify=verify_ssl)
    resp.raise_for_status()
    data = resp.content

    if url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name.endswith(".pth"):
                    dest.write_bytes(zf.read(name))
                    return
        raise RuntimeError(f"zip 内に .pth ファイルが見つかりません: {url}")
    else:
        dest.write_bytes(data)


def download_models(url: str = "", verify_ssl: bool = True) -> None:
    """pip install pymasking 後の `masking-download` コマンド。
    EasyOCR の OCR モデルを pymasking/data/model/ に事前ダウンロードする。

    --url を指定すると GitHub の代わりに社内サーバー（SharePoint 等）からDLする。
    """
    from pymasking.core.extractor.image import _MODEL_DIR

    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        click.echo("  ⚠ SSL 検証を無効にしています（--no-verify-ssl）", err=True)

    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    click.echo(f"モデル保存先: {_MODEL_DIR}")
    if url:
        click.echo(f"ダウンロード元: {url}")
    click.echo("")

    all_exist = True
    for m in _OCR_MODELS:
        dest = _MODEL_DIR / m["filename"]
        if dest.exists():
            click.echo(f"  スキップ（既存）: {m['label']}")
            continue

        all_exist = False
        click.echo(f"  ダウンロード中: {m['label']}", nl=False)
        try:
            src_url = (url.rstrip("/") + "/" + m["filename"]) if url else m["url"]
            _download_file(src_url, dest, verify_ssl=verify_ssl)
            click.echo("  完了")
        except Exception as e:
            click.echo(f"  失敗: {e}", err=True)
            raise SystemExit(1)

    click.echo("")
    if all_exist:
        click.echo("すべてのモデルが既にダウンロード済みです。")
    else:
        click.echo("ダウンロード完了。次回以降はオフラインで動作します。")


# click エントリーポイント（masking-download コマンド）
@click.command()
@click.option(
    "--url", "-u",
    default="",
    metavar="BASE_URL",
    help="社内サーバー（SharePoint 等）のフォルダ URL。省略時は GitHub からDL。",
)
@click.option(
    "--no-verify-ssl",
    is_flag=True,
    default=False,
    help="SSL 証明書の検証を無効にする（社内プロキシ環境用）。",
)
def download_models_cli(url: str, no_verify_ssl: bool) -> None:
    """EasyOCR OCR モデルを事前ダウンロードする。"""
    download_models(url=url, verify_ssl=not no_verify_ssl)


def _download_entry() -> None:
    """masking-download エントリーポイント。"""
    download_models_cli(standalone_mode=True)


# ── masking-shortcut コマンド（PyPI エントリーポイント） ──────────

def create_shortcut() -> None:
    """デスクトップに masking のショートカットを作成する（Windows 専用）。"""
    import sys

    if sys.platform != "win32":
        click.echo("このコマンドは Windows 専用です。", err=True)
        raise SystemExit(1)

    import shutil
    from pathlib import Path

    try:
        from win32com.client import Dispatch
    except ImportError:
        click.echo(
            "pywin32 が必要です: pip install pywin32",
            err=True,
        )
        raise SystemExit(1)

    # masking コマンドの実行ファイルパスを特定
    masking_exe = shutil.which("masking")
    if masking_exe is None:
        click.echo("masking コマンドが見つかりません。pip install pymasking を確認してください。", err=True)
        raise SystemExit(1)

    # アイコンパス
    icon_path = Path(__file__).parent.parent / "web" / "static" / "favicon.ico"

    # デスクトップパス
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        # 日本語 Windows 環境
        desktop = Path.home() / "デスクトップ"
    if not desktop.exists():
        desktop = Path.home()

    shortcut_path = desktop / "masking.lnk"

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = masking_exe
    shortcut.WorkingDirectory = str(Path.home())
    shortcut.Description = "pymasking — 個人情報マスキングツール"
    if icon_path.exists():
        shortcut.IconLocation = str(icon_path)
    shortcut.Save()

    click.echo(f"ショートカットを作成しました: {shortcut_path}")


if __name__ == "__main__":
    cli()
