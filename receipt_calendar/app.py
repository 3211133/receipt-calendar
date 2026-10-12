"""月カレンダーに領収書画像をドラッグ&ドロップして日付を割り当てるGUI。"""
from __future__ import annotations

import calendar
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import messagebox

from tkinterdnd2 import DND_FILES, TkinterDnD

from receipt_calendar.model import MonthReceipts

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
COLOR_EMPTY = "#ffffff"
COLOR_REGISTERED = "#c8e6c9"
COLOR_HOVER = "#fff59d"
COLOR_OUTSIDE = "#eeeeee"


class ReceiptCalendarApp:
    def __init__(self, root: tk.Tk, output_dir: Path) -> None:
        self.root = root
        self.output_dir = output_dir
        today = date.today()
        self.receipts = MonthReceipts(today.year, today.month, output_dir)

        root.title("領収書カレンダー")
        root.minsize(760, 520)

        header = tk.Frame(root)
        header.pack(fill="x", pady=6)
        tk.Button(header, text="◀", width=4, command=lambda: self.shift_month(-1)).pack(side="left", padx=8)
        self.title_label = tk.Label(header, font=("Meiryo", 14, "bold"))
        self.title_label.pack(side="left", expand=True)
        tk.Button(header, text="▶", width=4, command=lambda: self.shift_month(1)).pack(side="right", padx=8)

        self.grid = tk.Frame(root)
        self.grid.pack(fill="both", expand=True, padx=8)
        for col, name in enumerate(WEEKDAYS):
            tk.Label(self.grid, text=name, font=("Meiryo", 10, "bold")).grid(row=0, column=col, sticky="nsew")
            self.grid.columnconfigure(col, weight=1, uniform="col")

        self.cells: list[tk.Label] = []
        for row in range(6):
            self.grid.rowconfigure(row + 1, weight=1, uniform="row")
            for col in range(7):
                cell = tk.Label(
                    self.grid, relief="solid", borderwidth=1, anchor="nw", justify="left",
                    font=("Meiryo", 9), wraplength=100, padx=4, pady=2,
                )
                cell.grid(row=row + 1, column=col, sticky="nsew", padx=1, pady=1)
                cell.drop_target_register(DND_FILES)
                cell.dnd_bind("<<DropEnter>>", self._on_drop_enter)
                cell.dnd_bind("<<DropLeave>>", self._on_drop_leave)
                cell.dnd_bind("<<Drop>>", self._on_drop)
                cell.bind("<Button-3>", self._on_right_click)
                cell.bind("<Enter>", self._on_hover)
                self.cells.append(cell)

        self.status = tk.Label(root, anchor="w", relief="sunken", font=("Meiryo", 9))
        self.status.pack(fill="x", side="bottom")

        self.load_month()

    # --- 月の切り替えと描画 ---

    def shift_month(self, delta: int) -> None:
        index = self.receipts.year * 12 + (self.receipts.month - 1) + delta
        self.receipts = MonthReceipts(index // 12, index % 12 + 1, self.output_dir)
        self.load_month()

    def load_month(self) -> None:
        self.load_failed = False
        try:
            self.receipts.load()
        except Exception as e:  # 壊れたJSONでもGUIは起動させる。上書きで消さないよう編集は止める
            self.load_failed = True
            messagebox.showerror("読み込みエラー", f"{self.receipts.json_path}\n{e}\n\nこの月は編集できません。ファイルを直してから開き直してください。")
        self.title_label.config(text=f"{self.receipts.year}年 {self.receipts.month}月")
        self.redraw()

    def redraw(self) -> None:
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(self.receipts.year, self.receipts.month)
        days = [d for week in weeks for d in week]
        for i, cell in enumerate(self.cells):
            day = days[i] if i < len(days) else None
            cell.day = day if day and day.month == self.receipts.month else None
            self._paint(cell)
        count = len(self.receipts.entries)
        self.status.config(text=f"登録 {count} 件  →  {self.receipts.json_path}")

    def _paint(self, cell: tk.Label) -> None:
        day = cell.day
        if day is None:
            cell.config(text="", bg=COLOR_OUTSIDE)
            return
        path = self.receipts.get(day)
        if path is None:
            cell.config(text=str(day.day), bg=COLOR_EMPTY)
        else:
            cell.config(text=f"{day.day}\n{path.name}", bg=COLOR_REGISTERED)

    # --- イベント ---

    def _on_drop_enter(self, event):
        if event.widget.day is not None:
            event.widget.config(bg=COLOR_HOVER)
        return event.action

    def _on_drop_leave(self, event):
        self._paint(event.widget)
        return event.action

    def _on_drop(self, event):
        cell = event.widget
        self._paint(cell)
        day = cell.day
        if day is None or self.load_failed:
            return event.action
        files = self.root.tk.splitlist(event.data)
        if len(files) != 1:
            messagebox.showerror("登録エラー", "1日に登録できるファイルは1つです。1枚ずつドロップしてください。")
            return event.action
        new_path = Path(files[0])
        if not new_path.is_file():
            messagebox.showerror("登録エラー", f"ファイルではありません。\n{new_path}")
            return event.action
        current = self.receipts.get(day)
        if current is not None and current != new_path:
            if not messagebox.askyesno(
                "上書き確認", f"{day} には登録済みです。\n\n現在: {current.name}\n新規: {new_path.name}\n\n上書きしますか？"
            ):
                return event.action
        self.receipts.assign(day, new_path)
        self._save()
        return event.action

    def _on_right_click(self, event) -> None:
        day = event.widget.day
        path = self.receipts.get(day) if day else None
        if path is None or self.load_failed:
            return
        if messagebox.askyesno("登録解除", f"{day} の登録を解除しますか？\n\n{path.name}"):
            self.receipts.remove(day)
            self._save()

    def _on_hover(self, event) -> None:
        day = event.widget.day
        path = self.receipts.get(day) if day else None
        if path is not None:
            self.status.config(text=f"{day}: {path}")
        else:
            self.status.config(text=f"登録 {len(self.receipts.entries)} 件  →  {self.receipts.json_path}")

    def _save(self) -> None:
        try:
            self.receipts.save()
        except OSError as e:
            messagebox.showerror("保存エラー", str(e))
        self.redraw()


def main() -> None:
    root = TkinterDnD.Tk()
    ReceiptCalendarApp(root, Path.cwd() / "output")
    root.mainloop()
