import threading  # 並列処理用（監視スレッド）
import tkinter as tk  # GUI本体
from tkinter import ttk, filedialog  # GUI部品とファイルダイアログ
from watchfiles import watch, Change  # フォルダ監視
from win11toast import toast  # Windows11用トースト通知
import pystray  # タスクトレイ常駐アイコン
from PIL import Image  # アイコン画像読込
import os  # OS操作
import sys  # システム終了用


# =============================
# フォルダ監視スレッドクラス
# =============================
class FolderWatcher(threading.Thread):
    """
    指定フォルダを監視し、条件に合うファイルが追加されたら通知するスレッド。
    別スレッドで動作し、stop()で安全に停止可能。
    """
    def __init__(self, folder, target_name, target_ext, notifier):
        super().__init__()
        self.folder = folder  # 監視対象フォルダ
        self.target_name = target_name  # ファイル名部分一致条件
        self.target_ext = target_ext  # 拡張子条件
        self.notifier = notifier  # 通知関数（トースト表示）
        self._stop_event = threading.Event()  # 停止用イベント

    def run(self):
        print(f"[FolderWatcher] 監視開始: {self.folder}")
        # watchfilesでフォルダ監視ループ
        for changes in watch(self.folder, stop_event=self._stop_event):
            for change, path in changes:
                filename = os.path.basename(path)
                # ファイル追加かつ条件一致で通知
                if (change == Change.added and
                    self.target_name in filename and
                    filename.endswith(self.target_ext)):
                    print(f"[FolderWatcher] ヒット: {filename}")
                    self.notifier('作業報告書が追加されました', path)
            # 停止指示が来たらループ脱出
            if self._stop_event.is_set():
                break
        print("[FolderWatcher] 監視停止。")

    def stop(self):
        """監視スレッドの停止指示"""
        self._stop_event.set()
        print("[FolderWatcher] 監視停止シグナル発行")



# =============================
# 最小構成のGUI＆監視制御クラス
# =============================
class MinimalGUI:
    """
    ボタン無し・プログラム制御専用のTkウィンドウ。
    タスクトレイからの操作や設定ウィンドウ表示、監視スレッドの制御を担当。
    """
    def __init__(self, exit_callback):
        # --- Tkinterウィンドウ初期化（非表示・最小化） ---
        self.root = tk.Tk()
        self.root.title("フォルダ見えるくん")
        self.root.geometry("1x1+0+0")
        self.root.withdraw()  # 最初はウィンドウ非表示
        # --- 監視パラメータ初期値 ---
        username = os.environ["USERNAME"]
        self.folder = fr"C:\Users\{username}\.project\TEST"  # 監視対象フォルダ
        self.target_name = '作業報告書'  # ファイル名部分一致
        self.target_ext = '.xlsx'  # 拡張子
        self.watcher = None  # 監視スレッド
        # --- 通知関数（トーストをメインスレッドで実行） ---
        self.notifier = lambda title, msg: self.root.after(0, toast, title, msg, "short")
        self.exit_callback = exit_callback  # 終了時コールバック
        self.root.protocol("WM_DELETE_WINDOW", self.stop_and_exit)  # 閉じるボタン押下時
        print("[MinimalGUI] 初期化: 監視対象", self.folder)

    def start_watching(self):
        """
        監視スレッドを起動。
        既に起動中なら何もしない。
        """
        if self.watcher is None or not self.watcher.is_alive():
            print("[MinimalGUI] 監視スレッド起動")
            self.watcher = FolderWatcher(
                self.folder, self.target_name, self.target_ext, self.notifier
            )
            self.watcher.start()
            toast('監視を開始しました', self.folder, duration="short")
        else:
            toast('既に監視中です', '', duration="short")
            print("[MinimalGUI] 既に監視中")

    def stop_watching(self):
        """
        監視スレッドを停止。
        既に停止中なら何もしない。
        """
        if self.watcher is not None and self.watcher.is_alive():
            print("[MinimalGUI] 監視スレッド停止")
            self.watcher.stop()
            self.watcher.join()
            self.watcher = None
            toast('監視を中断しました', '', duration="short")
        else:
            toast('監視は停止中です', '', duration="short")
            print("[MinimalGUI] 監視は元々停止中")

    def show_settings(self):
        """
        設定ウィンドウの表示。
        監視対象フォルダ・ファイル名・拡張子をGUIで編集可能。
        OKで即反映＆監視再起動。
        """

        def browse_folder():
            # フォルダ選択ダイアログ表示
            folder_selected = filedialog.askdirectory()
            if folder_selected:
                folder_var.set(folder_selected)

        # --- 設定ウィンドウ構築 ---
        setting_win = tk.Toplevel(self.root)
        setting_win.title("設定")
        setting_win.geometry("400x200")
        setting_win.resizable(False, False)

        # 現在値をtkinter変数に束縛
        folder_var = tk.StringVar(value=self.folder)
        name_var   = tk.StringVar(value=self.target_name)
        ext_var    = tk.StringVar(value=self.target_ext)

        # --- 各種入力欄 ---
        tk.Label(setting_win, text="監視対象フォルダ:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        folder_entry = tk.Entry(setting_win, textvariable=folder_var, width=35)
        folder_entry.grid(row=0, column=1, padx=2)
        folder_button = tk.Button(setting_win, text="参照", command=browse_folder)
        folder_button.grid(row=0, column=2, padx=2)

        tk.Label(setting_win, text="ファイル名(部分一致):").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        name_entry = tk.Entry(setting_win, textvariable=name_var)
        name_entry.grid(row=1, column=1, columnspan=2, padx=2, sticky="we")

        tk.Label(setting_win, text="拡張子:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        ext_entry = tk.Entry(setting_win, textvariable=ext_var)
        ext_entry.grid(row=2, column=1, columnspan=2, padx=2, sticky="we")

        def apply_settings():
            # 入力値で監視パラメータを更新し、監視再起動
            self.folder = folder_var.get()
            self.target_name = name_var.get()
            self.target_ext = ext_var.get()
            self.stop_watching()
            self.start_watching()
            toast('設定を反映し再監視中', f'新: {self.folder}\n{self.target_name}{self.target_ext}', duration="short")
            print("[MinimalGUI] 設定反映:", self.folder, self.target_name, self.target_ext)
            setting_win.destroy()

        # --- OK/キャンセルボタン ---
        button_frame = tk.Frame(setting_win)
        button_frame.grid(row=3, column=0, columnspan=3, pady=15)
        ttk.Button(button_frame, text="OK", command=apply_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="キャンセル", command=setting_win.destroy).pack(side="left", padx=5)

        setting_win.grab_set()  # モーダル化（設定完了まで他操作不可）

    def stop_and_exit(self):
        """
        監視停止＆GUI終了＆コールバック呼び出し。
        完全終了処理。
        """
        self.stop_watching()
        self.root.quit()
        self.exit_callback()
        print("[MinimalGUI] 完全終了")


# =============================
# アプリ全体のエントリポイント
# =============================
def main():
    # --- アイコン画像のパス取得 ---
    BASE_DIR = os.path.dirname(__file__)
    icon_path = os.path.join(BASE_DIR, "icon", "icon.png")
    print(f"[main] アイコンパス: {icon_path}")
    icon_image = Image.open(icon_path)
    quit_event = threading.Event()  # 終了通知用イベント

    # --- GUIインスタンス生成 ---
    gui = MinimalGUI(exit_callback=quit_event.set)

    # --- タスクトレイメニューのコールバック定義 ---
    def on_start(icon, item):
        gui.start_watching()  # 監視開始
    def on_stop(icon, item):
        gui.stop_watching()  # 監視停止
    def on_exit(icon, item):
        icon.visible = False
        icon.stop()
        gui.stop_and_exit()  # 完全終了
    def on_settings(icon, item):
        # 設定ウィンドウを「メインスレッド」に依頼
        gui.root.after(0, gui.show_settings)

    # --- タスクトレイメニュー構築 ---
    menu = pystray.Menu(
        pystray.MenuItem("開始", on_start),
        pystray.MenuItem("中断", on_stop),
        pystray.MenuItem("終了", on_exit),
        pystray.MenuItem("設定", on_settings),
    )
    tray_icon = pystray.Icon("folderwatch", icon_image, "フォルダ見えるくん", menu)

    # --- タスクトレイ用スレッド起動 ---
    def tray_thread():
        tray_icon.run()
    threading.Thread(target=tray_thread, daemon=True).start()

    # --- Tkinterメインループ開始（ここでブロック） ---
    gui.root.mainloop()
    sys.exit()
    print("[main] アプリ終了")

# --- スクリプト直接実行時のみmain()を呼ぶ ---
if __name__ == "__main__":
    main()