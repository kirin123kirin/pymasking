"""
distlib を使って entry point だけを現在の python.exe パスで再構築する。

pip install も wheel も不要。
Python runtime を別の PC / 別フォルダに移動した後に実行してください。

使い方:
  python scripts/rebuild_entry_points.py
  python scripts/rebuild_entry_points.py --package some_other_package
"""

import argparse
import configparser
import sys
from pathlib import Path


def rebuild(package: str) -> None:
    from distlib.database import DistributionPath
    from distlib.scripts import ScriptMaker

    dp = DistributionPath()
    dist = dp.get_distribution(package)
    if dist is None:
        print(f"Error: '{package}' がインストールされていません", file=sys.stderr)
        sys.exit(1)

    ep_txt = Path(dist.path) / "entry_points.txt"
    if not ep_txt.exists():
        print(f"entry_points.txt が見つかりません: {ep_txt}", file=sys.stderr)
        sys.exit(1)

    cp = configparser.ConfigParser()
    cp.read_string(ep_txt.read_text(encoding="utf-8"))

    specs = []
    for section in ("console_scripts", "gui_scripts"):
        if cp.has_section(section):
            for name, target in cp.items(section):
                specs.append(f"{name} = {target}")

    if not specs:
        print("再構築する entry point がありません。")
        return

    scripts_dir = Path(sys.executable).parent
    maker = ScriptMaker(None, str(scripts_dir))
    maker.executable = sys.executable
    maker.clobber = True

    print(f"Python  : {sys.executable}")
    print(f"Scripts : {scripts_dir}")
    print()

    made = maker.make_multiple(specs)
    for path in made:
        print(f"  再作成: {path}")

    print(f"\n完了。{len(made)} 個の entry point を再構築しました。")


def main() -> None:
    parser = argparse.ArgumentParser(description="entry point を現在の Python パスで再構築する")
    parser.add_argument("--package", default="pymasking", help="対象パッケージ名（デフォルト: pymasking）")
    args = parser.parse_args()
    rebuild(args.package)


if __name__ == "__main__":
    main()
