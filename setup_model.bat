@echo off
setlocal
set REPO_DIR=%~dp0

echo ============================================================
echo  pymasking セットアップ
echo ============================================================

echo.
echo [1/5] 依存パッケージをインストール中...
pip install -e "%REPO_DIR%"
if errorlevel 1 goto :error

echo.
echo [2/5] spacy / ja-ginza をインストール中...
pip install ja-ginza spacy
if errorlevel 1 goto :error

echo.
echo [3/5] SudachiDict_full をインストール中（高精度辞書 約800MB）...
pip install sudachidict_full
if errorlevel 1 (
    echo [警告] sudachidict_full のインストールに失敗しました。
    echo        標準辞書（sudachidict_core）で動作します。
)

echo.
echo [4/5] GiNZA モデルをリポジトリ内にコピー中...
python "%REPO_DIR%scripts\download_model.py"
if errorlevel 1 goto :error

echo.
echo [5/5] JMnedict 姓名データを取得中（約30MB、初回のみ）...
python "%REPO_DIR%scripts\download_names.py"
if errorlevel 1 (
    echo [警告] JMnedict の取得に失敗しました。
    echo        ネットワーク接続を確認して scripts\download_names.py を手動実行してください。
    echo        GiNZA 単体モードで動作します。
)

echo.
echo ============================================================
echo  セットアップ完了
echo  GINZA_MODEL_PATH=%REPO_DIR%models\ja_ginza
echo  start_cli.bat  : CLI 起動
echo  start_web.bat  : Web UI 起動
echo ============================================================
pause
exit /b 0

:error
echo.
echo エラーが発生しました。
pause
exit /b 1
