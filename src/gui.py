import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog

from typing import Any, Callable, Optional
import json
import sys

def _default_toast(title: str, msg: str, duration: str = "short") -> None:
	print(f"TOAST: {title} - {msg}")

_toast_impl: Callable[..., Any] = _default_toast
try:
	from win11toast import toast as _toast_impl  # type: ignore
except Exception:
	# keep default
	pass

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
	def __init__(self, exit_callback):
		"""GUI を初期化する。

		引数:
		- exit_callback: アプリ終了時に呼び出されるコールバック関数。
		"""
		self.root = tk.Tk()
		self.root.title("フォルダ見えるくん")
		self.root.geometry("1x1+0+0")
		self.root.withdraw()

		username = os.environ.get("USERNAME", "user")
		self.folder = rf"C:\Users\{username}"
		self.target_name = '作業報告書'
		self.target_ext = '.xlsx'
		self.watcher = None
 		# 現在表示中の設定ウィンドウ参照（多重表示防止用）
		self._settings_win = None

		def _notify(title, msg):
			self.root.after(0, toast, title, msg, "short")

		self.notifier = _notify
		self.exit_callback = exit_callback
		self.root.protocol("WM_DELETE_WINDOW", self.stop_and_exit)
		print("[MinimalGUI] 初期化: 監視対象", self.folder)

	def _config_path(self) -> str:
		"""設定ファイルのパスを返す。

		frozen 実行時は実行ファイルのディレクトリ、通常はプロジェクトルート（src の親）を基準とする。
		"""
		if getattr(sys, "frozen", False):
			base = os.path.dirname(sys.executable)
		else:
			# gui.py は src 配下にあるため、親ディレクトリをプロジェクトルートと見なす
			base = os.path.dirname(os.path.dirname(__file__))
		return os.path.join(base, "config.json")

	def start_watching(self):
		"""監視スレッドを開始する。

		既に監視中であれば何もしない代わりに通知を行います。
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

	def stop_watching(self, wait: bool = True, final_toast: Optional[str] = None):
		"""監視スレッドを停止する。

		監視中であればスレッドに停止を指示します。
		`wait=True`（デフォルト）の場合は終了まで待機して結合(join)します。
		`wait=False` の場合は停止信号のみ送って即座に戻り、GUI をブロックしません。

		引数:
		- wait: 終了まで待つかどうか
		- final_toast: 終了時に表示するトーストのタイトル。None の場合は従来の文言を使う。
		"""
		if self.watcher is None or not self.watcher.is_alive():
			toast('監視は停止中です', '', duration="short")
			print("[MinimalGUI] 監視は元々停止中")
			return

		print("[MinimalGUI] 監視スレッド停止" + ("(非同期)" if not wait else ""))
		# 停止信号を送る
		try:
			self.watcher.stop()
		except Exception:
			pass

		if wait:
			# 終了まで待って結合する（GUI 側で呼ぶとブロックするので注意）
			try:
				self.watcher.join()
			except Exception:
				pass
			self.watcher = None
			# 設定更新時など、カスタムメッセージがあればそれを表示する
			if final_toast is None:
				toast('監視を中断しました', '', duration="short")
			else:
				toast(final_toast, '', duration="short")
		else:
			# 非同期停止: watcher の参照は残しておく（別スレッドで停止処理が続行される）
			pass


	def show_settings(self):
		"""設定ダイアログを表示し、監視対象やフィルタを編集する。

		ユーザが設定を変更すると、監視を再起動して新設定を反映します。
		"""
		def browse_folder():
			folder_selected = filedialog.askdirectory()
			if folder_selected:
				folder_var.set(folder_selected)

		# 既に設定ウィンドウが開かれていればそれを最前面にする
		if self._settings_win is not None and self._settings_win.winfo_exists():
			try:
				win = self._settings_win
				win.deiconify()
				win.lift()
				win.attributes("-topmost", True)
				win.after(100, lambda w=win: w.attributes("-topmost", False))
				win.focus_force()
			except Exception:
				pass
			return

		# 設定ウィンドウを新規作成する
		setting_win = tk.Toplevel(self.root)
		self._settings_win = setting_win
		setting_win.title("設定")
		setting_win.geometry("400x200")
		setting_win.resizable(False, False)

		folder_var = tk.StringVar(value=self.folder)
		name_var = tk.StringVar(value=self.target_name)
		ext_var = tk.StringVar(value=self.target_ext)

		# 監視対象フォルダ
		lbl_folder = tk.Label(setting_win, text="監視対象フォルダ:")
		lbl_folder.grid(row=0, column=0, sticky="w", padx=10, pady=10)
		folder_entry = tk.Entry(setting_win, textvariable=folder_var, width=35)
		folder_entry.grid(row=0, column=1, padx=2)
		folder_button = tk.Button(setting_win, text="参照", command=browse_folder)
		folder_button.grid(row=0, column=2, padx=2)

		# 監視対象のファイル名（部分一致）
		lbl_name = tk.Label(
			setting_win,
			text="ファイル名(部分一致):",
		)
		lbl_name.grid(row=1, column=0, sticky="w", padx=10, pady=10)
		name_entry = tk.Entry(setting_win, textvariable=name_var)
		name_entry.grid(row=1, column=1, columnspan=2, padx=2, sticky="we")

		# 監視対象の拡張子
		lbl_ext = tk.Label(setting_win, text="拡張子:")
		lbl_ext.grid(row=2, column=0, sticky="w", padx=10, pady=10)
		ext_entry = tk.Entry(setting_win, textvariable=ext_var)
		ext_entry.grid(row=2, column=1, columnspan=2, padx=2, sticky="we")

		def apply_settings():
			self.folder = folder_var.get()
			self.target_name = name_var.get()
			self.target_ext = ext_var.get()

			# 設定を config.json に書き込む（失敗しても処理を続行）
			try:
				cfg = {
					"watch_folder": self.folder,
					"target_name": self.target_name,
					"target_ext": self.target_ext,
				}
				with open(self._config_path(), "w", encoding="utf-8") as f:
					json.dump(cfg, f, ensure_ascii=False, indent=4)
			except Exception:
				try:
					print("[MinimalGUI] 設定ファイルへの保存に失敗しました")
				except Exception:
					pass
			# 監視の再起動は重い可能性があるため別スレッドで実行して GUI をブロックしない
			def _restart():
				try:
					self.stop_watching(wait=True, final_toast='設定を更新しました')
				except Exception:
					pass
				try:
					self.start_watching()
				except Exception:
					pass
			threading.Thread(target=_restart, daemon=True).start()
			message = f"新: {self.folder}\n{self.target_name}{self.target_ext}"
			toast('設定を反映し再監視中', message, duration="short")
			print("[MinimalGUI] 設定反映:", self.folder, self.target_name, self.target_ext)
			# 閉じる前に参照をクリア
			try:
				self._settings_win = None
			except Exception:
				pass
			setting_win.destroy()

		button_frame = tk.Frame(setting_win)
		button_frame.grid(row=3, column=0, columnspan=3, pady=15)
		btn_ok = ttk.Button(button_frame, text="OK", command=apply_settings)
		btn_ok.pack(side="left", padx=5)
		def _close_settings():
			try:
				self._settings_win = None
			except Exception:
				pass
			setting_win.destroy()

		btn_cancel = ttk.Button(button_frame, text="キャンセル", command=_close_settings)
		btn_cancel.pack(side="left", padx=5)

		# ウィンドウが閉じられたときに参照をクリア
		def _on_close():
			try:
				self._settings_win = None
			except Exception:
				pass
			setting_win.destroy()

		setting_win.protocol("WM_DELETE_WINDOW", _on_close)
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

