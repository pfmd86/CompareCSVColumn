#!/usr/bin/env python3
"""Unit tests for compare_csv.py"""

import csv
import pytest
from pathlib import Path
from unittest.mock import patch

from compare_csv import (
    read_csv_column,
    compare_csv,
    write_output_csv,
    save_results,
    list_columns,
    scan_csv_files,
    pick_file,
    pick_column,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def read_csv_values(path: Path, column: str) -> list[str]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row[column] for row in reader]


# ---------------------------------------------------------------------------
# read_csv_column
# ---------------------------------------------------------------------------

class TestReadCsvColumn:
    def test_reads_single_column(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"id": "A"}, {"id": "B"}, {"id": "C"}])
        assert read_csv_column(str(f), "id") == {"A", "B", "C"}

    def test_strips_whitespace(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"id": " X "}, {"id": " Y"}])
        assert read_csv_column(str(f), "id") == {"X", "Y"}

    def test_skips_empty_values(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"id": "A"}, {"id": ""}, {"id": "B"}])
        assert read_csv_column(str(f), "id") == {"A", "B"}

    def test_full_row_mode(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}])
        result = read_csv_column(str(f))
        assert ("1", "Alice") in result
        assert ("2", "Bob") in result

    def test_raises_for_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_csv_column(str(tmp_path / "missing.csv"), "id")

    def test_raises_for_missing_column(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"id": "A"}])
        with pytest.raises(ValueError, match="nope"):
            read_csv_column(str(f), "nope")

    def test_deduplicates_values(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"id": "A"}, {"id": "A"}, {"id": "B"}])
        assert read_csv_column(str(f), "id") == {"A", "B"}

    def test_utf8_bom_handling(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_bytes(b"\xef\xbb\xbfid\r\nX\r\nY\r\n")
        assert read_csv_column(str(f), "id") == {"X", "Y"}


# ---------------------------------------------------------------------------
# compare_csv
# ---------------------------------------------------------------------------

class TestCompareCsv:
    def test_identical_files_match(self, tmp_path):
        rows = [{"id": "1"}, {"id": "2"}]
        a = tmp_path / "a.csv"
        b = tmp_path / "b.csv"
        write_csv(a, rows)
        write_csv(b, rows)
        result = compare_csv(str(a), str(b), "id", "id")
        assert result["match"] is True
        assert result["only_in_a"] == []
        assert result["only_in_b"] == []
        assert result["in_both"] == ["1", "2"]

    def test_disjoint_files(self, tmp_path):
        a = tmp_path / "a.csv"
        b = tmp_path / "b.csv"
        write_csv(a, [{"id": "A"}])
        write_csv(b, [{"id": "B"}])
        result = compare_csv(str(a), str(b), "id", "id")
        assert result["match"] is False
        assert result["only_in_a"] == ["A"]
        assert result["only_in_b"] == ["B"]
        assert result["in_both"] == []

    def test_partial_overlap(self, tmp_path):
        a = tmp_path / "a.csv"
        b = tmp_path / "b.csv"
        write_csv(a, [{"id": "1"}, {"id": "2"}, {"id": "3"}])
        write_csv(b, [{"id": "2"}, {"id": "3"}, {"id": "4"}])
        result = compare_csv(str(a), str(b), "id", "id")
        assert result["only_in_a"] == ["1"]
        assert result["only_in_b"] == ["4"]
        assert result["in_both"] == ["2", "3"]

    def test_different_column_names(self, tmp_path):
        a = tmp_path / "a.csv"
        b = tmp_path / "b.csv"
        write_csv(a, [{"case_id": "X"}, {"case_id": "Y"}])
        write_csv(b, [{"number": "Y"}, {"number": "Z"}])
        result = compare_csv(str(a), str(b), "case_id", "number")
        assert result["only_in_a"] == ["X"]
        assert result["only_in_b"] == ["Z"]
        assert result["in_both"] == ["Y"]

    def test_results_are_sorted(self, tmp_path):
        a = tmp_path / "a.csv"
        b = tmp_path / "b.csv"
        write_csv(a, [{"id": "C"}, {"id": "A"}, {"id": "B"}])
        write_csv(b, [{"id": "A"}])
        result = compare_csv(str(a), str(b), "id", "id")
        assert result["only_in_a"] == ["B", "C"]

    def test_no_column_full_row(self, tmp_path):
        a = tmp_path / "a.csv"
        b = tmp_path / "b.csv"
        write_csv(a, [{"x": "1", "y": "a"}])
        write_csv(b, [{"x": "1", "y": "a"}])
        result = compare_csv(str(a), str(b))
        assert result["match"] is True

    def test_empty_files_match(self, tmp_path):
        a = tmp_path / "a.csv"
        b = tmp_path / "b.csv"
        write_csv(a, [{"id": ""}])
        write_csv(b, [{"id": ""}])
        result = compare_csv(str(a), str(b), "id", "id")
        assert result["match"] is True
        assert result["in_both"] == []


# ---------------------------------------------------------------------------
# write_output_csv
# ---------------------------------------------------------------------------

class TestWriteOutputCsv:
    def test_creates_file_with_header_and_rows(self, tmp_path):
        out = tmp_path / "sub" / "out.csv"
        write_output_csv(["alpha", "beta"], out, "my_col")
        values = read_csv_values(out, "my_col")
        assert values == ["alpha", "beta"]

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "a" / "b" / "c.csv"
        write_output_csv([], out, "h")
        assert out.exists()

    def test_empty_values(self, tmp_path):
        out = tmp_path / "empty.csv"
        write_output_csv([], out, "col")
        values = read_csv_values(out, "col")
        assert values == []

    def test_overwrites_existing_file(self, tmp_path):
        out = tmp_path / "out.csv"
        write_output_csv(["old"], out, "col")
        write_output_csv(["new"], out, "col")
        assert read_csv_values(out, "col") == ["new"]


# ---------------------------------------------------------------------------
# save_results
# ---------------------------------------------------------------------------

class TestSaveResults:
    def _result(self):
        return {
            "match": False,
            "only_in_a": ["A1", "A2"],
            "only_in_b": ["B1"],
            "in_both": ["C1", "C2", "C3"],
        }

    def test_creates_three_output_files(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        save_results(self._result(), "fileA.csv", "fileB.csv")
        assert (tmp_path / "output" / "onlyA.csv").exists()
        assert (tmp_path / "output" / "onlyB.csv").exists()
        assert (tmp_path / "output" / "AandB.csv").exists()

    def test_onlyA_content(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        save_results(self._result(), "fileA.csv", "fileB.csv")
        vals = read_csv_values(tmp_path / "output" / "onlyA.csv", "only_in_fileA")
        assert vals == ["A1", "A2"]

    def test_onlyB_content(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        save_results(self._result(), "fileA.csv", "fileB.csv")
        vals = read_csv_values(tmp_path / "output" / "onlyB.csv", "only_in_fileB")
        assert vals == ["B1"]

    def test_AandB_content(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        save_results(self._result(), "fileA.csv", "fileB.csv")
        vals = read_csv_values(tmp_path / "output" / "AandB.csv", "in_both")
        assert vals == ["C1", "C2", "C3"]

    def test_prints_summary(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        save_results(self._result(), "fileA.csv", "fileB.csv")
        out = capsys.readouterr().out
        assert "onlyA.csv" in out
        assert "onlyB.csv" in out
        assert "AandB.csv" in out


# ---------------------------------------------------------------------------
# list_columns
# ---------------------------------------------------------------------------

class TestListColumns:
    def test_returns_header_names(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"a": "1", "b": "2", "c": "3"}])
        assert list_columns(str(f)) == ["a", "b", "c"]

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("")
        assert list_columns(str(f)) == []


# ---------------------------------------------------------------------------
# scan_csv_files
# ---------------------------------------------------------------------------

class TestScanCsvFiles:
    def test_finds_csv_files(self, tmp_path):
        (tmp_path / "a.csv").touch()
        (tmp_path / "b.csv").touch()
        (tmp_path / "note.txt").touch()
        found = scan_csv_files(tmp_path)
        assert len(found) == 2
        assert all(f.suffix == ".csv" for f in found)

    def test_returns_sorted(self, tmp_path):
        (tmp_path / "z.csv").touch()
        (tmp_path / "a.csv").touch()
        (tmp_path / "m.csv").touch()
        found = scan_csv_files(tmp_path)
        assert [f.name for f in found] == ["a.csv", "m.csv", "z.csv"]

    def test_empty_directory(self, tmp_path):
        assert scan_csv_files(tmp_path) == []


# ---------------------------------------------------------------------------
# pick_file (interactive)
# ---------------------------------------------------------------------------

class TestPickFile:
    def test_picks_by_number(self, tmp_path, monkeypatch):
        (tmp_path / "one.csv").touch()
        (tmp_path / "two.csv").touch()
        monkeypatch.chdir(tmp_path)
        with patch("builtins.input", return_value="1"):
            result = pick_file("A")
        assert Path(result).name == "one.csv"

    def test_manual_path_fallback(self, tmp_path, monkeypatch):
        manual = tmp_path / "manual.csv"
        manual.touch()
        monkeypatch.chdir(tmp_path)
        # First input: "0" to trigger manual; second: the actual path
        with patch("builtins.input", side_effect=["0", str(manual)]):
            result = pick_file("A")
        assert result == str(manual)

    def test_invalid_then_valid(self, tmp_path, monkeypatch):
        (tmp_path / "file.csv").touch()
        monkeypatch.chdir(tmp_path)
        with patch("builtins.input", side_effect=["99", "abc", "1"]):
            result = pick_file("A")
        assert Path(result).name == "file.csv"

    def test_no_csvs_prompts_manual(self, tmp_path, monkeypatch):
        # manual file lives outside the empty work dir so scan finds nothing
        manual = tmp_path / "elsewhere.csv"
        manual.touch()
        empty_dir = tmp_path / "workdir"
        empty_dir.mkdir()
        monkeypatch.chdir(empty_dir)
        with patch("builtins.input", return_value=str(manual)):
            result = pick_file("A")
        assert result == str(manual)


# ---------------------------------------------------------------------------
# pick_column (interactive)
# ---------------------------------------------------------------------------

class TestPickColumn:
    def test_picks_column_by_number(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"id": "1", "name": "Alice"}])
        with patch("builtins.input", return_value="2"):
            result = pick_column(str(f), "A")
        assert result == "name"

    def test_zero_returns_none(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"id": "1"}])
        with patch("builtins.input", return_value="0"):
            result = pick_column(str(f), "A")
        assert result is None

    def test_no_columns_returns_none(self, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("")
        result = pick_column(str(f), "A")
        assert result is None

    def test_invalid_then_valid(self, tmp_path):
        f = tmp_path / "data.csv"
        write_csv(f, [{"id": "1", "name": "X"}])
        with patch("builtins.input", side_effect=["99", "abc", "1"]):
            result = pick_column(str(f), "A")
        assert result == "id"
