#!/usr/bin/env python3
"""Merge and filter literature CSV files for abstract extraction workflows."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Iterable


GENERATED_FILE_NAMES = {
    "filtered_articles.csv",
    "extraction_worklist.csv",
    "final_articles_with_dimensions.csv",
    "dimension_original_variables.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read all CSV files in a folder, apply optional filters, and write extraction work files."
    )
    parser.add_argument("--input-folder", required=True, help="Folder containing source CSV files.")
    parser.add_argument("--output-folder", default="", help="Folder where filtered outputs will be written.")
    parser.add_argument("--inspect-only", action="store_true", help="Only inspect CSV headers and suggest columns.")
    parser.add_argument("--abstract-column", default="", help="Column containing abstracts.")
    parser.add_argument("--language-column", default="", help="Optional language column.")
    parser.add_argument("--language-keep", default="", help="Language values to keep, separated by |, ;, or comma.")
    parser.add_argument("--year-column", default="", help="Optional year column.")
    parser.add_argument("--year-start", type=int, default=None, help="Inclusive start year.")
    parser.add_argument("--year-end", type=int, default=None, help="Inclusive end year.")
    parser.add_argument("--journal-column", default="", help="Optional journal or source-title column.")
    parser.add_argument("--journal-keep", default="", help="Journal values to keep, separated by | or ;.")
    parser.add_argument("--journal-exclude", default="", help="Journal values to exclude, separated by | or ;.")
    parser.add_argument("--encoding", default="auto", help="CSV encoding, or auto. Default: auto.")
    parser.add_argument("--filtered-name", default="filtered_articles.csv", help="Filtered article CSV file name.")
    parser.add_argument("--worklist-name", default="extraction_worklist.csv", help="Extraction worklist CSV file name.")
    parser.add_argument("--metadata-name", default="", help="Optional metadata JSON file name.")
    parser.add_argument("--inspect-name", default="", help="Optional column inspection JSON file name.")
    return parser.parse_args()


def split_values(raw: str) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[|;,]", raw) if part.strip()]


def norm_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm_key(value: object) -> str:
    return norm_text(value).casefold()


def compact_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", norm_key(value))


def classify_columns(columns: Iterable[str]) -> dict[str, list[str]]:
    candidates = {
        "abstract": [],
        "language": [],
        "year": [],
        "journal": [],
    }
    for column in columns:
        key = compact_key(column)
        if key in {"abstract", "ab", "summary"} or "abstract" in key:
            candidates["abstract"].append(column)
        if key in {"language", "lang", "documentlanguage"} or "language" in key:
            candidates["language"].append(column)
        if key in {"year", "publicationyear", "pubyear"} or key.endswith("year"):
            candidates["year"].append(column)
        if any(token in key for token in ("journal", "sourcetitle", "publicationname", "source", "periodical")):
            candidates["journal"].append(column)
    return candidates


def parse_year(value: object) -> int | None:
    text = norm_text(value)
    if not text:
        return None
    match = re.search(r"\b(18|19|20|21)\d{2}\b", text)
    if not match:
        return None
    return int(match.group(0))


def open_csv(path: Path, encoding: str):
    if encoding != "auto":
        return path.open("r", newline="", encoding=encoding)
    for candidate in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            handle = path.open("r", newline="", encoding=candidate)
            handle.read(4096)
            handle.seek(0)
            return handle
        except UnicodeDecodeError:
            continue
    return path.open("r", newline="", encoding="utf-8", errors="replace")


def list_csv_files(input_folder: Path) -> list[Path]:
    files = []
    for path in sorted(input_folder.glob("*.csv"), key=lambda p: p.name.casefold()):
        if path.name in GENERATED_FILE_NAMES:
            continue
        files.append(path)
    return files


def update_field_order(field_order: list[str], fieldnames: Iterable[str] | None) -> None:
    for field in fieldnames or []:
        if field not in field_order:
            field_order.append(field)


def inspect_headers(csv_files: list[Path], encoding: str) -> dict[str, object]:
    all_columns: list[str] = []
    by_file: dict[str, list[str]] = {}
    row_counts: dict[str, int] = {}
    sample_values: dict[str, list[str]] = {}
    value_counts: dict[str, dict[str, int]] = {}
    year_values: dict[str, list[int]] = {}

    for csv_file in csv_files:
        with open_csv(csv_file, encoding) as handle:
            reader = csv.DictReader(handle)
            fields = list(reader.fieldnames or [])
            by_file[csv_file.name] = fields
            update_field_order(all_columns, fields)
            count = 0
            for row in reader:
                count += 1
                for field in fields:
                    value = norm_text(row.get(field, ""))
                    if value and len(sample_values.get(field, [])) < 8 and value not in sample_values.get(field, []):
                        sample_values.setdefault(field, []).append(value)
                    if value:
                        value_counts.setdefault(field, {})
                        value_counts[field][value] = value_counts[field].get(value, 0) + 1
                    year = parse_year(value)
                    if year is not None:
                        year_values.setdefault(field, []).append(year)
            row_counts[csv_file.name] = count

    candidates = classify_columns(all_columns)
    candidate_filter_fields = set(candidates["language"] + candidates["year"] + candidates["journal"])
    top_values = {}
    for field in candidate_filter_fields:
        counts = value_counts.get(field, {})
        if not counts:
            continue
        top_values[field] = [
            {"value": value, "count": count}
            for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))[:30]
        ]
    year_ranges = {}
    for field in candidates["year"]:
        values = year_values.get(field, [])
        if values:
            year_ranges[field] = {"min": min(values), "max": max(values)}
    return {
        "csv_files": [path.name for path in csv_files],
        "row_counts": row_counts,
        "columns": all_columns,
        "columns_by_file": by_file,
        "candidates": candidates,
        "available_filters": {
            "language": bool(candidates["language"]),
            "year": bool(candidates["year"]),
            "journal": bool(candidates["journal"]),
        },
        "sample_values": {
            field: values
            for field, values in sample_values.items()
            if field in candidate_filter_fields
        },
        "top_values": top_values,
        "year_ranges": year_ranges,
    }


def row_passes_filters(row: dict[str, str], args: argparse.Namespace) -> tuple[bool, str]:
    abstract = norm_text(row.get(args.abstract_column, ""))
    if not abstract:
        return False, "empty_abstract"

    language_values = {norm_key(value) for value in split_values(args.language_keep)}
    if args.language_column and language_values:
        if norm_key(row.get(args.language_column, "")) not in language_values:
            return False, "language"

    if args.year_column and (args.year_start is not None or args.year_end is not None):
        year = parse_year(row.get(args.year_column, ""))
        if year is None:
            return False, "year_missing"
        if args.year_start is not None and year < args.year_start:
            return False, "year_before_start"
        if args.year_end is not None and year > args.year_end:
            return False, "year_after_end"

    journal_values = {norm_key(value) for value in split_values(args.journal_keep)}
    if args.journal_column and journal_values:
        if norm_key(row.get(args.journal_column, "")) not in journal_values:
            return False, "journal"
    journal_excluded_values = {norm_key(value) for value in split_values(args.journal_exclude)}
    if args.journal_column and journal_excluded_values:
        if norm_key(row.get(args.journal_column, "")) in journal_excluded_values:
            return False, "journal_excluded"

    return True, "kept"


def main() -> int:
    args = parse_args()
    input_folder = Path(args.input_folder).expanduser().resolve()

    if not input_folder.exists() or not input_folder.is_dir():
        print(f"Input folder does not exist or is not a folder: {input_folder}", file=sys.stderr)
        return 2

    csv_files = list_csv_files(input_folder)
    if not csv_files:
        print(f"No CSV files found in: {input_folder}", file=sys.stderr)
        return 2

    if args.inspect_only:
        inspection = inspect_headers(csv_files, args.encoding)
        if args.output_folder and args.inspect_name:
            output_folder = Path(args.output_folder).expanduser().resolve()
            output_folder.mkdir(parents=True, exist_ok=True)
            inspect_path = output_folder / args.inspect_name
            inspect_path.write_text(json.dumps(inspection, indent=2, ensure_ascii=False), encoding="utf-8")
            inspection["outputs"] = {"column_inspection": str(inspect_path)}
        print(json.dumps(inspection, indent=2, ensure_ascii=False))
        return 0

    if not args.abstract_column:
        print("Missing required --abstract-column. Run --inspect-only first if you need column suggestions.", file=sys.stderr)
        return 2

    if not args.output_folder:
        print("Missing required --output-folder.", file=sys.stderr)
        return 2

    output_folder = Path(args.output_folder).expanduser().resolve()
    output_folder.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    worklist_rows: list[dict[str, str]] = []
    field_order: list[str] = []
    source_counts: dict[str, int] = {}
    filter_counts: dict[str, int] = {}
    total_rows = 0

    for csv_file in csv_files:
        with open_csv(csv_file, args.encoding) as handle:
            reader = csv.DictReader(handle)
            update_field_order(field_order, reader.fieldnames)
            file_kept = 0
            for source_row_number, row in enumerate(reader, start=2):
                total_rows += 1
                keep, reason = row_passes_filters(row, args)
                filter_counts[reason] = filter_counts.get(reason, 0) + 1
                if not keep:
                    continue
                normalized_row = {field: row.get(field, "") for field in field_order}
                rows.append(normalized_row)
                worklist_rows.append(
                    {
                        "row_index": str(len(rows) - 1),
                        "source_file": csv_file.name,
                        "source_row": str(source_row_number),
                        "abstract": norm_text(row.get(args.abstract_column, "")),
                    }
                )
                file_kept += 1
            source_counts[csv_file.name] = file_kept

    if args.abstract_column not in field_order:
        print(
            f"Abstract column '{args.abstract_column}' was not found. Available columns: {', '.join(field_order)}",
            file=sys.stderr,
        )
        return 2

    filtered_path = output_folder / args.filtered_name
    worklist_path = output_folder / args.worklist_name

    with filtered_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_order, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    with worklist_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row_index", "source_file", "source_row", "abstract"])
        writer.writeheader()
        writer.writerows(worklist_rows)

    metadata = {
        "input_folder": str(input_folder),
        "output_folder": str(output_folder),
        "csv_files": [path.name for path in csv_files],
        "total_rows_read": total_rows,
        "filtered_rows_kept": len(rows),
        "source_counts": source_counts,
        "filter_counts": filter_counts,
        "abstract_column": args.abstract_column,
        "original_columns": field_order,
        "outputs": {
            "filtered_articles": str(filtered_path),
            "extraction_worklist": str(worklist_path),
        },
    }
    if args.metadata_name:
        metadata_path = output_folder / args.metadata_name
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
