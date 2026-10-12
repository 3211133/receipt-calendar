from datetime import date
from pathlib import Path

import pytest

from receipt_calendar.model import MonthReceipts


def test_assign_overwrite_remove(tmp_path):
    m = MonthReceipts(2026, 10, tmp_path)
    d = date(2026, 10, 1)
    m.assign(d, Path("a.jpg"))
    m.assign(d, Path("b.jpg"))
    assert m.get(d) == Path("b.jpg")
    m.remove(d)
    assert m.get(d) is None


def test_assign_rejects_other_month(tmp_path):
    m = MonthReceipts(2026, 10, tmp_path)
    with pytest.raises(ValueError):
        m.assign(date(2026, 11, 1), Path("a.jpg"))


def test_toml_roundtrip(tmp_path):
    m = MonthReceipts(2026, 10, tmp_path / "output")
    p1 = Path(r"C:\Users\テスト\My Pictures\IMG_20261003_081522.jpg")
    p2 = Path(r"C:\it's\IMG_2.jpg")
    m.assign(date(2026, 10, 2), p2)
    m.assign(date(2026, 10, 1), p1)
    m.save()

    text = m.toml_path.read_text(encoding="utf-8")
    assert m.toml_path.name == "receipts_2026-10.toml"
    assert text.index("2026-10-01") < text.index("2026-10-02")

    loaded = MonthReceipts(2026, 10, tmp_path / "output")
    loaded.load()
    assert loaded.entries == {date(2026, 10, 1): p1, date(2026, 10, 2): p2}


def test_load_missing_file(tmp_path):
    m = MonthReceipts(2026, 10, tmp_path)
    m.load()
    assert m.entries == {}
