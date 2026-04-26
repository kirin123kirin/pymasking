"""CLI エントリーポイント。

使用例:
  masking                           (Web UI 起動)
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
    click.echo("=" * 60)
    click.echo("【注意】画像・PDF の OCR マスキングには Tesseract OCR バイナリが別途必要です。")
    click.echo("")
    click.echo("  インストール手順（Windows）:")
    click.echo("  1. 以下の URL から installer をダウンロード")
    click.echo("     https://github.com/UB-Mannheim/tesseract/wiki")
    click.echo("  2. インストール時に「Additional language data」で")
    click.echo("     「Japanese (jpn)」にチェックを入れる")
    click.echo("  3. インストール先（例: C:\\Program Files\\Tesseract-OCR）を")
    click.echo("     システムの PATH 環境変数に追加する")
    click.echo("=" * 60)
    click.echo("")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    cli()
