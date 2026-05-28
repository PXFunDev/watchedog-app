import threading
import os
import sys

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

    # 実行ファイル直下の assert フォルダを優先して探す
    candidates = [
        os.path.join(root, "assert", "icon.ico"),
        os.path.join(root, "assert", "icon.png"),
        os.path.join(root, "src", "assert", "icon.png"),
        os.path.join(root, "src", "icon", "icon.png"),
        os.path.join(root, "icon", "icon.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


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
    pystray_impl = pystray if 'pystray' in globals() else None
    if pystray_impl is not None and icon_image is None:
        if Image is not None:
            try:
                icon_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            except Exception:
                print("pystray がアイコン作成に失敗したためトレイを無効化します")
                pystray_impl = None
        else:
            print("pystray があるが PIL がないためトレイを無効化します")
            pystray_impl = None

    quit_event = threading.Event()
    gui = MinimalGUI(exit_callback=quit_event.set)

    def on_start(icon=None, item=None):
        gui.start_watching()

    def on_stop(icon=None, item=None):
        gui.stop_watching()

    def on_exit(icon=None, item=None):
        try:
            if pystray_impl is not None and icon is not None:
                icon.visible = False
                icon.stop()
        except Exception:
            pass
        gui.stop_and_exit()

    def on_settings(icon=None, item=None):
        gui.root.after(0, gui.show_settings)

    # pystray を使わない場合は GUI のみで起動
    if pystray_impl is None:
        print("pystray が無効 — トレイなしで起動します")
        gui.start_watching()
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
    except Exception:
        print("トレイアイコンの初期化に失敗したためトレイを無効化します")
        gui.start_watching()
        gui.root.mainloop()
        return

    # 起動時に自動で監視を開始する
    try:
        gui.start_watching()
    except Exception:
        print("監視スレッドの起動に失敗しました")

    # トレイスレッド
    def _tray_runner():
        try:
            tray_icon.run()
        except Exception:
            # トレイ側の例外はログに出して無視
            print("トレイスレッドで例外が発生しました")

    threading.Thread(target=_tray_runner, daemon=True).start()

    try:
        gui.root.mainloop()
    finally:
        try:
            tray_icon.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()