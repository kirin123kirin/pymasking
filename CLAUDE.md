# CLAUDE.md

このファイルはリポジトリ内で作業する Claude Code (claude.ai/code) へのガイダンスです。

## Git ワークフロー

変更は常に `main` ブランチへプッシュしてください。

## インストール・起動

```bash
# 初回セットアップ（embedded Python ダウンロード＋依存インストール＋GiNZAモデル保存）
setup_model.bat

# CLI でマスキング実行
start_cli.bat mask report.docx
start_cli.bat mask report.docx --mode pigpen

# Web インターフェースを起動
start_web.bat           # http://127.0.0.1:5000
start_web.bat 8080      # ポート指定
```

## GiNZA モデルの管理

- `setup_model.bat` を実行すると `data/models/ja_ginza/` にモデルがコピーされる
- バッチファイルは起動時に `GINZA_MODEL_PATH=%REPO_DIR%data\models\ja_ginza` を設定する
- `detector.py` は `GINZA_MODEL_PATH` → システムインストール済み → フォールバックの順で試みる
- `data/models/ja_ginza/` は `.gitignore` で除外されている（大容量のため）
- モデルを再取得する場合は `data/models/ja_ginza/` を削除して `setup_model.bat` を再実行

## アーキテクチャ概要

```
pymasking/
├── data/
│   ├── dict/
│   │   └── custom_dict.txt  # カスタム辞書（手動編集）
│   ├── models/ja_ginza/     # GiNZA モデル（setup_model.bat で生成、git 管理外）
│   ├── surnames.txt         # JMnedict 由来の姓リスト（setup_model.bat で生成）
│   ├── given_names.txt      # JMnedict 由来の名リスト（setup_model.bat で生成）
│   └── person_names.txt     # JMnedict 由来の完全人名リスト（setup_model.bat で生成）
├── scripts/
│   ├── runtime/             # Python 3.12.10 embedded（setup_model.bat で生成、git 管理外）
│   ├── tesseract/           # Tesseract OCR v5.5.0 + jpn 言語データ（setup_model.bat で生成、git 管理外）
│   └── download_names.py    # JMnedict を取得して data/ へ保存するスクリプト
├── pymasking/
│   ├── core/
│   │   ├── detector.py      # センシティブ情報の検出エンジン（GiNZA NLP + 正規表現）
│   │   ├── masker.py        # mask_text — 検出→置換の統合処理
│   │   ├── cipher/
│   │   │   ├── pigpen.py    # ピッグペン暗号（暗号化のみ）: UTF-8 hex → Unicode記号
│   │   │   ├── unique.py    # 一意性保持方式（不可逆）: UniqueCounter クラス
│   │   │   └── blackout.py  # 伏字（不可逆）: 文字数分の●に置換
│   │   └── extractor/
│   │       ├── __init__.py  # process_file() — 拡張子で処理を振り分け
│   │       ├── plaintext.py # テキストファイル（encoding 自動検出）
│   │       ├── office.py    # docx / xlsx / pptx（テキスト置換）
│   │       ├── image.py     # jpg / png（OCR → 黒塗り）
│   │       └── pdf_handler.py # PDF（PyMuPDF でテキスト位置検索 → 黒矩形）
│   ├── cli/main.py          # Click ベース CLI（mask / web コマンド）
│   └── web/
│       ├── app.py           # Flask アプリ（create_app() ファクトリ）
│       └── templates/index.html  # シングルページ UI
```

### 処理フロー

**テキスト系ファイル（txt / docx / xlsx / pptx）**
1. テキスト抽出 → `detect_all()` で検出 → `resolve_overlaps()` で重複排除
2. 後ろから `mask_start:mask_end` を置換（位置ずれ防止）
3. `_masked` サフィックスを付けて同フォルダに保存

**画像・PDF（視覚的マスキング）**
- 画像: `pytesseract.image_to_data()` でワード位置を取得 → 検出語を黒矩形で塗りつぶし
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

### 暗号化方式

| 方式 | 出力形式 | 可逆 |
|------|---------|------|
| 伏字（デフォルト） | `●●●` | ✗ |
| 一意性保持 | `日付001` | ✗ |
| ピッグペン | `【日付:⊞⊟⊠…:】` | ✗（復号機能を削除済み） |

ピッグペンは `text.encode('utf-8').hex().upper()` の各 hex 文字を `⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭` へ全単射変換する（暗号化のみ）。

### カスタム辞書

`data/dict/custom_dict.txt` にタブ区切りで語と種別を登録すると固有名詞を検出できる。

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
| pytesseract + Tesseract | 画像 OCR |
| Pillow | 画像処理 |
| python-dateutil | 日付検証 |
| ja-ginza + spacy | 固有表現認識（最優先。setup_model.bat で導入） |
| sudachidict_full | 高精度辞書（旧字体正規化・珍しい固有名詞対応） |

> Windows 11 で Tesseract を使う場合は [Tesseract インストーラー](https://github.com/UB-Mannheim/tesseract/wiki) で `jpn` 言語データも含めてインストールし、`PATH` を通してください。
