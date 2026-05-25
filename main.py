import threading
import os
import sys

# `src` を `sys.path` の先頭に追加します。
# main.py を直接実行したときに `watchedog_app` パッケージをインポート可能にします。
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from src.gui import MinimalGUI

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pystray
except Exception:
    pystray = None

def _locate_icon():
    """アイコン画像を検索してファイルパスを返します。

    複数の候補パスを順に確認し、最初に存在するパスを返します。
    見つからなければ ``None`` を返します。
    """
    root = os.path.dirname(__file__)
    candidates = [
        os.path.join(root, "src", "assert", "icon.png"),
        os.path.join(root, "src", "icon", "icon.png"),
        os.path.join(root, "icon", "icon.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def main():
    """アプリのエントリポイント。

    システムトレイアイコンを初期化し、GUI と監視スレッドを起動します。
    pystray や Pillow (PIL) が利用できない環境ではフォールバック動作を行います。
    """

    icon_path = _locate_icon()
    if Image is not None and icon_path:
        try:
            icon_image = Image.open(icon_path)
        except Exception:
            icon_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    else:
        icon_image = None

    quit_event = threading.Event()
    gui = MinimalGUI(exit_callback=quit_event.set)


    def on_start(icon=None, item=None):
        """トレイメニューの「開始」アクション。

        監視を開始します。
        """
        gui.start_watching()

    def on_stop(icon=None, item=None):
        """トレイメニューの「中断」アクション。

        監視を停止します。
        """
        gui.stop_watching()

    def on_exit(icon=None, item=None):
        """トレイメニューの「終了」アクション。

        トレイアイコンを停止し、GUI を終了します。
        """
        if pystray is not None and icon is not None:
            try:
                icon.visible = False
                icon.stop()
            except Exception:
                pass
        gui.stop_and_exit()

    def on_settings(icon=None, item=None):
        """トレイメニューの「設定」アクション。

        GUI の設定ダイアログを表示します。
        """
        gui.root.after(0, gui.show_settings)

    if pystray is None:
        print("pystray not available — starting GUI without system tray")
        gui.start_watching()
        gui.root.mainloop()
    else:
        menu = pystray.Menu(
            pystray.MenuItem("開始", on_start),
            pystray.MenuItem("中断", on_stop),
            pystray.MenuItem("終了", on_exit),
            pystray.MenuItem("設定", on_settings),
        )
        tray_icon = pystray.Icon("folderwatch", icon_image, "フォルダ見えるくん", menu)

        def tray_thread():
            tray_icon.run()

        threading.Thread(target=tray_thread, daemon=True).start()
        gui.root.mainloop()

    sys.exit()


if __name__ == "__main__":
    main()