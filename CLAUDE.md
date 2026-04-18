# CLAUDE.md

このファイルはリポジトリ内で作業する Claude Code (claude.ai/code) へのガイダンスです。

## Git ワークフロー

変更は常に `main` ブランチへプッシュしてください。

## インストール・起動

```bash
# 初回セットアップ（依存インストール＋GiNZAモデルをリポジトリ内に保存）
setup_model.bat

# CLI でマスキング実行
start_cli.bat mask report.docx
start_cli.bat mask report.docx --mode pigpen
start_cli.bat mask --clipboard
start_cli.bat unmask report_masked.txt

# Web インターフェースを起動
start_web.bat           # http://127.0.0.1:5000
start_web.bat 8080      # ポート指定
```

## GiNZA モデルの管理

- `setup_model.bat` を実行すると `models/ja_ginza/` にモデルがコピーされる
- バッチファイルは起動時に `GINZA_MODEL_PATH=%REPO_DIR%models\ja_ginza` を設定する
- `detector.py` は `GINZA_MODEL_PATH` → システムインストール済み → フォールバックの順で試みる
- `models/ja_ginza/` は `.gitignore` で除外されている（大容量のため）
- モデルを再取得する場合は `models/ja_ginza/` を削除して `setup_model.bat` を再実行

## アーキテクチャ概要

```
pymasking/
├── models/ja_ginza/     # GiNZA モデル（setup_model.bat で生成、git 管理外）
├── scripts/
│   └── download_model.py  # models/ja_ginza/ へモデルをコピーするスクリプト
├── core/
│   ├── detector.py      # センシティブ情報の検出エンジン（GiNZA NLP + 正規表現）
│   ├── masker.py        # mask_text / unmask_text — 検出→置換の統合処理
│   ├── cipher/
│   │   ├── pigpen.py    # ピッグペン暗号（可逆）: UTF-8 hex → Unicode記号
│   │   ├── unique.py    # 一意性保持方式（不可逆）: UniqueCounter クラス
│   │   └── blackout.py  # 伏字（不可逆）: 文字数分の●に置換
│   └── extractor/
│       ├── __init__.py  # process_file() — 拡張子で処理を振り分け
│       ├── plaintext.py # テキストファイル（encoding 自動検出）
│       ├── office.py    # docx / xlsx / pptx（テキスト置換）
│       ├── image.py     # jpg / png（OCR → 黒塗り）
│       ├── pdf_handler.py # PDF（PyMuPDF でテキスト位置検索 → 黒矩形）
│       └── clipboard.py # クリップボード読み取り・一時ファイル保存
├── cli/main.py          # Click ベース CLI（mask / unmask / web コマンド）
└── web/
    ├── app.py           # Flask アプリ（create_app() ファクトリ）
    └── templates/index.html  # シングルページ UI
```

### 処理フロー

**テキスト系ファイル（txt / docx / xlsx / pptx）**
1. テキスト抽出 → `detect_all()` で検出 → `resolve_overlaps()` で重複排除
2. 後ろから `mask_start:mask_end` を置換（位置ずれ防止）
3. `_masked` サフィックスを付けて同フォルダに保存

**画像・PDF（視覚的マスキング）**
- 画像: `pytesseract.image_to_data()` でワード位置を取得 → 検出語を黒矩形で塗りつぶし
- PDF: `fitz.Page.search_for()` でテキスト矩形を取得 → `draw_rect()` で黒塗り

### 暗号化方式

| 方式 | 出力形式 | 可逆 |
|------|---------|------|
| 伏字（デフォルト） | `●●●` | ✗ |
| 一意性保持 | `日付001` | ✗ |
| ピッグペン | `【日付:⊞⊟⊠…:】` | ✓ |

ピッグペンは `text.encode('utf-8').hex().upper()` の各 hex 文字を `⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭` へ全単射変換する。

### カスタム辞書

`dict/custom_dict.txt` にタブ区切りで語と種別を登録すると固有名詞を検出できる。

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
| pywin32 | Windows クリップボード（画像・ファイル取得） |
| ja-ginza + spacy | 固有表現認識（最優先。setup_model.bat で導入） |

> Windows 11 で Tesseract を使う場合は [Tesseract インストーラー](https://github.com/UB-Mannheim/tesseract/wiki) で `jpn` 言語データも含めてインストールし、`PATH` を通してください。
