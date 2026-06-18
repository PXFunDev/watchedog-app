# フォルダ監視常駐アプリ (watchedog-app)

社内利用向けの軽量フォルダ監視アプリです。
指定フォルダに条件一致するファイルが追加されたとき、Windows トースト通知を表示し、タスクトレイから監視を操作できます。

## 現状の仕様（要点）

- エントリーポイント: `main.py` の `main()`
- GUI: `src/gui.py` の `MinimalGUI`（Tk を最小表示で起動し、設定ダイアログを提供）
- 監視エンジン: `src/watcher.py` の `FolderWatcher`
	- `watchfiles` ではなく、`os.listdir` によるポーリング方式で新規ファイルを検出
- 通知: `win11toast` を利用（失敗時は標準出力にフォールバック）
- タスクトレイ: `pystray` を利用（未導入時はトレイなしで起動）
- 設定: 実行ディレクトリの `config.json` を読み書き
	- `watch_folder`
	- `filename_keyword`
	- `extensions`
	- `last_used_folder`（実行時に追記される）

## 対応環境

- OS: Windows
- Python: >= 3.12

## 依存（主なパッケージ）

- pystray
- pillow
- win11toast
- watchdog（`pyproject.toml` 定義）

注: 現行の監視実装 (`src/watcher.py`) は `watchdog` を直接使用していません。

## インストール（開発環境）

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e .
```

## 起動方法

- 開発中/手動実行: `python main.py`

## Nuitka でワンファイルビルド（Windows）

1. ビルドツールをインストール

```bash
python -m pip install -U nuitka ordered-set zstandard
```

2. プロジェクトルートでビルド

```bash
uv run python -m nuitka `
  main.py `
  --standalone `
  --onefile `
  --windows-disable-console `
  --enable-plugin=tk-inter `
  --follow-imports `
  --remove-output `
  --assume-yes-for-downloads `
  --windows-icon-from-ico=src/assets/icon.ico `
  --include-data-file=src/assets/icon.png=src/assets/icon.png `
  --output-dir=dist `
  --output-filename=フォルダ監視くん.exe
```

3. 生成物

- 実行ファイル: `build/main.exe`

注:
- `win11toast` / `pystray` / `tkinter` は実行環境依存です。実機 Windows で動作確認してください。
- 現在のアイコン探索は `main.py` のロジックに依存します。必要に応じて `get_base_dir()` と `get_icon_path()` を配布形態に合わせて調整してください。

## プロジェクト構成（主要ファイル）

- `main.py`: エントリーポイント。設定読込、アイコン読込、GUI起動、トレイ連携を担当
- `src/gui.py`: GUI と監視開始/停止、設定ダイアログ
- `src/watcher.py`: フォルダ監視スレッド（ポーリング方式）
- `src/assert/icon.png`: タスクトレイアイコン
- `config.json`: 監視設定の保存先
- `pyproject.toml`: プロジェクト定義

## 注意点

- `pyproject.toml` のパッケージ設定（`watchedog_app`）と、現行の `src/` 配下構成には差分があります。
- トースト通知とタスクトレイの挙動は環境依存のため、実機 Windows で確認してください。

## 進捗

- `main` から GUI (`src/gui.py`) と監視ロジック (`src/watcher.py`) への分離は完了しています。
