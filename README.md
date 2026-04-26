# pymasking — 個人情報マスキングツール

文書・画像に含まれる個人情報を自動検出してマスキングします。  
Web UI と CLI の両方で動作します。

---

## デモ

### テキストタブ — テキストを直接入力してマスキング

![テキストマスキングデモ](https://raw.githubusercontent.com/kirin123kirin/pymasking/main/doc/demo_text.gif)

### ファイルタブ — ドラッグ＆ドロップでファイルをマスキング

![ファイルマスキングデモ](https://raw.githubusercontent.com/kirin123kirin/pymasking/main/doc/demo_file.gif)

---

## 動作環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10 / 11（64bit） |
| Python | 3.9 以上 |

---

## インストール

```bash
pip install pymasking
```

### 画像 OCR モデルのダウンロード（画像の OCR マスキングに必要）

画像ファイル（jpg / png / bmp）のマスキングには EasyOCR の日本語モデル（約 96 MB）が必要です。  
以下のコマンドで事前にダウンロードできます。

```bash
# GitHub からダウンロード（デフォルト）
masking-download

# 社内サーバー / SharePoint からダウンロード
masking-download --url https://company.sharepoint.com/sites/IT/Shared%20Documents/ocr-models/
```

モデルは `pymasking/data/model/` に保存され、2回目以降はオフラインで動作します。  
既にダウンロード済みのファイルはスキップされます。

#### 手動でモデルをダウンロードする場合

ネットワーク制限等で `masking-download` が使えない場合は、以下の手順で手動配置できます。

**1. 以下の ZIP ファイルをブラウザ等でダウンロード**

| ファイル | ダウンロード URL |
|---|---|
| `craft_mlt_25k.zip` | https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip |
| `japanese_g2.zip` | https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/japanese_g2.zip |
| `english_g2.zip` | https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip |

**2. ZIP を展開し、`.pth` ファイルを取り出す**

各 ZIP を展開すると `.pth` ファイルが1つ含まれています。

**3. `pymasking/data/model/` フォルダに配置**

```
site-packages\pymasking\data\model\
    craft_mlt_25k.pth
    japanese_g2.pth
    english_g2.pth
```

> `site-packages` の場所は `python -c "import site; print(site.getsitepackages()[0])"` で確認できます。

---

## 起動方法

### Web UI（推奨）

```bash
masking
```

ブラウザで http://127.0.0.1:55963 が自動的に開きます。  
**ブラウザのタブ・ウィンドウを閉じるとサーバーも自動終了します。**

### CLI

```bash
python -m pymasking.cli.main mask report.docx
python -m pymasking.cli.main mask report.docx --mode unique
```

出力ファイルは元のファイルと同じフォルダに `_変換後` サフィックスを付けて保存されます（例: `report_変換後.docx`）。

---

## Web UI の使い方

### 共通操作

#### マスキング方式の選択

画面上部の 2 つのボタンで方式を選択します。  
ボタンをクリックするとマスキング前後の例が表示されます。

| ボタン | 効果 |
|--------|------|
| **伏字（●）** | 検出した情報を `●` で塗りつぶす（既定） |
| **一意性保持** | `人物001` のように種別＋連番に置換 |

#### マスキング対象の絞り込み

実行ボタンの直上にあるチェックボックスで、マスクする情報の種別を選べます。  
全て ON の場合はすべてのカテゴリを対象とします。

---

### テキストタブ

1. テキストエリアに文章を貼り付け（Ctrl+V 可）
2. 必要に応じてマスキング対象のチェックボックスを調整
3. **マスキング実行** をクリック
4. 下の結果欄に変換後テキストが表示される
5. **結果をコピー** でクリップボードにコピー

---

### ファイルタブ

1. ドロップエリアにファイルをドラッグ＆ドロップ、またはクリックして選択  
   （対応形式: docx / xlsx / pptx / pdf / jpg / png / bmp / txt / csv / json 等）
2. マスキング対象・追加オプションを確認
3. **マスキング実行** をクリック
   - ボタンが赤く点滅し「**実行中**」と表示されます
   - 下のプログレスバーで処理状況を確認できます
4. 処理完了後、ボタンがオレンジ色の「**ダウンロード**」に変わります
5. **ダウンロード** をクリックするとマスキング済みファイルが保存されます（ファイル名: 元のファイル名に `_変換後` を付加）

---

## 対応ファイル形式

| 形式 | 処理方法 |
|------|---------|
| `.txt` `.csv` `.json` `.xml` `.md` `.log` | テキスト置換 |
| `.docx` `.xlsx` `.pptx` | テキスト置換（書式保持） |
| `.pdf` | テキスト座標を検出 → 黒矩形で塗りつぶし |
| `.jpg` `.jpeg` `.png` `.bmp` | EasyOCR で検出 → 黒矩形で塗りつぶし |

---

## マスキング方式

| 方式 | 出力例 |
|------|--------|
| 伏字（デフォルト） | `●●●` |
| 一意性保持 | `人物001` |

> 画像・PDF は方式に関わらず常に視覚的塗りつぶし（黒矩形）になります。

---

## 検出カテゴリ

人物名 / 組織名 / 住所 / メールアドレス / 電話番号 / 日付 / 金額 / SNS アカウント / 特許番号 / シリアル番号 / 型番

---

## カスタム辞書

`pymasking/data/dict/custom_dict.txt` にタブ区切りで追加すると独自の固有名詞を検出できます：

```
山田太郎	person
株式会社サンプル	org
```
