"""CLI エントリーポイント。

使用例:
  mask.bat report.docx
  mask.bat report.docx --mode pigpen
  mask.bat                          (クリップボードから入力)
  unmask.bat report_masked.txt
  unmask.bat                        (クリップボードから入力)
"""

import click
from pathlib import Path


@click.group()
def cli():
    """pymasking: 個人情報マスキングツール"""


# ── mask コマンド ──────────────────────────────────────────────

@cli.command()
@click.argument("file", required=False, type=click.Path(exists=True))
@click.option(
    "--mode", "-m",
    type=click.Choice(["blackout", "unique", "pigpen"]),
    default="blackout",
    show_default=True,
    help="マスキング方式（画像・PDF は常に視覚的塗りつぶし）",
)
@click.option("--clipboard", "-c", is_flag=True, help="クリップボードから入力")
def mask(file, mode, clipboard):
    """FILE または クリップボードのセンシティブ情報をマスキングする。FILE 省略時はクリップボードを使用。"""
    if clipboard or file is None:
        _mask_clipboard(mode)
    else:
        _mask_file(Path(file), mode)


def _mask_file(path: Path, mode: str) -> None:
    from pymasking.core.extractor import process_file
    click.echo(f"処理中: {path}")
    out = process_file(path, mode)
    click.echo(f"完了 → {out}")


def _mask_clipboard(mode: str) -> None:
    from pymasking.core.extractor.clipboard import (
        get_clipboard, open_with_default_app,
        save_to_temp, save_image_to_temp,
    )
    from pymasking.core.extractor import process_file

    kind, content = get_clipboard()

    if kind == "text":
        from pymasking.core.masker import mask_text
        masked = mask_text(content, mode)
        out = save_to_temp(masked, suffix=".txt")
        click.echo(f"テキストをマスキングしました → {out}")
        open_with_default_app(out)

    elif kind == "image":
        from pymasking.core.extractor.image import process_image_data
        masked_img = process_image_data(content, mode)
        out = save_image_to_temp(masked_img, suffix=".png")
        click.echo(f"画像をマスキングしました → {out}")
        open_with_default_app(out)

    elif kind == "file":
        click.echo(f"クリップボードのファイル: {content}")
        out = process_file(content, mode)
        click.echo(f"完了 → {out}")
        open_with_default_app(out)

    else:
        raise click.ClickException("クリップボードにサポートされたデータがありません。")


# ── unmask コマンド ────────────────────────────────────────────

@cli.command()
@click.argument("file", required=False, type=click.Path(exists=True))
def unmask(file):
    """ピッグペン暗号化されたテキストファイルを復号する。FILE 省略時はクリップボードを使用。"""
    from pymasking.core.masker import unmask_text

    if file is None:
        from pymasking.core.extractor.clipboard import get_clipboard, save_to_temp, open_with_default_app
        kind, content = get_clipboard()
        if kind != "text":
            raise click.ClickException("クリップボードにテキストがありません。")
        restored = unmask_text(content)
        out = save_to_temp(restored, suffix=".txt")
        click.echo(f"復号完了 → {out}")
        open_with_default_app(out)
        return

    path = Path(file)
    text = path.read_text(encoding="utf-8", errors="replace")
    restored = unmask_text(text)
    out = path.parent / f"{path.stem}_unmasked{path.suffix}"
    out.write_text(restored, encoding="utf-8")
    click.echo(f"復号完了 → {out}")


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
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    cli()
