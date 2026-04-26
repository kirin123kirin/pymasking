"""Playwright でデモ GIF を自動生成するスクリプト。"""

import io
import threading
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
OUT_DIR = Path(__file__).parent.parent / "doc"
URL = "http://127.0.0.1:55963"


def start_server():
    from pymasking.web.app import create_app
    app = create_app()
    t = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=55963, debug=False, use_reloader=False),
        daemon=True,
    )
    t.start()
    time.sleep(2)


def shot(page) -> Image.Image:
    return Image.open(io.BytesIO(page.screenshot()))


def save_gif(frames: list, path: Path, durations: list):
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )
    print(f"saved: {path}")


def make_text_gif(page):
    frames, durations = [], []

    def add(ms=800):
        frames.append(shot(page))
        durations.append(ms)

    page.goto(URL)
    page.wait_for_load_state("networkidle")
    add(1200)

    # テキストタブが既定で表示されている
    textarea = page.locator("textarea").first
    textarea.click()
    add(600)

    sample = (
        "山田太郎様\n"
        "お世話になっております。\n"
        "ご連絡先: taro.yamada@example.com\n"
        "電話: 090-1234-5678\n"
        "ご請求額: 150,000円"
    )
    for ch in sample:
        textarea.type(ch, delay=18)
    add(1000)

    # マスキング実行
    page.locator("button", has_text="マスキング実行").first.click()
    page.wait_for_timeout(1200)
    add(2000)

    # 結果をコピーボタンが見えることを確認
    add(1500)

    save_gif(frames, OUT_DIR / "demo_text.gif", durations)


def make_file_gif(page):
    import tempfile, os
    frames, durations = [], []

    def add(ms=800):
        frames.append(shot(page))
        durations.append(ms)

    page.goto(URL)
    page.wait_for_load_state("networkidle")

    # ファイルタブをクリック
    page.locator(".tab", has_text="ファイル").click()
    page.wait_for_timeout(400)
    add(1200)

    # テスト用 txt ファイルを作成してアップロード
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
        f.write("山田太郎 taro@example.com 090-1234-5678\n150,000円")
        tmp_path = f.name

    try:
        page.locator("input[type=file]").set_input_files(tmp_path)
        page.wait_for_timeout(600)
        add(1200)

        # マスキング実行ボタンが有効になるまで待機してクリック
        page.locator("#file-mask-btn").wait_for(state="visible")
        page.wait_for_timeout(300)
        add(800)
        page.locator("#file-mask-btn").click()
        page.wait_for_timeout(400)
        add(1000)

        # 実行中の状態
        page.wait_for_timeout(1500)
        add(1200)

        # ダウンロードボタンが現れた状態
        page.wait_for_timeout(1500)
        add(2000)
    finally:
        os.unlink(tmp_path)

    save_gif(frames, OUT_DIR / "demo_file.gif", durations)


def main():
    start_server()
    OUT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROMIUM,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(viewport={"width": 1024, "height": 768})
        page = context.new_page()

        make_text_gif(page)
        make_file_gif(page)

        browser.close()


if __name__ == "__main__":
    main()
