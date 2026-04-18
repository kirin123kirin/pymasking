@echo off
setlocal
set REPO_DIR=%~dp0

echo ============================================================
echo  pymasking セットアップ
echo ============================================================

echo.
echo [1/3] 依存パッケージをインストール中...
pip install -e "%REPO_DIR%"
if errorlevel 1 goto :error

echo.
echo [2/3] spacy / ja-ginza をインストール中...
pip install ja-ginza spacy
if errorlevel 1 goto :error

echo.
echo [3/3] モデルをリポジトリ内にコピー中...
python "%REPO_DIR%scripts\download_model.py"
if errorlevel 1 goto :error

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
