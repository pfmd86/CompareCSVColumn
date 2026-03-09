# CompareCSVColumn

Compare two CSV files by sorted content and identify which values are only in file A, only in file B, or present in both.

## Features

- Compare a specific column from each file, or compare full rows
- Column names can differ between files
- Sorted, deduplicated output
- Saves results to `output/onlyA.csv`, `output/onlyB.csv`, `output/AandB.csv`
- CLI-ready with interactive fallback when called without arguments

## Requirements

Python 3.10+ (uses `str | None` union syntax). No third-party runtime dependencies.

Install test dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Interactive mode

Run without arguments. The script scans the current directory for CSV files and lets you pick by number:

```
python compare_csv.py
```

```
=== CSV Comparator ===

  CSV files found:
    [1] export_2024.csv
    [2] export_2025.csv
    [0] Enter path manually
  Pick file A (number): 1

  Columns in A (export_2024.csv):
    [1] Id
    [2] CaseNumber
    [3] Priority
    [0] Full-row comparison (no column filter)
  Pick column for A (number): 1
```

### CLI mode

```bash
# Compare the same column in both files
python compare_csv.py a.csv b.csv --col Id

# Use different column names per file
python compare_csv.py a.csv b.csv --col-a CaseId --col-b Number

# Compare full rows (no column filter)
python compare_csv.py a.csv b.csv
```

### Options

| Argument | Description |
|---|---|
| `file_a` | First CSV file |
| `file_b` | Second CSV file |
| `--col COLUMN` | Same column name for both files |
| `--col-a COLUMN` | Column name in file A |
| `--col-b COLUMN` | Column name in file B |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Files match |
| `1` | Files differ |
| `2` | Error (file not found, column not found) |

## Output

After every run an `output/` folder is created in the current directory:

| File | Content |
|---|---|
| `onlyA.csv` | Values present in A but not B |
| `onlyB.csv` | Values present in B but not A |
| `AandB.csv` | Values present in both |

Each file has a single column. The header is derived from the source file stem (e.g. `only_in_export_2024`).

## Running the tests

```bash
python -m pytest test_compare_csv.py -v
```

The test suite covers all public functions using temporary files and `unittest.mock` — no real CSV files required.

| Test class | What it covers |
|---|---|
| `TestReadCsvColumn` | Column reading, whitespace, empty values, BOM, deduplication, error cases |
| `TestCompareCsv` | Identical, disjoint, overlapping, different column names, sorted output |
| `TestWriteOutputCsv` | File creation, parent dirs, overwrite, empty input |
| `TestSaveResults` | All three output files, correct content, printed summary |
| `TestListColumns` | Header parsing, empty file |
| `TestScanCsvFiles` | Discovery, sorting, empty directory |
| `TestPickFile` | Number selection, manual path fallback (empty dir), invalid input recovery, no-CSVs manual prompt |
| `TestPickColumn` | Number selection, full-row option (`0`), no-header fallback |
