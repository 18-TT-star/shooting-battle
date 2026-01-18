# Bob's Big Adventure - リリース手順

## 📦 配布パッケージの場所

ビルド後、以下の場所に配布用ファイルが作成されます：

```
release/
├── Bobs_Big_Adventure_v1.0_Linux.tar.gz    (Linux版)
└── Bobs_Big_Adventure_v1.0_Windows.zip     (Windows版)
```

## 🐧 Linux版のビルド方法

**Linux環境で実行:**

```bash
chmod +x build_release.sh
./build_release.sh
```

**生成されるファイル:**
- `release/Bobs_Big_Adventure_v1.0_Linux.tar.gz`

**ユーザー側の使い方:**
1. tar.gzファイルを解凍
2. `./BobsBigAdventure` を実行

---

## 🪟 Windows版のビルド方法

**Windows環境で実行が必要です**（Linux上ではWindows版は作れません）

### Windowsでのビルド手順:

1. **プロジェクトをWindowsマシンに転送**

2. **仮想環境を作成（初回のみ）:**
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install pygame numpy
   ```

3. **ビルドスクリプトを実行:**
   ```cmd
   build_release_windows.bat
   ```

**生成されるファイル:**
- `release/Bobs_Big_Adventure_v1.0_Windows.zip`

**ユーザー側の使い方:**
1. ZIPファイルを解凍
2. `BobsBigAdventure.exe` をダブルクリックで起動

---

## ⚠️ 重要な注意事項

### プラットフォーム依存性
- **Linux版はLinux上でのみビルド可能** → Linux実行ファイル生成
- **Windows版はWindows上でのみビルド可能** → Windows実行ファイル生成
- PyInstallerはクロスコンパイルに対応していません

### 両プラットフォーム対応するには:
1. Linux環境で `build_release.sh` を実行 → Linux版生成
2. Windows環境で `build_release_windows.bat` を実行 → Windows版生成
3. 両方のファイルを配布

---

## 📂 release/ フォルダの内容

ビルド完了後、以下の構成になります：

```
release/
├── BobsBigAdventure/              (Linux版展開済み)
│   ├── BobsBigAdventure           (実行ファイル)
│   ├── assets/
│   ├── saves/
│   └── README.txt
├── BobsBigAdventure_Windows/      (Windows版展開済み)
│   ├── BobsBigAdventure.exe       (実行ファイル)
│   ├── assets/
│   ├── saves/
│   └── README.txt
├── Bobs_Big_Adventure_v1.0_Linux.tar.gz     ← 配布用
└── Bobs_Big_Adventure_v1.0_Windows.zip      ← 配布用
```

---

## 🚀 配布方法

### GitHub Releasesで配布する場合:

1. GitHubリポジトリのページに移動
2. 右側の "Releases" をクリック
3. "Draft a new release" をクリック
4. 以下を設定:
   - **Tag version**: `v1.0`
   - **Release title**: `Bob's Big Adventure v1.0`
   - **Description**: ゲームの説明と操作方法
5. **Attach binaries** にファイルをドラッグ&ドロップ:
   - `Bobs_Big_Adventure_v1.0_Linux.tar.gz`
   - `Bobs_Big_Adventure_v1.0_Windows.zip`
6. "Publish release" をクリック

### 他の配布方法:
- itch.io
- Google Drive / Dropbox
- 自分のウェブサイト
- Steam（商用の場合）

---

## 🔧 トラブルシューティング

### Linux版ビルド時:
- **PyInstaller not found**: `pip install pyinstaller`
- **Permission denied**: `chmod +x build_release.sh`

### Windows版ビルド時:
- **Python not found**: Pythonをインストール（3.10以降推奨）
- **Virtual environment error**: `.venv` フォルダを削除して再作成

### 実行時の問題:
- **Linux**: `chmod +x BobsBigAdventure` で実行権限を付与
- **Windows**: Windows Defenderがブロック → 「詳細情報」→「実行」
- **音が出ない**: システムの音量設定を確認

---

## ✅ ビルド確認チェックリスト

- [ ] Linux版: `Bobs_Big_Adventure_v1.0_Linux.tar.gz` 作成完了
- [ ] Windows版: `Bobs_Big_Adventure_v1.0_Windows.zip` 作成完了
- [ ] Linux版: 実行テスト成功
- [ ] Windows版: 実行テスト成功（Windows環境で）
- [ ] README.txtが含まれている
- [ ] assetsフォルダ（音楽・フォント）が含まれている
- [ ] savesフォルダが作成されている
- [ ] ファイルサイズが適切（目安: 50-100MB）

---

**現在の状況**: Linux版のみビルド済み
**次のステップ**: Windows環境で `build_release_windows.bat` を実行してWindows版を作成
