# CLAUDE.md

このファイルはリポジトリ内で作業する Claude Code (claude.ai/code) へのガイダンスです。

## Git ワークフロー

変更は常に `main` ブランチへプッシュしてください。

## インストール・起動

```bash
# インストール
pip install pymasking

# OCR モデルの事前ダウンロード（初回のみ・画像マスキングに必要）
masking-download
# SSL エラーが出る場合（社内プロキシ環境）
masking-download --no-verify-ssl
# 社内サーバー / SharePoint からダウンロードする場合
masking-download --url https://company.sharepoint.com/sites/IT/Shared%20Documents/ocr-models/

# Web UI 起動
masking               # http://127.0.0.1:55963

# デスクトップにショートカットを作成（Windows）
masking-shortcut

# CLI でマスキング実行
python -m pymasking.cli.main mask report.docx
python -m pymasking.cli.main mask report.docx --mode unique
```

## アーキテクチャ概要

```
pymasking/
├── data/
│   ├── dict/
│   │   └── custom_dict.txt      # カスタム辞書（手動編集）
│   └── model/                   # EasyOCR モデル（masking-download で生成、git 管理外）
├── scripts/
│   ├── make_demo_gifs.py        # デモ GIF 自動生成（Playwright）
│   └── make_user_manual.py      # user_manual.docx 自動生成
├── doc/
│   ├── demo_text.gif
│   ├── demo_file.gif
│   └── user_manual.docx
└── pymasking/
    ├── core/
    │   ├── detector.py          # センシティブ情報の検出エンジン（GiNZA NLP + 正規表現）
    │   ├── masker.py            # mask_text — 検出→置換の統合処理
    │   ├── cipher/
    │   │   ├── unique.py        # 一意性保持方式（不可逆）: UniqueCounter クラス
    │   │   └── blackout.py      # 伏字（不可逆）: 文字数分の●に置換
    │   └── extractor/
    │       ├── __init__.py      # process_file() — 拡張子で処理を振り分け
    │       ├── plaintext.py     # テキストファイル（encoding 自動検出）
    │       ├── office.py        # docx / xlsx / pptx（テキスト置換）
    │       ├── image.py         # jpg / png（EasyOCR → 黒塗り）
    │       └── pdf_handler.py   # PDF（PyMuPDF でテキスト位置検索 → 黒矩形）
    ├── cli/main.py              # Click ベース CLI（mask / web コマンド）
    └── web/
        ├── app.py               # Flask アプリ（create_app() ファクトリ）
        └── templates/index.html # シングルページ UI
```

### 処理フロー

**テキスト系ファイル（txt / docx / xlsx / pptx）**
1. テキスト抽出 → `detect_all()` で検出 → `resolve_overlaps()` で重複排除
2. 後ろから `mask_start:mask_end` を置換（位置ずれ防止）
3. `_変換後` サフィックスを付けて同フォルダに保存

**画像・PDF（視覚的マスキング）**
- 画像: EasyOCR でワード位置を取得 → 検出語を黒矩形で塗りつぶし
- PDF: `fitz.Page.search_for()` でテキスト矩形を取得 → `draw_rect()` で黒塗り

### 人物・組織検出パイプライン（GiNZA 使用時）

```
テキスト
  ↓ SudachiPy（sudachidict_full で最高精度の形態素解析・旧字体正規化）
  ↓ GiNZA NER（文脈ベースの固有表現認識）
  ↓ EntityRuler（after="ner", overwrite_ents=False）
      ├─ person_names.txt（完全人名・最高信頼度）
      ├─ surnames.txt（姓・2文字以上）
      └─ given_names.txt（名・2文字以上）
  ↓ 検出結果（GiNZA + EntityRuler の補完）
```

- `phrase_matcher_attr="NORM"` で Sudachi の正規化形を使い旧字体・異体字に対応
- `overwrite_ents=False` で GiNZA 検出済みエンティティは上書きしない

### マスキング方式

| 方式 | 出力形式 | 可逆 |
|------|---------|------|
| 伏字（デフォルト） | `●●●` | ✗ |
| 一意性保持 | `日付001` | ✗ |

### カスタム辞書

`pymasking/data/dict/custom_dict.txt` にタブ区切りで語と種別を登録すると固有名詞を検出できる。

```
山田太郎	person
株式会社サンプル	org
```

## 主要依存ライブラリ

| ライブラリ | 用途 |
|-----------|------|
| click | CLI |
| flask | Web UI |
| python-docx / openpyxl / python-pptx | Office ファイル読み書き |
| PyMuPDF (fitz) | PDF テキスト位置検索・黒塗り |
| easyocr | 画像 OCR（モデルは masking-download で取得） |
| Pillow | 画像処理 |
| python-dateutil | 日付検証 |
| ja-ginza + spacy | 固有表現認識 |
| sudachidict_full | 高精度辞書（旧字体正規化・珍しい固有名詞対応） |
| pywin32 | Windows ショートカット作成（masking-shortcut） |
