@echo off
REM ===================================================
REM Bob's Big Adventure - Windows Release Build Script
REM ===================================================

echo === Bob's Big Adventure - Windows Release Build ===
echo.

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Error: Virtual environment not found!
    echo Please create a virtual environment first: python -m venv .venv
    pause
    exit /b 1
)

REM Install PyInstaller if not already installed
echo Installing PyInstaller...
python -m pip install pyinstaller

REM Clean old build files
echo Cleaning old build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "BobsBigAdventure.spec" del "BobsBigAdventure.spec"

REM Build executable with PyInstaller
echo Creating Windows executable...
pyinstaller --name="BobsBigAdventure" ^
    --onefile ^
    --windowed ^
    --add-data="assets;assets" ^
    --add-data="saves;saves" ^
    --hidden-import=pygame ^
    --hidden-import=numpy ^
    --collect-all pygame ^
    shooting_game.py

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

REM Prepare release directory
echo Preparing release package...
if exist "release\BobsBigAdventure_Windows" rmdir /s /q "release\BobsBigAdventure_Windows"
mkdir "release\BobsBigAdventure_Windows"

REM Copy executable
copy "dist\BobsBigAdventure.exe" "release\BobsBigAdventure_Windows\"

REM Copy assets folder
xcopy /E /I /Y "assets" "release\BobsBigAdventure_Windows\assets"

REM Create saves folder
mkdir "release\BobsBigAdventure_Windows\saves"

REM Create README
echo ==================================================>> "release\BobsBigAdventure_Windows\README.txt"
echo          Bob's Big Adventure - Windows版>> "release\BobsBigAdventure_Windows\README.txt"
echo ==================================================>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo 【起動方法】>> "release\BobsBigAdventure_Windows\README.txt"
echo BobsBigAdventure.exe をダブルクリックで起動します。>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo 【操作方法】>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo ■ タイトル画面>> "release\BobsBigAdventure_Windows\README.txt"
echo   スペースキー - ゲーム開始 / メニュー進行>> "release\BobsBigAdventure_Windows\README.txt"
echo   T キー - タイトル画面に戻る>> "release\BobsBigAdventure_Windows\README.txt"
echo   ESC キー - ゲーム終了>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo ■ ステージ選択>> "release\BobsBigAdventure_Windows\README.txt"
echo   ↑↓ キー - ステージ選択>> "release\BobsBigAdventure_Windows\README.txt"
echo   スペースキー - 選択決定>> "release\BobsBigAdventure_Windows\README.txt"
echo   ESC / T キー - タイトルに戻る>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo ■ バトル画面>> "release\BobsBigAdventure_Windows\README.txt"
echo   矢印キー - プレイヤー移動>> "release\BobsBigAdventure_Windows\README.txt"
echo   スペースキー - 弾を発射>> "release\BobsBigAdventure_Windows\README.txt"
echo   P キー - ポーズ>> "release\BobsBigAdventure_Windows\README.txt"
echo   T キー - タイトルに戻る（ポーズ中のみ）>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo ■ 装備画面>> "release\BobsBigAdventure_Windows\README.txt"
echo   ↑↓ キー - アイテム選択>> "release\BobsBigAdventure_Windows\README.txt"
echo   スペースキー - 装備ON/OFF切替>> "release\BobsBigAdventure_Windows\README.txt"
echo   ESC / T キー - タイトルに戻る>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo 【ゲーム目標】>> "release\BobsBigAdventure_Windows\README.txt"
echo - 全6ステージのボスを倒してゲームクリア！>> "release\BobsBigAdventure_Windows\README.txt"
echo - ステージクリア後、装備アイテムを獲得できます>> "release\BobsBigAdventure_Windows\README.txt"
echo - 全ステージクリア後、装備なしモードに挑戦可能>> "release\BobsBigAdventure_Windows\README.txt"
echo - 装備なしモード全クリアで真のエンディングへ！>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo 【セーブデータ】>> "release\BobsBigAdventure_Windows\README.txt"
echo セーブデータは saves フォルダに保存されます。>> "release\BobsBigAdventure_Windows\README.txt"
echo 3つのセーブスロットが使用可能です。>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo 【動作環境】>> "release\BobsBigAdventure_Windows\README.txt"
echo - Windows 7 以降>> "release\BobsBigAdventure_Windows\README.txt"
echo - 画面解像度: 800x600 以上推奨>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo 【トラブルシューティング】>> "release\BobsBigAdventure_Windows\README.txt"
echo - ゲームが起動しない場合は、Windows Defender等の>> "release\BobsBigAdventure_Windows\README.txt"
echo   セキュリティソフトが実行をブロックしている可能性があります。>> "release\BobsBigAdventure_Windows\README.txt"
echo - 音が出ない場合は、Windowsの音量設定を確認してください。>> "release\BobsBigAdventure_Windows\README.txt"
echo.>> "release\BobsBigAdventure_Windows\README.txt"
echo 【クレジット】>> "release\BobsBigAdventure_Windows\README.txt"
echo Created with Python ^& Pygame>> "release\BobsBigAdventure_Windows\README.txt"
echo ==================================================>> "release\BobsBigAdventure_Windows\README.txt"

REM Create ZIP archive
echo Creating ZIP archive...
cd release
powershell Compress-Archive -Path "BobsBigAdventure_Windows" -DestinationPath "Bobs_Big_Adventure_v1.0_Windows.zip" -Force
cd ..

echo.
echo === Build Complete! ===
echo.
echo Release package: release\Bobs_Big_Adventure_v1.0_Windows.zip
echo Extracted folder: release\BobsBigAdventure_Windows\
echo.
echo Distribute the ZIP file. Users can extract and run BobsBigAdventure.exe!
echo.
pause
