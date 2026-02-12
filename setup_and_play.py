#!/usr/bin/env python3
"""
Bob's Big Adventure - 自動セットアップ＆起動スクリプト
Windows / Linux / Mac 対応
仮想環境を自動作成してクリーンな環境で実行
"""

import subprocess
import sys
import os
from pathlib import Path

VENV_DIR = Path('.venv')

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

def create_venv():
    """仮想環境を作成"""
    print("\n" + "=" * 60)
    print("仮想環境を作成しています...")
    print("=" * 60)
    
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'venv', str(VENV_DIR)],
            stdout=subprocess.DEVNULL
        )
        print("✅ 仮想環境の作成が完了しました")
    except subprocess.CalledProcessError as e:
        print(f"❌ 仮想環境の作成に失敗しました: {e}")
        print("\n以下を試してください:")
        print("  Ubuntu/Debian: sudo apt install python3-venv")
        print("  または: python3 -m pip install --user virtualenv")
        input("\nEnterキーを押して終了...")
        sys.exit(1)

def get_venv_python():
    """仮想環境のPythonパスを取得"""
    if os.name == 'nt':  # Windows
        return VENV_DIR / 'Scripts' / 'python.exe'
    else:  # Linux / Mac
        return VENV_DIR / 'bin' / 'python'

def get_venv_pip():
    """仮想環境のpipパスを取得"""
    if os.name == 'nt':  # Windows
        return VENV_DIR / 'Scripts' / 'pip.exe'
    else:  # Linux / Mac
        return VENV_DIR / 'bin' / 'pip'

def install_requirements():
    """必要なライブラリを仮想環境にインストール"""
    print("\n" + "=" * 60)
    print("必要なライブラリをインストールしています...")
    print("=" * 60)
    
    venv_pip = get_venv_pip()
    requirements = ['pygame>=2.0.0', 'numpy', 'pyttsx3>=2.90']
    
    for package in requirements:
        package_name = package.split('>=')[0].split('==')[0]
        print(f"\n📦 {package} をインストール中...")
        
        try:
            subprocess.check_call(
                [str(venv_pip), 'install', package, '--quiet'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"✅ {package} インストール完了")
        except subprocess.CalledProcessError:
            print(f"⚠️  {package} のインストールに失敗しました")
            print(f"\nインターネット接続を確認してください")
            input("\nEnterキーを押して終了...")
            sys.exit(1)
    
    # セットアップ完了マーカー作成
    Path('.setup_complete').touch()
    
    print("\n" + "=" * 60)
    print("✨ セットアップが完了しました！")
    print("=" * 60)

def check_venv_ready():
    """仮想環境が準備できているかチェック"""
    venv_python = get_venv_python()
    if not venv_python.exists():
        return False
    
    # 仮想環境内のライブラリチェック
    try:
        result = subprocess.run(
            [str(venv_python), '-c', 
             'import pygame; import numpy; import pyttsx3'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

def launch_game():
    """ゲームを仮想環境のPythonで起動"""
    print("\n🚀 ゲームを起動しています...\n")
    
    game_file = Path('shooting_game.py')
    if not game_file.exists():
        print("=" * 60)
        print("エラー: shooting_game.py が見つかりません")
        print("このスクリプトはゲームフォルダ内で実行してください")
        print("=" * 60)
        input("\nEnterキーを押して終了...")
        sys.exit(1)
    
    venv_python = get_venv_python()
    
    try:
        # 仮想環境のPythonでゲームを起動
        subprocess.run([str(venv_python), str(game_file)])
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
    
    # 仮想環境の確認と作成
    if not VENV_DIR.exists():
        print("\n初回セットアップを開始します...")
        create_venv()
        install_requirements()
        print("\n次回からは自動的にゲームが起動します")
        input("\nEnterキーを押してゲームを起動...")
    elif not check_venv_ready():
        print("\n仮想環境が不完全です。再セットアップします...")
        install_requirements()
        input("\nEnterキーを押してゲームを起動...")
    
    # ゲーム起動
    launch_game()

if __name__ == '__main__':
    main()
