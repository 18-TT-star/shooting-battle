@echo off
chcp 65001 >nul
title Bob's Big Adventure
cls

echo ============================================
echo   Bob's Big Adventure - 起動中...
echo ============================================
echo.

REM Pythonのパスを確認
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [エラー] Python が見つかりません！
    echo.
    echo Python 3.8以上をインストールしてください：
    echo https://www.python.org/downloads/
    echo.
    echo インストール時に "Add Python to PATH" に
    echo 必ずチェックを入れてください。
    echo.
    pause
    exit /b 1
)

echo Python を確認しました
python --version
echo.

REM ゲームを起動
python setup_and_play.py

REM エラーが発生した場合は待機
if %errorlevel% neq 0 (
    echo.
    echo [エラー] ゲームの起動に失敗しました
    pause
)
