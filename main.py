from pathlib import Path
import threading
import os
import sys
import json

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


# ルートパスを取得
def get_base_dir() -> Path:
    # exe（Nuitka / PyInstaller）
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent

    # __file__ が使える通常実行
    if '__file__' in globals():
        return Path(__file__).resolve().parent

    # 最終フォールバック（VSCodeなど例外環境）
    return Path.cwd()
    

# ===========================================
# config関連
# ===========================================

DEFAULT_CONFIG = {
    "watch_folder": "",
    "filename_keyword": "",
    "extensions": [".xlsx"],
    "target_name": "",
    "target_ext": ".xlsx",
    "last_used_folder": ""
}

def get_config_file_path() -> str:
    """設定ファイルパス取得"""
    return os.path.join(get_base_dir(), "config.json")


def load_config() -> dict:
    """設定ファイル読み込み（自己修復付き）"""
    config_path = get_config_file_path()

    # ① なければ作成
    if not os.path.exists(config_path):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    # ② 読み込み
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except Exception:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    # ③ キー補完
    updated = False

    # 旧キーから新キーへの互換補完
    if "target_name" not in config_data and "filename_keyword" in config_data:
        config_data["target_name"] = config_data.get("filename_keyword", "")
        updated = True

    if "target_ext" not in config_data:
        exts = config_data.get("extensions", [])
        if isinstance(exts, list) and exts:
            config_data["target_ext"] = exts[0]
        else:
            config_data["target_ext"] = DEFAULT_CONFIG["target_ext"]
        updated = True

    if "watch_folder" not in config_data and "last_used_folder" in config_data:
        config_data["watch_folder"] = config_data.get("last_used_folder", "")
        updated = True

    for key, value in DEFAULT_CONFIG.items():
        if key not in config_data:
            config_data[key] = value
            updated = True

    if updated:
        save_config(config_data)

    return config_data


def save_config(config_data: dict):
    """設定ファイル保存"""
    config_path = get_config_file_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"設定ファイル保存エラー: {e}")

# ===========================================
# アイコン関連
# ===========================================

def get_icon_path():
    """アイコンファイルパス取得"""
    return os.path.join(get_base_dir(), "src", "assets", "icon.png")

def locate_icon_file():
    """ビルド版かどうかでアイコンファイルの存在を確認してパスを返します。"""
    icon_path = get_icon_path()

    if os.path.exists(icon_path):
        return icon_path

    print("アイコンファイルが見つかりません:", icon_path)
    return None

def load_icon_image():
    """アイコン画像ロード"""
    icon_path = locate_icon_file()
    print("ICON_PATH:", icon_path)

    if Image is not None and icon_path:
        try:
            return Image.open(icon_path)
        except Exception as e:
            print("アイコン読み込み失敗:", e)

    return Image.new("RGBA", (64, 64), (0, 0, 0, 0))


# ===========================================
# GUI関連
# ===========================================

def _create_gui(config):
    """GUIを作成します"""
    quit_event = threading.Event()
    return MinimalGUI(config, exit_callback=quit_event.set)

def _run_without_tray(gui, config):
    """pystrayがない場合の起動方法"""
    print("pystrayなし → GUIのみ")

    _restore_last_folder(gui, config)

    gui.start_watching()
    gui.root.mainloop()

def _run_with_tray(gui, config, icon_image):
    """pystrayがある場合の起動方法"""
    print("トレイ起動")

    tray_icon = _create_tray(gui, config, icon_image)

    threading.Thread(target=tray_icon.run, daemon=True).start()

    _restore_last_folder(gui, config)

    gui.root.mainloop()

def _create_tray(gui, config, icon_image):
    """トレイアイコンを作成します"""
    def on_start(icon=None, item=None):
        """開始 メニューのコールバック"""
        print("監視開始")
        _save_last_folder(gui, config)
        gui.start_watching()

    def on_stop(icon=None, item=None):
        """中断 メニューのコールバック"""
        print("監視停止")
        gui.stop_watching()

    def on_exit(icon=None, item=None):
        """終了 メニューのコールバック"""
        print("終了")
        try:
            if icon:
                icon.visible = False
                icon.stop()
        except Exception:
            pass
        _save_last_folder(gui, config)
        gui.stop_and_exit()

    def on_settings(icon=None, item=None):
        """設定 メニューのコールバック"""
        gui.root.after(0, gui.show_settings)

    menu = pystray.Menu(
        pystray.MenuItem("開始", on_start),
        pystray.MenuItem("中断", on_stop),
        pystray.MenuItem("設定", on_settings),
        pystray.MenuItem("終了", on_exit),
    )

    return pystray.Icon("folderwatch", icon_image, "フォルダ見えるくん", menu)

def _save_last_folder(gui, config):
    """GUIの現在設定を設定ファイルへ保存します"""
    try:
        folder = getattr(gui, "target_folder", "")
        config["last_used_folder"] = folder
        config["watch_folder"] = folder

        target_name = getattr(gui, "target_name", "")
        target_ext = getattr(gui, "target_ext", "")
        config["target_name"] = target_name
        config["target_ext"] = target_ext

        # 既存設定との互換性のため旧キーも更新
        config["filename_keyword"] = target_name
        config["extensions"] = [target_ext] if target_ext else []

        save_config(config)
    except Exception:
        pass

def _restore_last_folder(gui, config):
    """設定ファイルからGUIの監視条件を復元します"""
    try:
        folder = config.get("last_used_folder") or config.get("watch_folder", "")
        if folder:
            gui.target_folder = folder

        gui.target_name = config.get("target_name", config.get("filename_keyword", ""))

        if "target_ext" in config:
            gui.target_ext = config.get("target_ext", "")
        else:
            exts = config.get("extensions", [])
            gui.target_ext = exts[0] if isinstance(exts, list) and exts else ""
    except Exception:
        pass


def main():
    config = load_config()              # 設定ファイル読み込み（自己修復付き）
    icon_image = load_icon_image()      # アイコン画像ロード
    gui = _create_gui(config)           # GUI作成

    # 起動方法の選択
    if pystray is None:
        _run_without_tray(gui, config)
    else:
        _run_with_tray(gui, config, icon_image)

    # 終了時に設定ファイルを保存 [20260616:add]
    _save_last_folder(gui, config)
    sys.exit()


if __name__ == "__main__":
    main()