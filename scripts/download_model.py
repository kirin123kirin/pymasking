"""インストール済み ja_ginza モデルをリポジトリ内の models/ja_ginza/ へコピーする。"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEST = REPO_ROOT / "models" / "ja_ginza"


def _install_ginza() -> None:
    print("ja-ginza / spacy をインストール中...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "ja-ginza", "spacy"],
        check=True,
    )


def _load_nlp():
    import spacy
    try:
        return spacy.load("ja_ginza")
    except OSError:
        _install_ginza()
        import importlib
        importlib.invalidate_caches()
        import spacy as spacy2
        return spacy2.load("ja_ginza")


def main() -> None:
    if DEST.exists() and (DEST / "meta.json").exists():
        print(f"モデルは既に存在します: {DEST}")
        print("再ダウンロードする場合は models/ja_ginza/ を削除してから再実行してください。")
        return

    print("ja_ginza モデルのパスを取得中...")
    nlp = _load_nlp()
    src = Path(nlp.path)
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
