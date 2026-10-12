"""月ごとの領収書割り当て（日付 -> ファイルパス）とTOML入出力。GUI非依存。"""
from __future__ import annotations

import tomllib
from datetime import date
from pathlib import Path

import tomli_w


class MonthReceipts:
    def __init__(self, year: int, month: int, output_dir: Path) -> None:
        self.year = year
        self.month = month
        self.output_dir = Path(output_dir)
        self.entries: dict[date, Path] = {}

    @property
    def toml_path(self) -> Path:
        return self.output_dir / f"receipts_{self.year:04d}-{self.month:02d}.toml"

    def get(self, day: date) -> Path | None:
        return self.entries.get(day)

    def assign(self, day: date, path: Path) -> None:
        if (day.year, day.month) != (self.year, self.month):
            raise ValueError(f"{day} は {self.year}-{self.month:02d} の日付ではありません")
        self.entries[day] = Path(path)

    def remove(self, day: date) -> None:
        self.entries.pop(day, None)

    def save(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "receipts": {
                d.isoformat(): str(p) for d, p in sorted(self.entries.items())
            }
        }
        self.toml_path.write_text(tomli_w.dumps(data), encoding="utf-8")

    def load(self) -> None:
        self.entries.clear()
        if not self.toml_path.exists():
            return
        data = tomllib.loads(self.toml_path.read_text(encoding="utf-8"))
        for key, value in data.get("receipts", {}).items():
            self.assign(date.fromisoformat(key), Path(value))
