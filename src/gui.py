import os
import tkinter as tk
from tkinter import ttk, filedialog
try:
	from win11toast import toast as _toast_impl
except Exception:
	def _toast_impl(title, msg, duration="short"):
		print(f"TOAST: {title} - {msg}")

from typing import Any

def toast(title, msg, duration="short") -> None:
	"""ラッパー: 実装の戻り値を破棄して常に None を返す。

	型チェックで戻り値が期待値と異なる場合に備えるためのアダプタ。
	"""
	try:
		# 実装を呼び出して副作用（通知）を発生させる。
		# 戻り値は型チェック上不要なので破棄する。
		_ = _toast_impl(title, msg, duration)
	except Exception:
		# 実行時エラーはログに出して無視する
		try:
			print(f"TOAST failed: {title} - {msg}")
		except Exception:
			pass
	return None

from .watcher import FolderWatcher


class MinimalGUI:
	"""
	最小構成のTkウィンドウ。タスクトレイ操作からの監視制御と設定を提供します。
	"""
	def __init__(self, config, exit_callback):
		"""GUI を初期化する。

		引数:
		- config: 設定データ
		- exit_callback: アプリ終了時に呼び出されるコールバック関数。
		"""
		self.root = tk.Tk()
		self.root.title("フォルダ見えるくん")
		self.root.geometry("1x1+0+0")
		self.root.withdraw()

		username = os.environ.get("USERNAME", "")
		self.target_folder = config.get("watch_folder", os.path.join("C:\\Users", username, "Downloads"))
		self.target_name = config.get("target_name", "")
		self.target_ext =  config.get("target_ext", "")
		self.watcher = None

		def _notify(title, msg):
			"""通知を表示する。GUIスレッドで実行されるようにスケジュールする。"""
			self.root.after(0, toast, title, msg, "short")

		self.notifier = _notify
		self.exit_callback = exit_callback
		self.root.protocol("WM_DELETE_WINDOW", self.stop_and_exit)
		print("[MinimalGUI] 初期化: 監視対象", self.target_folder)

	def start_watching(self):
		"""監視スレッドを開始する。

		既に監視中であれば何もしない代わりに通知を行います。
		"""
		if self.watcher is None or not self.watcher.is_alive():
			print("[MinimalGUI] 監視スレッド起動")
			self.watcher = FolderWatcher(
				self.target_folder, self.target_name, self.target_ext, self.notifier
			)
			self.watcher.start()
			toast('監視を開始しました', self.target_folder, duration="short")
		else:
			toast('既に監視中です', '', duration="short")
			print("[MinimalGUI] 既に監視中")

	def stop_watching(self):
		"""監視スレッドを停止する。

		監視中であればスレッドに停止を指示して結合(join)します。
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
		"""設定ダイアログを表示し、監視対象やフィルタを編集する。

		ユーザが設定を変更すると、監視を再起動して新設定を反映します。
		"""
		def browse_folder():
			"""フォルダ選択ダイアログを開き、選択されたフォルダを設定に反映する。"""
			folder_selected = filedialog.askdirectory()
			if folder_selected:
				folder_var.set(folder_selected)

		setting_win = tk.Toplevel(self.root)
		setting_win.title("設定")
		setting_win.geometry("400x200")
		setting_win.resizable(False, False)

		folder_var = tk.StringVar(value=self.target_folder)
		name_var = tk.StringVar(value=self.target_name)
		ext_var = tk.StringVar(value=self.target_ext)

		lbl_folder = tk.Label(setting_win, text="監視対象フォルダ:")
		lbl_folder.grid(row=0, column=0, sticky="w", padx=10, pady=10)
		folder_entry = tk.Entry(setting_win, textvariable=folder_var, width=35)
		folder_entry.grid(row=0, column=1, padx=2)
		folder_button = tk.Button(setting_win, text="参照", command=browse_folder)
		folder_button.grid(row=0, column=2, padx=2)

		lbl_name = tk.Label(
			setting_win,
			text="ファイル名(部分一致):",
		)
		lbl_name.grid(row=1, column=0, sticky="w", padx=10, pady=10)
		name_entry = tk.Entry(setting_win, textvariable=name_var)
		name_entry.grid(row=1, column=1, columnspan=2, padx=2, sticky="we")

		lbl_ext = tk.Label(setting_win, text="拡張子:")
		lbl_ext.grid(row=2, column=0, sticky="w", padx=10, pady=10)
		ext_entry = tk.Entry(setting_win, textvariable=ext_var)
		ext_entry.grid(row=2, column=1, columnspan=2, padx=2, sticky="we")

		def apply_settings():
			"""ユーザが設定を適用したときの処理。新しい設定を保存し、監視を再起動して反映させる。"""
			self.target_folder = folder_var.get()
			self.target_name = name_var.get()
			self.target_ext = ext_var.get()
			self.stop_watching()
			self.start_watching()
			message = f"新: {self.target_folder}\n{self.target_name}{self.target_ext}"
			toast('設定を反映し再監視中', message, duration="short")
			print("[MinimalGUI] 設定反映:", self.target_folder, self.target_name, self.target_ext)
			setting_win.destroy()

		button_frame = tk.Frame(setting_win)
		button_frame.grid(row=3, column=0, columnspan=3, pady=15)
		btn_ok = ttk.Button(button_frame, text="OK", command=apply_settings)
		btn_ok.pack(side="left", padx=5)
		btn_cancel = ttk.Button(button_frame, text="キャンセル", command=setting_win.destroy)
		btn_cancel.pack(side="left", padx=5)

		setting_win.grab_set()

	def stop_and_exit(self):
		"""監視を停止して GUI を終了し、終了コールバックを呼び出す。"""
		self.stop_watching()
		self.root.quit()
		try:
			self.exit_callback()
		except Exception:
			pass
		print("[MinimalGUI] 完全終了")

