"""JMnedict から姓名データを取得して data/ に保存する。

出力ファイル:
  data/surnames.txt     - 姓（surname エントリ）
  data/given_names.txt  - 名（given / fem / masc エントリ）
  data/person_names.txt - 完全人名（person エントリ）
"""

import gzip
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

JMNEDICT_URL = "http://ftp.edrdg.org/pub/Nihongo/JMnedict.xml.gz"

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
XML_GZ = DATA_DIR / "JMnedict.xml.gz"

# EntityRuler に追加する名前種別
_SURNAME_TYPES = {"surname"}
_GIVEN_TYPES = {"given", "fem", "masc"}
_PERSON_TYPES = {"person"}


def download(url: str, dest: Path) -> None:
    print(f"ダウンロード中: {url}")

    def _progress(count, block_size, total_size):
        pct = count * block_size * 100 // total_size
        print(f"\r  {pct}%", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print(f"\r完了: {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")


def parse(xml_gz: Path) -> tuple[set[str], set[str], set[str]]:
    """JMnedict を iterparse で解析し (surnames, given_names, person_names) を返す。"""
    surnames: set[str] = set()
    given_names: set[str] = set()
    person_names: set[str] = set()

    print("解析中（数分かかる場合があります）...")

    with gzip.open(xml_gz, "rb") as f:
        count = 0
        for event, elem in ET.iterparse(f, events=("end",)):
            if elem.tag != "entry":
                continue

            kanji_forms = [ke.text for ke in elem.findall("k_ele/keb") if ke.text]
            name_types = {nt.text for nt in elem.findall(".//name_type") if nt.text}

            for kf in kanji_forms:
                if not kf or len(kf) < 2:   # 1文字エントリは誤検知リスク大のため除外
                    continue
                if name_types & _SURNAME_TYPES:
                    surnames.add(kf)
                if name_types & _GIVEN_TYPES:
                    given_names.add(kf)
                if name_types & _PERSON_TYPES:
                    person_names.add(kf)

            elem.clear()
            count += 1
            if count % 50_000 == 0:
                print(f"  {count:,} エントリ処理済み...")

    print(
        f"解析完了: 姓={len(surnames):,}件 / 名={len(given_names):,}件 / "
        f"完全人名={len(person_names):,}件"
    )
    return surnames, given_names, person_names


def save(surnames: set[str], given_names: set[str], person_names: set[str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)

    def _write(path: Path, data: set[str]) -> None:
        path.write_text("\n".join(sorted(data)), encoding="utf-8")
        print(f"  {path.name}: {len(data):,} 件")

    print("保存中...")
    _write(DATA_DIR / "surnames.txt", surnames)
    _write(DATA_DIR / "given_names.txt", given_names)
    _write(DATA_DIR / "person_names.txt", person_names)


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    if XML_GZ.exists():
        print(f"既存ファイルを使用: {XML_GZ}")
    else:
        download(JMNEDICT_URL, XML_GZ)

    surnames, given_names, person_names = parse(XML_GZ)
    save(surnames, given_names, person_names)
    print("\ndata/ ディレクトリへの保存完了。")


if __name__ == "__main__":
    main()
