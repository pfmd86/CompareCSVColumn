#!/usr/bin/env python3
"""Compare two CSV files by sorted content, optionally filtering by column names."""

import csv
import sys
import argparse
from pathlib import Path


def read_csv_column(filepath: str, column: str | None = None) -> set[str]:
    """Read a CSV file and return a set of values from the specified column (or all rows)."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    values = set()
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if column is not None:
            if reader.fieldnames and column not in reader.fieldnames:
                available = ", ".join(reader.fieldnames)
                raise ValueError(
                    f"Column '{column}' not found in {filepath}.\nAvailable columns: {available}"
                )
            for row in reader:
                val = row[column].strip()
                if val:
                    values.add(val)
        else:
            # No column specified: treat each row as a tuple of all values
            for row in reader:
                values.add(tuple(v.strip() for v in row.values()))
    return values


def compare_csv(
    file_a: str,
    file_b: str,
    col_a: str | None = None,
    col_b: str | None = None,
) -> dict:
    """
    Compare two CSV files.

    Returns a dict with:
      - only_in_a: values present in A but not B
      - only_in_b: values present in B but not A
      - in_both:   values present in both
      - match:     True if both sets are identical
    """
    set_a = read_csv_column(file_a, col_a)
    set_b = read_csv_column(file_b, col_b)

    only_a = sorted(str(v) for v in (set_a - set_b))
    only_b = sorted(str(v) for v in (set_b - set_a))
    both = sorted(str(v) for v in (set_a & set_b))

    return {
        "match": set_a == set_b,
        "only_in_a": only_a,
        "only_in_b": only_b,
        "in_both": both,
    }


def write_output_csv(values: list[str], filepath: Path, header: str) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([header])
        for v in values:
            writer.writerow([v])


def save_results(result: dict, file_a: str, file_b: str) -> None:
    out = Path("output")
    label_a = Path(file_a).stem
    label_b = Path(file_b).stem

    write_output_csv(result["only_in_a"], out / "onlyA.csv", f"only_in_{label_a}")
    write_output_csv(result["only_in_b"], out / "onlyB.csv", f"only_in_{label_b}")
    write_output_csv(result["in_both"],   out / "AandB.csv", "in_both")

    print(f"\n  Output written to {out.resolve()}/")
    print(f"    onlyA.csv  — {len(result['only_in_a'])} row(s)")
    print(f"    onlyB.csv  — {len(result['only_in_b'])} row(s)")
    print(f"    AandB.csv  — {len(result['in_both'])} row(s)")


def print_results(result: dict, file_a: str, file_b: str) -> None:
    sep = "-" * 60
    if result["match"]:
        print(f"\n✓ Files match — {len(result['in_both'])} identical value(s).")
    else:
        print(f"\n✗ Files differ.")

    if result["only_in_a"]:
        print(f"\n[Only in A: {file_a}]  ({len(result['only_in_a'])} value(s))")
        print(sep)
        for v in result["only_in_a"]:
            print(f"  {v}")

    if result["only_in_b"]:
        print(f"\n[Only in B: {file_b}]  ({len(result['only_in_b'])} value(s))")
        print(sep)
        for v in result["only_in_b"]:
            print(f"  {v}")

    if result["in_both"]:
        print(f"\n[In both]  ({len(result['in_both'])} value(s))")
        print(sep)
        for v in result["in_both"]:
            print(f"  {v}")


def list_columns(filepath: str) -> list[str]:
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or [])


def scan_csv_files(directory: Path = Path(".")) -> list[Path]:
    """Return all CSV files in the given directory, sorted by name."""
    return sorted(directory.glob("*.csv"))


def pick_file(label: str) -> str:
    """Let the user pick a CSV file by number from the current directory."""
    csv_files = scan_csv_files()
    if not csv_files:
        print("  No CSV files found in the current directory.")
        print("  Enter a full path manually:")
        while True:
            path = input(f"  File {label}: ").strip().strip('"')
            if Path(path).exists():
                return path
            print(f"    File not found: {path}")

    print(f"  CSV files found:")
    for i, f in enumerate(csv_files, 1):
        print(f"    [{i}] {f.name}")
    print(f"    [0] Enter path manually")

    while True:
        raw = input(f"  Pick file {label} (number): ").strip()
        if raw == "0":
            path = input(f"  File {label} path: ").strip().strip('"')
            if Path(path).exists():
                return path
            print(f"    File not found: {path}")
            continue
        if raw.isdigit() and 1 <= int(raw) <= len(csv_files):
            return str(csv_files[int(raw) - 1])
        print(f"    Enter a number between 0 and {len(csv_files)}.")


def pick_column(filepath: str, label: str) -> str | None:
    """Let the user pick a column by number from the file's header."""
    cols = list_columns(filepath)
    if not cols:
        return None

    print(f"\n  Columns in {label} ({Path(filepath).name}):")
    for i, col in enumerate(cols, 1):
        print(f"    [{i}] {col}")
    print(f"    [0] Full-row comparison (no column filter)")

    while True:
        raw = input(f"  Pick column for {label} (number): ").strip()
        if raw == "0":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(cols):
            return cols[int(raw) - 1]
        print(f"    Enter a number between 0 and {len(cols)}.")


def interactive_mode() -> None:
    print("=== CSV Comparator ===\n")
    file_a = pick_file("A")
    file_b = pick_file("B")
    col_a = pick_column(file_a, "A")
    col_b = pick_column(file_b, "B")

    result = compare_csv(file_a, file_b, col_a, col_b)
    print_results(result, file_a, file_b)
    save_results(result, file_a, file_b)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two CSV files by sorted content."
    )
    parser.add_argument("file_a", nargs="?", help="First CSV file")
    parser.add_argument("file_b", nargs="?", help="Second CSV file")
    parser.add_argument("--col-a", metavar="COLUMN", help="Column name in file A")
    parser.add_argument("--col-b", metavar="COLUMN", help="Column name in file B")
    parser.add_argument(
        "--col",
        metavar="COLUMN",
        help="Same column name for both files (shorthand)",
    )

    args = parser.parse_args()

    # Interactive mode when no files given
    if not args.file_a or not args.file_b:
        interactive_mode()
        return

    col_a = args.col_a or args.col
    col_b = args.col_b or args.col

    try:
        result = compare_csv(args.file_a, args.file_b, col_a, col_b)
        print_results(result, args.file_a, args.file_b)
        save_results(result, args.file_a, args.file_b)
        sys.exit(0 if result["match"] else 1)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
