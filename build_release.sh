#!/bin/bash
# ゲームのリリースビルドを作成するスクリプト

set -e

echo "=== Bob's Big Adventure - リリースビルド ==="
echo ""

# 仮想環境をアクティベート
source .venv/bin/activate

# PyInstallerがインストールされているか確認
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstallerをインストール中..."
    pip install pyinstaller
fi

# 古いビルドを削除
echo "古いビルドファイルを削除中..."
rm -rf build dist *.spec

# PyInstallerでビルド
echo "実行ファイルを作成中..."
pyinstaller --name="BobsBigAdventure" \
    --onefile \
    --windowed \
    --add-data="assets:assets" \
    --add-data="saves:saves" \
    --hidden-import=pygame \
    --hidden-import=numpy \
    --collect-all pygame \
    shooting_game.py

# releaseディレクトリの準備
echo "リリースパッケージを準備中..."
rm -rf release/BobsBigAdventure
mkdir -p "release/BobsBigAdventure"

# 実行ファイルをコピー
cp "dist/BobsBigAdventure" "release/BobsBigAdventure/"

# assetsフォルダをコピー
cp -r assets "release/BobsBigAdventure/"

# savesフォルダを作成
mkdir -p "release/BobsBigAdventure/saves"

# README作成
cat > "release/BobsBigAdventure/README.txt" << 'EOF'
==================================================
      Bob's Big Adventure
==================================================

■ 遊び方
  「Bob's Big Adventure」実行ファイルをダブルクリックして起動してください。

■ 操作方法
  【タイトル画面】
    Enter: ゲーム開始
    
  【ステージ選択】
    ↑↓: ステージ選択
    Enter: 選択したステージを開始
    E: 装備画面
    S: セーブ
    L: ロード
    T: タイトルに戻る
    
  【バトル中】
    矢印キー: 移動
    Z / Space: 弾を撃つ
    V: 武器切り替え（ホーミング弾/拡散弾を解放後）
    ←← / →→: ダッシュ（二度押し、解放後）
    P / ESC: ポーズ
    Q: 即座に終了
    
  【装備画面】
    ↑↓: 装備選択
    Enter / Space: オン/オフ切り替え
    ESC: メニューに戻る

■ ゲームの目的
  6体のボスを倒してゲームクリアを目指そう！
  装備なしクリアで金の星、ボス6を装備なし＆phase1からクリアで虹の星が獲得できます。

■ セーブデータ
  ゲームのセーブデータは「saves」フォルダに保存されます。
  
■ 動作環境
  - Linux (推奨)
  - その他のOSでも動作する可能性があります

■ トラブルシューティング
  - 音が出ない場合: システムの音量設定を確認してください
  - 起動しない場合: ターミナルから実行してエラーメッセージを確認してください

■ クレジット
  Game Design & Programming: T.T
  Music: Various (詳細はゲーム内参照)
  
バージョン: 1.0
リリース日: 2026年1月18日

==================================================
EOF

# 圧縮アーカイブ作成
echo "アーカイブを作成中..."
cd release
tar -czf Bobs_Big_Adventure_v1.0_Linux.tar.gz "BobsBigAdventure"
cd ..

echo ""
echo "=== ビルド完了！ ==="
echo ""
echo "リリースパッケージ: release/Bobs_Big_Adventure_v1.0_Linux.tar.gz"
echo "展開済みフォルダ: release/Bob's Big Adventure/"
echo ""
echo "配布するには tar.gz ファイルを使用してください。"
echo "ユーザーは解凍後、「Bob's Big Adventure」を実行するだけで遊べます。"
