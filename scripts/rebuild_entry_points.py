"""
Python runtime を別の PC / 別フォルダに移動した後、
Scripts\\ 配下の entry point (.exe) を現在のパスで再構築する。

使い方:
  python scripts/rebuild_entry_points.py          # PyPI からインストール
  python scripts/rebuild_entry_points.py --wheel  # 同梱 wheel から（オフライン）

同梱 wheel の置き場所:
  <runtime_root>/wheels/pymasking-*.whl
  または
  <このスクリプトと同じフォルダ>/pymasking-*.whl
"""

import argparse
import subprocess
import sys
from pathlib import Path


PACKAGE_NAME = "pymasking"

# wheel を探す候補ディレクトリ（優先順）
_WHEEL_SEARCH_DIRS = [
    Path(sys.executable).parent.parent / "wheels",   # runtime_root/wheels/
    Path(sys.executable).parent / "wheels",          # Scripts/wheels/
    Path(__file__).parent,                            # scripts/ (このスクリプトと同じ場所)
    Path(__file__).parent.parent,                    # repo root
]


def find_wheel() -> Path | None:
    """同梱の wheel ファイルを探す。複数あれば最新バージョンを返す。"""
    for d in _WHEEL_SEARCH_DIRS:
        found = sorted(d.glob(f"{PACKAGE_NAME}-*.whl"))
        if found:
            return found[-1]
    return None


def build_wheel() -> Path:
    """カレントディレクトリの pyproject.toml からその場で wheel をビルドする。"""
    repo_root = Path(__file__).parent.parent
    out_dir = repo_root / "wheels"
    out_dir.mkdir(exist_ok=True)
    print("wheel をビルドします ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(out_dir), str(repo_root)],
        check=True,
    )
    wheels = sorted(out_dir.glob(f"{PACKAGE_NAME}-*.whl"))
    if not wheels:
        raise RuntimeError("wheel のビルドに失敗しました")
    return wheels[-1]


def reinstall(source: str) -> None:
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--force-reinstall", "--no-deps",
        source,
    ]
    print(f"実行: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="entry point を現在の Python パスで再構築する",
    )
    parser.add_argument(
        "--wheel", action="store_true",
        help="同梱の .whl からオフラインで再インストール（見つからなければ自動ビルド）",
    )
    parser.add_argument(
        "--wheel-path", metavar="PATH", default="",
        help="使用する .whl ファイルを直接指定",
    )
    args = parser.parse_args()

    print(f"Python : {sys.executable}")
    print(f"Scripts: {Path(sys.executable).parent}\n")

    if args.wheel_path:
        whl = Path(args.wheel_path)
        if not whl.exists():
            print(f"Error: 指定した wheel が見つかりません: {whl}", file=sys.stderr)
            sys.exit(1)
        print(f"wheel  : {whl}")
        reinstall(str(whl))

    elif args.wheel:
        whl = find_wheel()
        if whl is None:
            print("同梱 wheel が見つかりません。その場でビルドします ...")
            whl = build_wheel()
        print(f"wheel  : {whl}")
        reinstall(str(whl))

    else:
        print(f"PyPI から {PACKAGE_NAME} を再インストールします ...")
        reinstall(PACKAGE_NAME)

    scripts_dir = Path(sys.executable).parent
    print(f"\n完了。{scripts_dir} の entry point が再作成されました。")


if __name__ == "__main__":
    main()
