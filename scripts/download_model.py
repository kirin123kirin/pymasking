"""インストール済み ja_ginza モデルをリポジトリ内の data/models/ja_ginza/ へコピーする。

spacy.load() は使わない。
設定バリデーション（confection の split_mode=None 問題）を完全に回避するため、
importlib でパッケージのパスを直接取得する。
"""

import importlib
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEST = REPO_ROOT / "data" / "models" / "ja_ginza"


def _install_ginza() -> None:
    print("ja-ginza / spacy をインストール中...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "ja-ginza", "spacy"],
        check=True,
    )


def _find_ginza_path() -> Path:
    """spacy.load() を経由せず ja_ginza パッケージのディレクトリを返す。"""
    spec = importlib.util.find_spec("ja_ginza")
    if spec is None or spec.origin is None:
        raise RuntimeError("ja_ginza が見つかりません。")
    return Path(spec.origin).parent


def main() -> None:
    if DEST.exists() and (DEST / "meta.json").exists():
        print(f"モデルは既に存在します: {DEST}")
        print("再コピーする場合は data/models/ja_ginza/ を削除してから再実行してください。")
        return

    print("ja_ginza モデルのパスを取得中...")
    try:
        src = _find_ginza_path()
    except RuntimeError:
        _install_ginza()
        importlib.invalidate_caches()
        src = _find_ginza_path()

    print(f"コピー元: {src}")
    print(f"コピー先: {DEST}")

    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists():
        shutil.rmtree(DEST)
    try:
        shutil.copytree(str(src), str(DEST))
    except Exception as e:
        print(f"[エラー] モデルのコピーに失敗しました: {e}")
        sys.exit(1)
    print("完了。")
    print(f"\n環境変数 GINZA_MODEL_PATH={DEST}")


if __name__ == "__main__":
    main()
