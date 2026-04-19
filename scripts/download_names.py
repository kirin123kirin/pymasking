"""Download name data from JMnedict and save as Sudachi binary dict + gzip pickle."""

import gzip
import importlib.util
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

JMNEDICT_URL = "http://ftp.edrdg.org/pub/Nihongo/JMnedict.xml.gz"

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
XML_GZ = DATA_DIR / "JMnedict.xml.gz"

_SURNAME_TYPES = {"surname"}
_GIVEN_TYPES = {"given", "fem", "masc"}
_PERSON_TYPES = {"person"}

_JMNEDICT_ENTITIES: dict[str, str] = {
    "surname": "surname", "given": "given", "fem": "fem", "masc": "masc",
    "person": "person", "place": "place", "company": "company",
    "organization": "organization", "ok": "ok", "work": "work",
    "station": "station", "unclass": "unclass", "char": "char",
    "creat": "creat", "dei": "dei", "doc": "doc", "ev": "ev",
    "fict": "fict", "god": "god", "leg": "leg", "myth": "myth",
    "obj": "obj", "product": "product", "relig": "relig", "serv": "serv",
    "ship": "ship", "rr": "rr", "road": "road",
}


def _make_parser() -> ET.XMLParser:
    parser = ET.XMLParser()
    for k, v in _JMNEDICT_ENTITIES.items():
        parser.entity[k] = v
    return parser


def download(url: str, dest: Path) -> None:
    print(f"Downloading: {url}")

    def _progress(count, block_size, total_size):
        pct = count * block_size * 100 // total_size
        print(f"\r  {pct}%", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=_progress)
    print(f"\rDone: {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")


def parse(xml_gz: Path) -> tuple[set[str], set[str], set[str]]:
    """Parse JMnedict and return (surnames, given_names, person_names)."""
    surnames: set[str] = set()
    given_names: set[str] = set()
    person_names: set[str] = set()

    print("Parsing (may take a few minutes)...")

    with gzip.open(xml_gz, "rb") as f:
        count = 0
        for event, elem in ET.iterparse(f, events=("end",), parser=_make_parser()):
            if elem.tag != "entry":
                continue

            kanji_forms = [ke.text for ke in elem.findall("k_ele/keb") if ke.text]
            name_types = {x for nt in elem.findall(
                ".//name_type") if nt.text for x in nt.text.split(" ")}

            for kf in kanji_forms:
                if not kf or len(kf) < 2:
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
                print(f"  {count:,} entries processed...")

    print(
        f"Parse complete: surnames={len(surnames):,} / given={len(given_names):,} / "
        f"full_names={len(person_names):,}"
    )
    return surnames, given_names, person_names


def _find_system_dic() -> Path | None:
    """Find Sudachi system.dic from installed dictionary package."""
    for pkg in ("sudachidict_full", "sudachidict_core", "sudachidict_small"):
        try:
            spec = importlib.util.find_spec(pkg)
            if spec and spec.submodule_search_locations:
                for loc in spec.submodule_search_locations:
                    p = Path(loc) / "resources" / "system.dic"
                    if p.exists():
                        return p
        except Exception:
            pass
    return None


def _build_sudachi_dict(surnames: set[str], given_names: set[str], person_names: set[str]) -> None:
    """Build Sudachi binary user dictionary from name data."""
    system_dic = _find_system_dic()
    if not system_dic:
        print("  [WARNING] Sudachi system.dic not found. Skipping binary dict build.")
        return

    csv_path = DATA_DIR / "_names_user_tmp.csv"
    dic_path = DATA_DIR / "names_user.dic"
    rows: list[str] = []

    for name in sorted(person_names):
        s = name.replace(",", "")
        if not s:
            continue
        rows.append(f"{s},0,0,3000,{s},{s},{s},{s},名詞,固有名詞,人名,一般,,,,,,")
    for name in sorted(surnames):
        if len(name) < 2:
            continue
        s = name.replace(",", "")
        rows.append(f"{s},0,0,3000,{s},{s},{s},{s},名詞,固有名詞,人名,姓,,,,,,")
    for name in sorted(given_names):
        if len(name) < 2:
            continue
        s = name.replace(",", "")
        rows.append(f"{s},0,0,3000,{s},{s},{s},{s},名詞,固有名詞,人名,名,,,,,,")

    csv_path.write_text("\n".join(rows), encoding="utf-8")
    print(f"  Building Sudachi user dict ({len(rows):,} entries)...")

    try:
        import sudachipy.command_line as _cl
        _saved = sys.argv[:]
        sys.argv = ["sudachipy", "ubuild", "-s", str(system_dic), "-o", str(dic_path), str(csv_path)]
        try:
            _cl.main()
        finally:
            sys.argv = _saved
    except SystemExit as e:
        if e.code not in (None, 0):
            print(f"  [WARNING] Sudachi dict build failed (exit {e.code})")
            return
    except Exception as e:
        print(f"  [WARNING] Sudachi dict build failed: {e}")
        return
    finally:
        csv_path.unlink(missing_ok=True)

    if dic_path.exists():
        print(f"  names_user.dic: {dic_path.stat().st_size / 1024:.0f} KB")
    else:
        print("  [WARNING] names_user.dic was not created")


def save(surnames: set[str], given_names: set[str], person_names: set[str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    print("Saving name data...")
    _build_sudachi_dict(surnames, given_names, person_names)

    for fname in ("surnames.txt", "given_names.txt", "person_names.txt", "names_patterns.pkl.gz"):
        p = DATA_DIR / fname
        if p.exists():
            p.unlink()
            print(f"  Removed legacy file: {fname}")


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    if XML_GZ.exists():
        print(f"Using existing file: {XML_GZ}")
    else:
        download(JMNEDICT_URL, XML_GZ)

    surnames, given_names, person_names = parse(XML_GZ)
    save(surnames, given_names, person_names)
    print("\nSaved to data/ directory.")


if __name__ == "__main__":
    main()
