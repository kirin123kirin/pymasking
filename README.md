# pymasking — 個人情報マスキングツール

文書・画像・クリップボードに含まれる個人情報を自動検出してマスキングします。  
CLI と Web UI の両方で動作します。

![操作デモ](docs/demo.gif)

---

## 動作環境

| 項目 | 要件 |
|------|------|
| OS | Windows 11 (64bit) |
| ネットワーク | セットアップ時のみ必要（初回のみ） |
| Tesseract | 画像OCRを使う場合のみ別途インストール |

> **Tesseract（画像マスキングを使う場合）**  
> [UB Mannheim 版インストーラー](https://github.com/UB-Mannheim/tesseract/wiki) で `jpn` 言語データを含めてインストールし、`PATH` を通してください。

---

## インストール

### 1. ZIP を展開する

以下のパスに ZIP の中身を展開してください（フォルダ名含む）：

```
%LOCALAPPDATA%\pymasking\
```

エクスプローラーのアドレスバーに上記を貼り付けると開けます。  
展開後のフォルダ構成：

```
%LOCALAPPDATA%\pymasking\
├── setup_model.bat
├── start_cli.bat
├── start_web.bat
├── pymasking\
├── data\
└── scripts\
```

### 2. セットアップを実行する

`setup_model.bat` をダブルクリックして実行します。  
以下を自動的に行います（初回のみ、ネットワーク接続が必要）：

| ステップ | 内容 | 目安時間 |
|---------|------|---------|
| 1 | Python 3.12.10 ランタイムをダウンロード・展開 | 1〜2 分 |
| 2 | pip をインストール | 1 分 |
| 3 | 依存ライブラリをインストール | 3〜5 分 |
| 4 | spaCy / ja-ginza をインストール | 2〜3 分 |
| 5 | SudachiDict_full をインストール（約 800MB） | 10〜20 分 |
| 6 | GiNZA モデルをコピー | 1〜2 分 |
| 7 | JMnedict 姓名データを取得（約 30MB） | 1〜2 分 |

完了するとデスクトップに **`pymasking.lnk`** ショートカットが作成されます。

---

## 起動方法

### Web UI（推奨）

デスクトップの **`pymasking`** ショートカットをダブルクリック、  
またはインストールフォルダの `start_web.bat` をダブルクリックします。

ブラウザで http://127.0.0.1:59631 が開きます。  
**ブラウザのタブ・ウィンドウを閉じるとサーバーも自動終了します。**

### CLI

```bat
start_cli.bat mask report.docx
start_cli.bat mask report.docx --mode pigpen
start_cli.bat mask --clipboard
start_cli.bat unmask report_masked.txt
```

---

## 対応ファイル形式

| 形式 | 処理方法 |
|------|---------|
| `.txt` `.csv` `.json` `.xml` `.md` `.log` | テキスト置換 |
| `.docx` `.xlsx` `.pptx` | テキスト置換（書式保持） |
| `.pdf` | テキスト位置を黒矩形で塗りつぶし |
| `.jpg` `.jpeg` `.png` | OCR で検出 → 黒矩形で塗りつぶし |

---

## マスキング方式

| 方式 | 出力例 | 復号 |
|------|--------|------|
| 伏字（デフォルト） | `●●●` | 不可 |
| 一意性保持 | `人物001` | 不可 |
| ピッグペン暗号 | `【人物:⊞⊟⊠⊡:】` | 可能（`unmask` コマンド） |

> 画像・PDF は方式に関わらず常に視覚的塗りつぶしになります。

---

## 検出カテゴリ

人物名 / 組織名 / 住所 / メールアドレス / 電話番号 / 日付 / 金額 / SNSアカウント / 特許番号 / シリアル番号 / 型番

---

## カスタム辞書

`data\dict\custom_dict.txt` にタブ区切りで追加すると独自の固有名詞を検出できます：

```
山田太郎	person
株式会社サンプル	org
```

---

## アンインストール

以下のフォルダを削除するだけです：

```
%LOCALAPPDATA%\pymasking\
```

デスクトップの `pymasking.lnk` も手動で削除してください。
