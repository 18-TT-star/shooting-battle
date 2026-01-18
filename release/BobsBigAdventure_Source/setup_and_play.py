#!/usr/bin/env python3
"""
Bob's Big Adventure - 自動セットアップ＆起動スクリプト
Windows / Linux / Mac 対応
"""

import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """Python バージョンチェック"""
    if sys.version_info < (3, 8):
        print("=" * 60)
        print("エラー: Python 3.8 以上が必要です")
        print(f"現在のバージョン: Python {sys.version_info.major}.{sys.version_info.minor}")
        print("https://www.python.org/ から最新版をダウンロードしてください")
        print("=" * 60)
        input("Enterキーを押して終了...")
        sys.exit(1)

def install_requirements():
    """必要なライブラリをインストール"""
    print("\n" + "=" * 60)
    print("初回セットアップを実行しています...")
    print("=" * 60)
    
    requirements = ['pygame>=2.0.0', 'numpy']
    
    for package in requirements:
        print(f"\n📦 {package} をインストール中...")
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', package, '--quiet'],
                stdout=subprocess.DEVNULL
            )
            print(f"✅ {package} インストール完了")
        except subprocess.CalledProcessError:
            print(f"❌ {package} のインストールに失敗しました")
            print("インターネット接続を確認してください")
            input("\nEnterキーを押して終了...")
            sys.exit(1)
    
    # セットアップ完了マーカー作成
    Path('.setup_complete').touch()
    
    print("\n" + "=" * 60)
    print("✨ セットアップが完了しました！")
    print("=" * 60)

def check_dependencies():
    """依存ライブラリがインストール済みかチェック"""
    try:
        import pygame
        import numpy
        return True
    except ImportError:
        return False

def launch_game():
    """ゲームを起動"""
    print("\n🚀 ゲームを起動しています...\n")
    
    game_file = Path('shooting_game.py')
    if not game_file.exists():
        print("=" * 60)
        print("エラー: shooting_game.py が見つかりません")
        print("このスクリプトはゲームフォルダ内で実行してください")
        print("=" * 60)
        input("\nEnterキーを押して終了...")
        sys.exit(1)
    
    try:
        # ゲームを起動
        subprocess.run([sys.executable, str(game_file)])
    except KeyboardInterrupt:
        print("\n\nゲームを終了しました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        input("\nEnterキーを押して終了...")
        sys.exit(1)

def main():
    """メイン処理"""
    os.chdir(Path(__file__).parent)
    
    print("=" * 60)
    print("  Bob's Big Adventure - クロスプラットフォーム版")
    print("=" * 60)
    
    # Python バージョンチェック
    check_python_version()
    
    # 初回セットアップチェック
    setup_marker = Path('.setup_complete')
    if not setup_marker.exists() or not check_dependencies():
        install_requirements()
        print("\n次回からは自動的にゲームが起動します")
        input("\nEnterキーを押してゲームを起動...")
    
    # ゲーム起動
    launch_game()

if __name__ == '__main__':
    main()
