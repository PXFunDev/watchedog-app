

import threading
import os
import sys
import json


# パッケージ参照用に src をパス先頭に追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from src.gui import MinimalGUI

try:
    from PIL import Image
except Exception:
    Image = None

# pystray の読み込み（frozen でも可能なら読み込む）
try:
    import pystray
except Exception:
    pystray = None

def _locate_icon():
    """候補からアイコンのパスを返す。見つからなければ None を返す。"""
    # frozen 実行ファイルでは、可能なら PyInstaller の展開先（_MEIPASS）を優先
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            root = meipass
        else:
            # one-folder 形式や未展開の場合は実行ファイルのディレクトリ
            root = os.path.dirname(sys.executable)
    else:
        root = os.path.dirname(__file__)

    # 実行ファイル直下の assets フォルダを優先して探す
    candidates = [
        os.path.join(root, "assets", "icon.ico"),
        os.path.join(root, "assets", "icon.png"),
        os.path.join(root, "src", "assets", "icon.png"),
        os.path.join(root, "src", "icon", "icon.png"),
        os.path.join(root, "icon", "icon.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

# 現在のディレクトリを取得
def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable) # .exeとして実行
    else:
        return os.path.dirname(__file__)       # 通常スクリプト

def main():
    """エントリポイント。GUI とシステムトレイを安全に起動する。"""

    # アイコン画像を用意する
    icon_image = None
    icon_path = _locate_icon()
    if Image is not None and icon_path:
        try:
            icon_image = Image.open(icon_path)
        except Exception:
            try:
                icon_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            except Exception:
                icon_image = None

    # pystray の有無とアイコンの有無で動作を決める（ローカル変数で扱う）
    pystray_impl = pystray
    if pystray_impl is not None and icon_image is None:
        if Image is not None:
            try:
                icon_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            except Exception:
                print("[WARN] pystray がアイコン作成に失敗したためトレイを無効化します")
                pystray_impl = None
        else:
            print("[WARN] pystray があるが PIL がないためトレイを無効化します")
            pystray_impl = None

    # 設定ファイルの読み込み
    config_path = os.path.join(get_base_dir(), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("設定ファイルが見つかりませんでした。")
        print("デフォルト設定で起動します。")
        config = {}
    except json.JSONDecodeError as e:
        print(f"設定ファイルの読み込みに失敗しました: {e}. ")
        print("デフォルト設定で起動します。")
        config = {}

    # GUI を初期化する
    quit_event = threading.Event()
    gui = MinimalGUI(exit_callback=quit_event.set)

    # 読み込んだ設定を GUI に反映する
    if isinstance(config, dict):
        # 複数フォルダ指定があれば先頭を採用
        if 'watch_folders' in config and isinstance(config['watch_folders'], list) and config['watch_folders']:
            gui.folder = config['watch_folders'][0]
        else:
            wf = config.get('watch_folder')
            if wf:
                gui.folder = wf

        gui.target_name = config.get('target_name', gui.target_name)
        gui.target_ext = config.get('target_ext', gui.target_ext)
        try:
            print("[main] 設定反映: ", gui.folder, gui.target_name, gui.target_ext)
        except Exception as e:
            print(f"[WARN] 設定の反映に失敗しました: {e}")

    def on_start(icon=None, item=None):
        gui.root.after(0, gui.start_watching)

    def on_stop(icon=None, item=None):
        gui.root.after(0, gui.stop_watching)

    def on_exit(icon=None, item=None):
        try:
            if pystray_impl is not None and icon is not None:
                icon.visible = False
                icon.stop()
        except Exception as e:
            print(f"[WARN] トレイアイコンの停止に失敗しました: {e}")
        gui.root.after(0, gui.stop_and_exit)

    def on_settings(icon=None, item=None):
        gui.root.after(0, gui.show_settings)

    # pystray を使わない場合は GUI のみで起動
    if pystray_impl is None:
        print("pystray が無効 — トレイなしで起動します")
        gui.root.after(0, gui.start_watching)
        gui.root.mainloop()
        return

    # メニューとトレイアイコンを作成
    menu = pystray_impl.Menu(
        pystray_impl.MenuItem("開始", on_start),
        pystray_impl.MenuItem("中断", on_stop),
        pystray_impl.MenuItem("終了", on_exit),
        pystray_impl.MenuItem("設定", on_settings),
    )

    try:
        tray_icon = pystray_impl.Icon("folderwatch", icon_image, "フォルダ見えるくん", menu)
    except Exception as e:
        print(f"[WARN] トレイアイコンの初期化に失敗したためトレイを無効化します: {e}")
        gui.root.after(0, gui.start_watching)
        gui.root.mainloop()
        return

    # 起動時に自動で監視を開始する
    try:
        gui.root.after(0, gui.start_watching)
    except Exception as e:
        print(f"[WARN] 監視スレッドの起動に失敗しました: {e}")

    # トレイスレッド
    def _tray_runner():
        try:
            tray_icon.run()
        except Exception as e:
            # トレイ側の例外はログに出して無視
            print(f"[WARN] トレイスレッドで例外が発生しました: {e}")

    threading.Thread(target=_tray_runner, daemon=True).start()

    try:
        gui.root.mainloop()
    finally:
        try:
            tray_icon.stop()
        except Exception as e:
            print(f"[WARN] トレイアイコンの停止に失敗しました: {e}")


if __name__ == "__main__":
    main()