# フォルダ見えるくん (watchedog-app)

軽量なフォルダ監視アプリケーション（社内利用）。指定フォルダに特定の名前・拡張子を持つファイルが追加されたときに、Windows のトースト通知およびタスクトレイ操作で監視を制御します。

**現状の仕様（要点）**
- 監視エンジン: `watchfiles.watch` を用いた監視スレッド（`FolderWatcher`）
- GUI: 最小構成の Tk をメインループで動かし、タスクトレイ操作で監視開始/停止/設定表示を行う（`MinimalGUI`）
- 通知: `win11toast` を使ったトースト通知をメインスレッド経由で表示
- タスクトレイ: `pystray` を使用し、開始/中断/設定/終了メニューを提供
- デフォルト監視条件: ユーザーディレクトリ下の `.project/TEST`、ファイル名に「作業報告書」を含み拡張子 `.xlsx` を対象

動作は `main.py` の `main()` で開始します。現在はアプリケーション全体が一つのスクリプトにまとまっています。

対応環境
- OS: Windows（トースト通知は Windows 向け実装）
- Python: >=3.12

依存（実行に必要な主なパッケージ）
- watchfiles
- win11toast
- pystray
- pillow (PIL)

インストール（開発環境）
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -U pip
pip install watchfiles win11toast pystray pillow
```

起動方法
- 開発中/手動実行: `python main.py`
- GUI はタスクトレイで操作します（右クリックメニューから設定/開始/中断/終了）。

プロジェクト構成（主要ファイル）
- `main.py` - 現在のエントリポイント。GUI と監視ロジックを含む。
- `src/` - 配布用のパッケージ領域（`watchedog_app` モジュール等）
- `pyproject.toml` - プロジェクト設定・ビルド設定（社内テンプレート）

注意点
- `src/watchedog_app` 以下はまだ最小実装です。配布用パッケージ化を行う場合は、`__main__` などエントリポイント実装を整備してください。
- トースト通知やタスクトレイの動作は環境依存のため、テストは実機 Windows 上で行ってください。

今後のタスク
- `main` を `gui` とフォルダ監視（watcher）に分解する
- `main` はエントリーポイントとしての役割だけを残す

貢献方法
- まずは `gui` と `watcher` の分割を行い、`src/watchedog_app` 以下にモジュール化してください。
- 単体テスト（watcher の挙動）と CI の追加を推奨します。

---
この README は現在の実装を短くまとめたものです。分割や CI 追加を行う場合、README を更新します。

