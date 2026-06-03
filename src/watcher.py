import threading
import os
import time
import json
from typing import List, Callable, Dict


class FolderWatcher(threading.Thread):
    """
    軽量なポーリング方式のフォルダ監視。
    外部依存を避けるため、watchfiles の代替として短い間隔でディレクトリを走査します。
    """
    def __init__(
        self,
        folder: str,
        target_name: str,
        target_ext: str,
        notifier,
        interval: float = 1.0,
    ):
        """フォルダ監視スレッドを初期化する。

        Args:
            folder: 監視対象のディレクトリパス。
            target_name: ファイル名の部分一致条件。
            target_ext: 監視対象の拡張子（例: '.xlsx'）。
            notifier: 変更を通知するコールバック関数 (title, message) を受け取る。
            interval: ポーリング間隔（秒）。
        """
        super().__init__()
        self.folder = folder
        self.target_name = target_name
        self.target_ext = target_ext
        self.notifier = notifier
        self._stop_event = threading.Event()
        self.interval = interval

    def run(self) -> None:
        """監視ループを実行する。

        指定間隔でディレクトリを走査し、新規追加ファイルが条件に合致する
        場合に `notifier` を呼び出します。
        """
        print(f"[FolderWatcher] 監視開始: {self.folder}")
        seen = set()
        try:
            if os.path.isdir(self.folder):
                for entry in os.listdir(self.folder):
                    seen.add(entry)
        except Exception:
            seen = set()

        while not self._stop_event.is_set():
            try:
                if os.path.isdir(self.folder):
                    current = set(os.listdir(self.folder))
                else:
                    current = set()
            except Exception:
                current = set()

            added = current - seen
            for filename in added:
                if self.target_name in filename and filename.endswith(self.target_ext):
                    path = os.path.join(self.folder, filename)
                    print(f"[FolderWatcher] ヒット: {filename}")
                    try:
                        self.notifier('作業報告書が追加されました', path)
                    except Exception:
                        print("[FolderWatcher] 通知に失敗しました")
            seen = current
            time.sleep(self.interval)

        print("[FolderWatcher] 監視停止。")

    def stop(self) -> None:
        """監視の停止を要求する。スレッドは次回のループで終了します。"""
        self._stop_event.set()
        print("[FolderWatcher] 監視停止シグナル発行")


def load_config(path: str) -> Dict:
    """設定ファイルを読み込んで辞書で返す。存在しない場合は空辞書を返す。"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def start_watchers_from_config(config_path: str, notifier: Callable[[str, str], None]) -> List[FolderWatcher]:
    """設定ファイルから監視対象を読み込み、フォルダ監視スレッドを起動する。

    サポートする設定キー:
    - "watch_folder": 文字列または空文字列
    - "watch_folders": 文字列のリスト
    - "target_name": ファイル名の部分一致 (省略可)
    - "target_ext": 拡張子 (省略可)
    - "interval": ポーリング間隔（秒、省略可）

    返り値: 起動した `FolderWatcher` オブジェクトのリスト
    """
    cfg = load_config(config_path)
    target_name = cfg.get('target_name', '')
    target_ext = cfg.get('target_ext', '')
    interval = float(cfg.get('interval', 1.0))

    folders = []
    if 'watch_folders' in cfg and isinstance(cfg['watch_folders'], list):
        folders = cfg['watch_folders']
    else:
        wf = cfg.get('watch_folder', '')
        if wf:
            folders = [wf]

    watchers: List[FolderWatcher] = []
    for folder in folders:
        w = FolderWatcher(folder=folder, target_name=target_name, target_ext=target_ext, notifier=notifier, interval=interval)
        w.daemon = True
        w.start()
        watchers.append(w)

    return watchers


if __name__ == '__main__':
    # テスト用簡易実行。カレントディレクトリの ../src/config.json を読み込む
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')

    def _print_notifier(title: str, message: str) -> None:
        print(f"[NOTIFY] {title}: {message}")

    ws = start_watchers_from_config(config_file, _print_notifier)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for w in ws:
            w.stop()
        time.sleep(0.2)
