"""センシティブ情報の検出エンジン。"""

import re
import calendar
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import List

def _setup_nlp():
    """Load ja_ginza.

    names_user.dic is registered in sudachipy/resources/sudachi.json at build time
    by download_names.py, so no runtime config is needed here.
    compound_splitter excluded: ja_ginza 5.x ships split_mode=null which fails
    confection validation on newer spacy/confection versions.
    """
    import spacy
    return spacy.load("ja_ginza", exclude=["compound_splitter"])


try:
    _nlp = _setup_nlp()
    _HAS_GINZA = True
except Exception as _e:
    import logging as _logging
    _logging.getLogger(__name__).warning("ja_ginza を読み込めませんでした（正規表現のみで動作します）: %s", _e)
    _HAS_GINZA = False
    _nlp = None

CUSTOM_DICT_PATH = Path(__file__).parent.parent / "data" / "dict" / "custom_dict.txt"

_custom_persons: List[str] = []
_custom_orgs: List[str] = []


def _load_custom_dict() -> None:
    global _custom_persons, _custom_orgs
    if not CUSTOM_DICT_PATH.exists():
        return
    for line in CUSTOM_DICT_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        word = parts[0]
        category = parts[1].strip().lower() if len(parts) > 1 else "person"
        if "org" in category:
            _custom_orgs.append(word)
        else:
            _custom_persons.append(word)
    _custom_persons.sort(key=len, reverse=True)
    _custom_orgs.sort(key=len, reverse=True)


_load_custom_dict()


@dataclass
class Detection:
    start: int
    end: int
    category: str
    text: str
    preserved_prefix: str = ""
    preserved_suffix: str = ""

    @property
    def mask_text(self) -> str:
        s = len(self.preserved_prefix)
        e = len(self.text) - len(self.preserved_suffix) if self.preserved_suffix else len(self.text)
        e = max(s, e)
        return self.text[s:e]

    @property
    def mask_start(self) -> int:
        return self.start + len(self.preserved_prefix)

    @property
    def mask_end(self) -> int:
        return max(self.mask_start, self.end - len(self.preserved_suffix))


# ── 都道府県 ──────────────────────────────────────────────────
PREFECTURES = (
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
    "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府",
    "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県",
    "山口県", "徳島県", "香川県", "愛媛県", "高知県",
    "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
)
_PREF_PAT = "|".join(re.escape(p) for p in PREFECTURES)

# ── 役職・敬称 ─────────────────────────────────────────────────
_TITLES = [
    "代表取締役社長", "代表取締役", "取締役社長", "取締役", "執行役員",
    "社長", "副社長", "専務", "常務",
    "部長", "副部長", "課長", "係長", "主任", "担当",
    "支店長", "所長", "院長", "局長", "室長", "センター長",
    "教授", "准教授", "講師", "助教", "博士", "先生",
    r"さん", r"様", r"氏", r"君", r"ちゃん",
    r"Mr\.", r"Ms\.", r"Mrs\.", r"Dr\.", r"Prof\.",
]
_TITLE_PAT = "|".join(sorted(_TITLES, key=len, reverse=True))

# ── 組織サフィックス ───────────────────────────────────────────
_ORG_SUFFIXES = [
    "株式会社", "有限会社", "合同会社", "合名会社", "合資会社",
    "一般社団法人", "一般財団法人", "公益社団法人", "公益財団法人",
    "医療法人", "学校法人", "社会福祉法人", "宗教法人",
    r"Inc\.", r"Corp\.", "LLC", r"Ltd\.", r"Co\.",
    "銀行", "証券", "保険", "信託", "組合",
    "大学院", "大学", "高等学校", "高校", "中学校", "小学校", "幼稚園", "保育園",
    "病院", "クリニック", "診療所",
    "研究所", "研究院",
    "省", "庁",
]
_ORG_SUFFIX_PAT = "|".join(sorted(_ORG_SUFFIXES, key=len, reverse=True))

# ── 建物名サフィックス ─────────────────────────────────────────
_BUILDING_SUFFIXES = [
    "ビルディング", "ビル", "タワー", "マンション", "アパート",
    "ハイツ", "コーポ", "レジデンス", "プラザ", "センター",
    "ハウス", "ホーム", "パーク", "ガーデン", "ヒルズ",
]
_BUILDING_PAT = "|".join(re.escape(b) for b in sorted(_BUILDING_SUFFIXES, key=len, reverse=True))

# ── 一般姓リスト（約100件）────────────────────────────────────
# 1文字姓（林・森・岡等）は単独語との誤検知が多いため意図的に除外
_SURNAMES = [
    "佐藤", "鈴木", "高橋", "田中", "渡辺", "伊藤", "山本", "中村", "小林", "加藤",
    "吉田", "山田", "佐々木", "山口", "松本", "井上", "木村", "斎藤", "清水",
    "山崎", "阿部", "池田", "橋本", "山下", "石川", "中島", "前田", "藤田",
    "小川", "後藤", "岡田", "長谷川", "村上", "近藤", "石井", "坂本", "遠藤", "青木",
    "藤井", "西村", "福田", "太田", "三浦", "原田", "中川", "松田", "岡本", "中野",
    "今村", "久保", "菅原", "武田", "小島", "工藤", "丸山", "上田", "横山", "大野",
    "宮崎", "宮本", "内田", "高田", "安藤", "島田", "大西", "萩原", "永田",
    "川口", "松井", "岩崎", "小野", "田村", "野村", "川村", "星野",
    "藤原", "服部", "吉川", "土屋", "中山", "菊地", "谷口", "今井", "杉山", "水野",
    "大塚", "河野", "平野", "熊谷", "秋山", "栗原", "三田", "増田", "浜田", "西川",
    "橘", "松岡", "新井", "辻", "和田", "福島", "大石", "原", "斉藤", "千葉",
    "山上", "田口", "川田", "西田", "東", "北村", "南", "上野", "下田", "高木",
    "桑田", "大村", "小山", "浅野", "吉野", "桐島", "片山", "村田", "奥田", "堀",
]
_SURNAME_PAT = "|".join(re.escape(s) for s in sorted(_SURNAMES, key=len, reverse=True))

_DATE_CONTEXT_KEYWORDS = [
    "日付", "日時", "年月日", "生年月日", "締切", "期限",
    "予定日", "発行日", "受領日", "入社日", "退社日",
    "date", "Date", "DATE",
]
_DATE_CTX_WIN = 50

_MONTHS_EN = (
    "January|February|March|April|May|June|"
    "July|August|September|October|November|December"
)

_KANJI_NUM = {"〇": "0", "一": "1", "二": "2", "三": "3", "四": "4",
              "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}

_WAREKI_BASE = {"令和": 2018, "平成": 1988, "昭和": 1925, "大正": 1911, "明治": 1867}


def _normalize(text: str) -> str:
    result = unicodedata.normalize("NFKC", text)
    return "".join(_KANJI_NUM.get(c, c) for c in result)


def _valid_date(year: int, month: int, day: int) -> bool:
    if not (1900 <= year <= 2100) or not (1 <= month <= 12):
        return False
    return 1 <= day <= calendar.monthrange(year, month)[1]


# ── [修正1] 日付バリデーション ─────────────────────────────────

def _validate_date_text(text: str) -> bool:
    """マッチした文字列が実在する日付かを検証する。"""
    norm = _normalize(text)

    # 和暦年月日
    m = re.match(r"(明治|大正|昭和|平成|令和)\s*(\d{1,3})年\s*(\d{1,2})月\s*(\d{1,2})日", norm)
    if m:
        y = _WAREKI_BASE.get(m.group(1), 0) + int(m.group(2))
        return _valid_date(y, int(m.group(3)), int(m.group(4)))

    # 西暦年月日
    m = re.match(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", norm)
    if m:
        return _valid_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # YYYY/M/D  YYYY-MM-DD  YYYY.MM.DD
    m = re.match(r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$", norm)
    if m:
        return _valid_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # 8桁 YYYYMMDD
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", norm)
    if m:
        return _valid_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # 和暦省略形 R7.4.1
    m = re.match(r"^[RHTSMrhtsmｒｈｔｓｍ](\d{1,2})\.(\d{1,2})\.(\d{1,2})$", norm)
    if m:
        return 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31

    # 月日のみ
    m = re.match(r"^(\d{1,2})月(\d{1,2})日$", norm)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        return 1 <= month <= 12 and 1 <= day <= 31

    return True  # 検証できない形式はそのまま通す


# ── 日付検出 ──────────────────────────────────────────────────

def detect_dates(text: str) -> List[Detection]:
    results: List[Detection] = []

    raw_patterns = [
        r"(?:明治|大正|昭和|平成|令和)\s*\d{1,3}年\s*\d{1,2}月\s*\d{1,2}日",
        r"[１２12][０-９0-9]{3}年\s*\d{1,2}月\s*\d{1,2}日",
        r"(?:" + _MONTHS_EN + r")\s+\d{1,2},?\s+[12]\d{3}",
        r"\d{1,2}(?:st|nd|rd|th)?\s+(?:" + _MONTHS_EN + r")\s+[12]\d{3}",
        r"[RHTSMrhtsmｒｈｔｓｍ]\d{1,2}\.\d{1,2}\.\d{1,2}",
        r"[12]\d{3}/\d{1,2}/\d{1,2}",
        r"[12]\d{3}-\d{2}-\d{2}",
        r"[12]\d{3}\.\d{2}\.\d{2}",
        r"(?<!\d)[12]\d{7}(?!\d)",
        r"\d{1,2}月\d{1,2}日",
    ]

    for pat in raw_patterns:
        for m in re.finditer(pat, text):
            if _validate_date_text(m.group()):  # [修正1] バリデーション追加
                results.append(Detection(m.start(), m.end(), "日付", m.group()))

    # MM/DD（文脈依存）
    for m in re.finditer(r"(?<!\d)\d{1,2}/\d{1,2}(?!\d)", text):
        cs = max(0, m.start() - _DATE_CTX_WIN)
        ce = min(len(text), m.end() + _DATE_CTX_WIN)
        if any(kw in text[cs:ce] for kw in _DATE_CONTEXT_KEYWORDS):
            norm = _normalize(m.group())
            parts = norm.split("/")
            try:
                if len(parts) == 2 and 1 <= int(parts[0]) <= 12 and 1 <= int(parts[1]) <= 31:
                    results.append(Detection(m.start(), m.end(), "日付", m.group()))
            except ValueError:
                pass

    return results


# ── 人物・組織検出 ──────────────────────────────────────────────

def detect_persons_orgs(text: str) -> List[Detection]:
    results: List[Detection] = []

    # カスタム辞書は GiNZA 有無に関わらず常に実行
    for word in _custom_persons:
        for m in re.finditer(re.escape(word), text):
            results.append(Detection(m.start(), m.end(), "人物", m.group()))
    for word in _custom_orgs:
        for m in re.finditer(re.escape(word), text):
            results.append(Detection(m.start(), m.end(), "組織", m.group()))

    if _HAS_GINZA and _nlp is not None:
        doc = _nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("Person", "PERSON"):
                results.append(Detection(ent.start_char, ent.end_char, "人物", ent.text))
            elif ent.label_ in ("ORG", "Organization", "Company"):
                results.append(Detection(ent.start_char, ent.end_char, "組織", ent.text))
        # 既知姓パターンで補完（姓＋漢字1〜3文字の名）
        pat_d = rf"({_SURNAME_PAT})([\u4E00-\u9FFF]{{1,3}})(?![\u4E00-\u9FFF])"
        for m in re.finditer(pat_d, text):
            results.append(Detection(m.start(), m.end(), "人物", m.group()))
        # 敬称（さん・様・氏等）直前の語も補完：GiNZA が短文脈で見落とす場合のフォールバック
        _hon = r"さん|様|氏|君|ちゃん|Mr\.|Ms\.|Mrs\.|Dr\.|Prof\."
        pat_b_hon = rf"([\u3040-\u9FFF]{{1,6}})(?:{_hon})"
        for m in re.finditer(pat_b_hon, text):
            results.append(Detection(m.start(1), m.end(1), "人物", m.group(1)))
        return results

    # B: 役職・敬称の直前テキスト
    pat_b = rf"([\u3040-\u9FFF]{{1,6}})(?:{_TITLE_PAT})"
    for m in re.finditer(pat_b, text):
        results.append(Detection(m.start(1), m.end(1), "人物", m.group(1)))

    # C: 組織名サフィックス
    pat_c = rf"[\u4E00-\u9FFF\u30A0-\u30FFa-zA-Z]{{2,20}}(?:{_ORG_SUFFIX_PAT})"
    for m in re.finditer(pat_c, text):
        results.append(Detection(m.start(), m.end(), "組織", m.group()))

    # D: 既知姓＋漢字1〜3文字の名
    # [修正3] 後方に漢字が続く場合は複合語の可能性が高いため除外
    pat_d = rf"({_SURNAME_PAT})([\u4E00-\u9FFF]{{1,3}})(?![\u4E00-\u9FFF])"
    for m in re.finditer(pat_d, text):
        results.append(Detection(m.start(), m.end(), "人物", m.group()))

    return results


# ── 住所検出 ───────────────────────────────────────────────────

_ADDR_BODY = r"[\u3040-\u9FFF\uFF00-\uFFEF0-9０-９a-zA-Z\-\s]{5,50}"

def detect_addresses(text: str) -> List[Detection]:
    results: List[Detection] = []

    for m in re.finditer(r"〒\d{3}-\d{4}" + _ADDR_BODY, text):
        results.append(Detection(m.start(), m.end(), "住所", m.group(), preserved_prefix="〒"))

    for m in re.finditer(rf"({_PREF_PAT})" + _ADDR_BODY, text):
        pref = m.group(1)
        results.append(Detection(m.start(), m.end(), "住所", m.group(), preserved_prefix=pref))

    for m in re.finditer(r"[\u4E00-\u9FFF]{2,6}(?:市|区|町|村)[\u3040-\u9FFF0-9０-９\-]{3,30}", text):
        results.append(Detection(m.start(), m.end(), "住所", m.group()))

    for m in re.finditer(rf"[\u30A0-\u30FFa-zA-Z0-9\u4E00-\u9FFF]{{2,20}}(?:{_BUILDING_PAT})", text):
        results.append(Detection(m.start(), m.end(), "住所", m.group()))

    branch = "支社|支店|工場|営業所|事業所|出張所"
    for m in re.finditer(rf"(?:{_PREF_PAT})[\u4E00-\u9FFF]{{2,10}}({branch})", text):
        results.append(Detection(m.start(), m.end(), "住所", m.group(), preserved_suffix=m.group(1)))

    return results


# ── メール ────────────────────────────────────────────────────

def detect_emails(text: str) -> List[Detection]:
    pat = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    return [Detection(m.start(), m.end(), "メール", m.group()) for m in re.finditer(pat, text)]


# ── SNS ───────────────────────────────────────────────────────

def detect_sns(text: str) -> List[Detection]:
    results: List[Detection] = []
    pats = [
        r"@[a-zA-Z0-9_\.]{2,30}",
        # [修正4] 汎用URLを除外し、既知SNSドメインのみに絞る
        r"https?://(?:www\.)?(?:twitter|x|instagram|github|discord|linkedin|facebook|tiktok|youtube)\.com/\S{2,80}",
    ]
    for pat in pats:
        for m in re.finditer(pat, text):
            results.append(Detection(m.start(), m.end(), "SNS", m.group()))
    return results


# ── 電話番号 ───────────────────────────────────────────────────

def detect_phones(text: str) -> List[Detection]:
    results: List[Detection] = []
    pats = [
        r"\+81[\-\s]?\d{1,4}[\-\s]?\d{1,4}[\-\s]?\d{4}",
        r"0120[\-\s]?\d{3}[\-\s]?\d{3}",
        r"0[5-9]0[\-\s]?\d{4}[\-\s]?\d{4}",
        r"0\d{1,4}[\-\s]?\d{1,4}[\-\s]?\d{4}",
    ]
    for pat in pats:
        for m in re.finditer(pat, text):
            results.append(Detection(m.start(), m.end(), "電話", m.group()))
    return results


# ── 特許番号 ───────────────────────────────────────────────────

def detect_patents(text: str) -> List[Detection]:
    results: List[Detection] = []
    specs = [
        (r"特許第(\d+)号", "特許", "特許第", "号"),
        (r"特願(\d{4}-\d+)", "特許", "特願", ""),
        (r"特開(\d{4}-\d+)", "特許", "特開", ""),
        (r"US\d{7,8}[A-Z]\d?", "特許", "", ""),
        (r"EP\d{7}[A-Z]\d?", "特許", "", ""),
    ]
    for pat, cat, pre, suf in specs:
        for m in re.finditer(pat, text):
            results.append(Detection(m.start(), m.end(), cat, m.group(),
                                     preserved_prefix=pre, preserved_suffix=suf))
    return results


# ── シリアル番号 ───────────────────────────────────────────────

def detect_serials(text: str) -> List[Detection]:
    # [修正5] ラベルあり（厳密）＋ラベルなし（形式パターン）の2段階
    results: List[Detection] = []

    # ラベルあり
    labeled = r"(?:S/N|SN|Serial\s*No\.?|製造番号|シリアル番号|シリアルNo\.?)\s*:?\s*([A-Z0-9][A-Z0-9\-]{4,19})"
    for m in re.finditer(labeled, text, re.IGNORECASE):
        results.append(Detection(m.start(), m.end(), "シリアル", m.group()))

    # ラベルなし（大文字英字2字以上＋数字4桁以上のパターン）
    unlabeled = r"(?<![A-Z0-9])(?:[A-Z]{2,4}-\d{4,12}|\d{4,12}-[A-Z]{2,4})(?![A-Z0-9])"
    for m in re.finditer(unlabeled, text):
        results.append(Detection(m.start(), m.end(), "シリアル", m.group()))

    return results


# ── 型番 ──────────────────────────────────────────────────────

def detect_models(text: str) -> List[Detection]:
    results: List[Detection] = []

    # ラベルあり
    labeled = r"(?:型番|品番|モデル(?:番号)?|Model\s*No\.?|Part\s*No\.?)\s*:?\s*([A-Z][A-Z0-9\-]{3,20})"
    for m in re.finditer(labeled, text, re.IGNORECASE):
        results.append(Detection(m.start(), m.end(), "型番", m.group()))

    # ラベルなし（英字1〜3字＋ハイフン＋数字4〜8桁の典型的型番）
    unlabeled = r"(?<![A-Z0-9])([A-Z]{1,3}-\d{4,8})(?![A-Z0-9\-])"
    for m in re.finditer(unlabeled, text):
        results.append(Detection(m.start(), m.end(), "型番", m.group()))

    return results


# ── 金額 ──────────────────────────────────────────────────────

def detect_amounts(text: str) -> List[Detection]:
    # \d+ で1桁単位付き金額（3億円, 1万円）も検出する
    pat = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:兆|億|万|千)?円"
    return [Detection(m.start(), m.end(), "金額", m.group()) for m in re.finditer(pat, text)]


# ── 統合 ──────────────────────────────────────────────────────

def detect_all(text: str, categories: set = None) -> List[Detection]:
    results: List[Detection] = []
    results.extend(detect_dates(text))
    results.extend(detect_persons_orgs(text))
    results.extend(detect_addresses(text))
    results.extend(detect_emails(text))
    results.extend(detect_sns(text))
    results.extend(detect_phones(text))
    results.extend(detect_patents(text))
    results.extend(detect_serials(text))
    results.extend(detect_models(text))
    results.extend(detect_amounts(text))
    if categories is not None:
        results = [d for d in results if d.category in categories]
    return results


def resolve_overlaps(detections: List[Detection]) -> List[Detection]:
    """重複区間を解決：長い方を優先。"""
    if not detections:
        return []
    sorted_dets = sorted(detections, key=lambda d: (d.start, -(d.end - d.start)))
    result: List[Detection] = []
    last_end = -1
    for det in sorted_dets:
        if det.start >= last_end:
            result.append(det)
            last_end = det.end
    return result
