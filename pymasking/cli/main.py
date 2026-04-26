"""CLI エントリーポイント。

使用例:
  masking                           (Web UI 起動)
  masking-download                  (OCR モデル事前ダウンロード)
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


def download_models() -> None:
    """pip install pymasking 後の `masking-download` コマンド。
    EasyOCR の OCR モデルを pymasking/data/model/ に事前ダウンロードする。
    """
    from pymasking.core.extractor.image import _MODEL_DIR
    from easyocr.utils import download_and_unzip

    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    click.echo(f"モデル保存先: {_MODEL_DIR}")
    click.echo("")

    all_exist = True
    for m in _OCR_MODELS:
        dest = _MODEL_DIR / m["filename"]
        if dest.exists():
            click.echo(f"  スキップ（既存）: {m['label']}")
        else:
            all_exist = False
            click.echo(f"  ダウンロード中: {m['label']}")
            download_and_unzip(m["url"], m["filename"], str(_MODEL_DIR), verbose=False)
            click.echo(f"  完了")

    click.echo("")
    if all_exist:
        click.echo("すべてのモデルが既にダウンロード済みです。")
    else:
        click.echo("ダウンロード完了。次回以降はオフラインで動作します。")


if __name__ == "__main__":
    cli()
