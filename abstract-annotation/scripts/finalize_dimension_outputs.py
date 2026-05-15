#!/usr/bin/env python3
"""Create final dimension outputs from extracted variables and an approved mapping."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import shutil
import sys
import textwrap
from collections import OrderedDict
from pathlib import Path
from typing import Iterable


_MISSING_PACKAGES_NOTED: set[str] = set()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add binary dimension columns, calculate mention ratios, and render chart/table outputs."
    )
    parser.add_argument("--articles-csv", required=True, help="Filtered article CSV preserving original columns.")
    parser.add_argument("--mapping-csv", required=True, help="Approved variable-to-dimension mapping CSV.")
    parser.add_argument("--output-folder", required=True, help="Folder where final outputs will be written.")
    parser.add_argument("--extractions-csv", default="", help="Optional CSV with row_index and extracted_variables.")
    parser.add_argument("--extracted-column", default="extracted_variables", help="Column containing JSON-array variables.")
    parser.add_argument("--topic-label", default="", help="Optional topic label for chart title.")
    parser.add_argument("--final-name", default="final_articles_with_dimensions.csv")
    parser.add_argument("--chart-name", default="dimension_mention_ratio_barplot.png")
    parser.add_argument("--table-name", default="dimension_mention_ratio_table.png")
    parser.add_argument("--dimension-variables-name", default="dimension_original_variables.csv")
    parser.add_argument(
        "--cleanup-work-folder",
        default="",
        help="Optional temporary work folder to remove after successful output creation. The folder name must be .abstract_annotation_work.",
    )
    return parser.parse_args()


def note_missing(package: str) -> None:
    if package in _MISSING_PACKAGES_NOTED:
        return
    _MISSING_PACKAGES_NOTED.add(package)
    print(
        f"Missing optional plotting dependency: {package}. Falling back to SVG/HTML outputs. "
        f"Install it with: python -m pip install {package}",
        file=sys.stderr,
    )


def norm_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm_var(value: object) -> str:
    text = norm_text(value).casefold()
    text = re.sub(r"^[\"'`]+|[\"'`,.;:]+$", "", text)
    return re.sub(r"\s+", " ", text).strip()


def split_values(raw: str) -> list[str]:
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [norm_text(item) for item in parsed if norm_text(item)]
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in re.split(r"[|;\n]", text) if part.strip()]


def parse_variable_array(raw: str) -> list[str]:
    return split_values(raw)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def get_header(row: dict[str, str], *names: str) -> str:
    by_norm = {norm_var(key): key for key in row.keys()}
    for name in names:
        key = by_norm.get(norm_var(name))
        if key is not None:
            return key
    return ""


def load_mapping(
    path: Path,
) -> tuple[OrderedDict[str, list[str]], dict[str, tuple[str, str]], OrderedDict[str, dict[str, str]]]:
    fieldnames, rows = read_csv(path)
    if not fieldnames:
        raise ValueError("Mapping CSV has no header row.")

    dimensions: OrderedDict[str, list[str]] = OrderedDict()
    variable_to_mapping: dict[str, tuple[str, str]] = {}
    variable_assignments: OrderedDict[str, dict[str, str]] = OrderedDict()

    for row in rows:
        dimension_key = get_header(row, "dimension")
        subdimension_key = get_header(row, "subdimension", "sub_dimension", "sub-dimension")
        variable_key = get_header(row, "variable")
        variables_key = get_header(row, "variables", "original variables", "original_variables")

        if not dimension_key or not subdimension_key:
            raise ValueError("Mapping CSV must include Dimension and Subdimension columns.")

        dimension = norm_text(row.get(dimension_key, ""))
        subdimension = norm_text(row.get(subdimension_key, ""))
        if not dimension:
            continue
        if not subdimension:
            subdimension = "Unspecified"

        if dimension not in dimensions:
            dimensions[dimension] = []
        if subdimension not in dimensions[dimension]:
            dimensions[dimension].append(subdimension)

        variables: list[str] = []
        if variable_key:
            variables.extend(split_values(row.get(variable_key, "")))
        if variables_key:
            variables.extend(split_values(row.get(variables_key, "")))

        for variable in variables:
            key = norm_var(variable)
            if key:
                original_variable = norm_text(variable)
                variable_to_mapping[key] = (dimension, subdimension)
                variable_assignments[key] = {
                    "Dimension": dimension,
                    "Subdimension": subdimension,
                    "Original Variable": original_variable,
                }

    if not dimensions:
        raise ValueError("Mapping CSV did not contain any dimensions.")
    if not variable_to_mapping:
        raise ValueError("Mapping CSV did not contain any variables to map.")
    return dimensions, variable_to_mapping, variable_assignments


def write_dimension_variables_csv(
    path: Path,
    variable_assignments: OrderedDict[str, dict[str, str]],
    dimensions: OrderedDict[str, list[str]],
) -> None:
    dimension_order = {dimension: index for index, dimension in enumerate(dimensions.keys())}
    subdimension_order = {
        (dimension, subdimension): index
        for dimension, subdimensions in dimensions.items()
        for index, subdimension in enumerate(subdimensions)
    }
    rows = sorted(
        variable_assignments.values(),
        key=lambda row: (
            dimension_order.get(row["Dimension"], len(dimension_order)),
            subdimension_order.get((row["Dimension"], row["Subdimension"]), 999999),
            row["Original Variable"].casefold(),
        ),
    )
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Dimension", "Subdimension", "Original Variable"])
        writer.writeheader()
        writer.writerows(rows)


def merge_extractions(
    articles: list[dict[str, str]],
    article_fields: list[str],
    extractions_csv: Path,
    extracted_column: str,
) -> None:
    extraction_fields, extraction_rows = read_csv(extractions_csv)
    if not extraction_fields:
        raise ValueError("Extractions CSV has no header row.")
    if extracted_column not in extraction_fields:
        raise ValueError(f"Extractions CSV must include '{extracted_column}'.")

    has_row_index = "row_index" in extraction_fields
    if has_row_index:
        for extraction in extraction_rows:
            index_text = norm_text(extraction.get("row_index", ""))
            if not index_text.isdigit():
                continue
            index = int(index_text)
            if 0 <= index < len(articles):
                articles[index][extracted_column] = extraction.get(extracted_column, "")
    else:
        if len(extraction_rows) != len(articles):
            raise ValueError(
                "Extractions CSV has no row_index column and its row count does not match the article CSV."
            )
        for article, extraction in zip(articles, extraction_rows):
            article[extracted_column] = extraction.get(extracted_column, "")


def collect_mentions(
    articles: list[dict[str, str]],
    dimensions: OrderedDict[str, list[str]],
    variable_to_mapping: dict[str, tuple[str, str]],
    extracted_column: str,
) -> tuple[dict[str, int], list[dict[str, str]]]:
    dimension_counts = {dimension: 0 for dimension in dimensions}
    enriched_rows: list[dict[str, str]] = []

    for article in articles:
        variables = parse_variable_array(article.get(extracted_column, ""))
        mentioned_dimensions: set[str] = set()
        for variable in variables:
            mapped = variable_to_mapping.get(norm_var(variable))
            if mapped:
                mentioned_dimensions.add(mapped[0])

        for dimension in mentioned_dimensions:
            dimension_counts[dimension] += 1

        enriched = dict(article)
        normalized_json = json.dumps([norm_text(value) for value in variables if norm_text(value)], ensure_ascii=False)
        enriched[extracted_column] = normalized_json
        for dimension in dimensions:
            enriched[dimension] = "1" if dimension in mentioned_dimensions else "0"
        enriched_rows.append(enriched)

    return dimension_counts, enriched_rows


def write_final_csv(
    path: Path,
    rows: list[dict[str, str]],
    original_fields: list[str],
    dimensions: Iterable[str],
    extracted_column: str,
) -> None:
    dimension_list = list(dimensions)
    fieldnames = [
        field
        for field in original_fields
        if field != extracted_column and field not in dimension_list
    ]
    fieldnames.extend([extracted_column] + dimension_list)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_summary_rows(
    dimensions: OrderedDict[str, list[str]],
    dimension_counts: dict[str, int],
    total_articles: int,
) -> list[dict[str, str]]:
    rows = []
    denominator = max(total_articles, 1)
    for dimension, subdimensions in dimensions.items():
        ratio = dimension_counts.get(dimension, 0) / denominator
        rows.append(
            {
                "Dimension": dimension,
                "Subdimension": " | ".join(subdimensions),
                "Mention Ratio": f"{ratio * 100:.1f} %",
                "_ratio": ratio,
            }
        )
    rows.sort(key=lambda row: row["_ratio"], reverse=True)
    return rows


def fallback_path(path: Path, suffix: str) -> Path:
    if path.suffix.lower() == suffix:
        return path
    if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        return path.with_suffix(suffix)
    return path


def svg_escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg_text_lines(text: str, max_chars: int) -> list[str]:
    wrapped = textwrap.wrap(
        norm_text(text),
        width=max_chars,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return wrapped or [""]


def save_bar_chart_svg(path: Path, summary_rows: list[dict[str, str]], topic_label: str) -> Path:
    actual_path = fallback_path(path, ".svg")
    rows = summary_rows
    longest_label = max([len(row["Dimension"]) for row in rows] + [20])
    left = min(520, max(300, 58 + longest_label * 7))
    right = 110
    top = 62
    row_height = 35
    bottom = 66
    plot_width = max(620, min(940, 720 + len(rows) * 12))
    width = left + plot_width + right
    axis_y = top + len(rows) * row_height + 6
    height = max(240, axis_y + bottom)
    max_ratio = max([row["_ratio"] for row in rows] + [0.05])
    x_max = min(1.08, max(0.1, max_ratio + 0.08))
    title = "Proportion of Mentions across Different Dimensions"
    if topic_label:
        title += f" under the Topic of {topic_label}"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2:.1f}" y="28" text-anchor="middle" font-family="Arial, sans-serif" font-size="18">{svg_escape(title)}</text>',
    ]
    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        if tick > x_max:
            continue
        x = left + (tick / x_max) * plot_width
        parts.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{axis_y}" stroke="#e6eaf0" stroke-width="1"/>')
    parts.append(f'<line x1="{left}" y1="{axis_y}" x2="{left + plot_width}" y2="{axis_y}" stroke="#111" stroke-width="1"/>')
    for index, row in enumerate(rows):
        y = top + index * row_height
        bar_y = y + 8
        bar_width = max(1, int((row["_ratio"] / x_max) * plot_width))
        label_lines = svg_text_lines(row["Dimension"], max(24, int((left - 80) / 7)))
        line_start = y + 15 - (len(label_lines) - 1) * 6
        for line_index, line in enumerate(label_lines[:2]):
            parts.append(
                f'<text x="{left - 12}" y="{line_start + line_index * 13}" text-anchor="end" '
                f'font-family="Arial, sans-serif" font-size="13" fill="#111827">{svg_escape(line)}</text>'
            )
        parts.append(f'<rect x="{left}" y="{bar_y}" width="{bar_width}" height="22" fill="#1f77b4"/>')
        parts.append(
            f'<text x="{left + bar_width + 8}" y="{bar_y + 16}" '
            f'font-family="Arial, sans-serif" font-size="13" fill="#111827">{row["_ratio"] * 100:.1f}%</text>'
        )
    parts.append(
        f'<text x="{left + plot_width / 2:.1f}" y="{axis_y + 45}" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="14">Proportion of Articles Mentioning Dimension</text>'
    )
    for tick in (0, 0.25, 0.5, 0.75, 1.0):
        if tick > x_max:
            continue
        x = left + (tick / x_max) * plot_width
        parts.append(f'<line x1="{x:.1f}" y1="{axis_y}" x2="{x:.1f}" y2="{axis_y + 4}" stroke="#111" stroke-width="1"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{axis_y + 19}" text-anchor="middle" '
            f'font-family="Arial, sans-serif" font-size="12" fill="#111827">{tick:g}</text>'
        )
    parts.append("</svg>")
    actual_path.write_text("\n".join(parts), encoding="utf-8")
    return actual_path


def save_bar_chart(path: Path, summary_rows: list[dict[str, str]], topic_label: str) -> Path:
    if path.suffix.lower() == ".svg":
        return save_bar_chart_svg(path, summary_rows, topic_label)
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        note_missing("matplotlib")
        return save_bar_chart_svg(path, summary_rows, topic_label)

    dimensions = [row["Dimension"] for row in summary_rows]
    ratios = [row["_ratio"] for row in summary_rows]
    label_chars = max([len(dimension) for dimension in dimensions] + [20])
    height = max(2.8, min(12.0, 1.25 + 0.42 * len(dimensions)))
    width = max(9.0, min(16.0, 7.6 + 0.12 * label_chars + 0.03 * len(dimensions)))
    wrapped_dimensions = [
        textwrap.fill(dimension, width=max(24, min(48, int(label_chars * 0.85))), break_long_words=False)
        for dimension in dimensions
    ]

    fig, ax = plt.subplots(figsize=(width, height))
    y_positions = range(len(dimensions))
    ax.barh(y_positions, ratios, color="#1f77b4", height=0.64)
    ax.set_yticks(list(y_positions))
    ax.set_yticklabels(wrapped_dimensions, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Proportion of Articles Mentioning Dimension", labelpad=8)
    ax.set_ylabel("")

    title = "Proportion of Mentions across Different Dimensions"
    if topic_label:
        title += f" under the Topic of {topic_label}"
    ax.set_title(textwrap.fill(title, width=95), fontsize=11, pad=12)

    upper = min(1.08, max(ratios + [0.05]) + 0.08)
    ax.set_xlim(0, upper)
    for index, ratio in enumerate(ratios):
        ax.text(ratio + upper * 0.01, index, f"{ratio * 100:.1f}%", va="center", fontsize=9)
    ax.xaxis.grid(True, color="#e6eaf0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    left_margin = min(0.44, max(0.20, 0.12 + label_chars * 0.006))
    fig.subplots_adjust(left=left_margin, right=0.92, top=0.84, bottom=0.18)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def wrap_text(value: str, width: int) -> str:
    return textwrap.fill(value, width=width, break_long_words=False, break_on_hyphens=False)


def format_subdimension_text(value: str) -> str:
    return value.replace(" | ", r" $\mathbf{|}$ ")


def subdimension_html(value: str) -> str:
    return " <strong>|</strong> ".join(html.escape(part.strip()) for part in value.split(" | "))


def save_table_html(path: Path, summary_rows: list[dict[str, str]]) -> Path:
    actual_path = path if path.suffix.lower() == ".html" else path.with_suffix(".html")
    rows = []
    for row in summary_rows:
        rows.append(
            "<tr>"
            f"<td>{html.escape(row['Dimension'])}</td>"
            f"<td>{subdimension_html(row['Subdimension'])}</td>"
            f"<td class=\"ratio\">{html.escape(row['Mention Ratio'])}</td>"
            "</tr>"
        )
    document = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ margin: 24px; background: #fff; font-family: Arial, sans-serif; color: #0f1f2e; }}
table {{ border-collapse: collapse; width: 100%; table-layout: fixed; font-size: 14px; }}
th {{ background: #24313a; color: white; font-weight: 700; text-align: left; padding: 14px; border: 1px solid #d8dee6; }}
td {{ padding: 14px; border: 1px solid #d8dee6; vertical-align: middle; overflow-wrap: anywhere; line-height: 1.35; }}
tr:nth-child(even) td {{ background: #f3f6fa; }}
th:nth-child(1), td:nth-child(1) {{ width: 30%; }}
th:nth-child(2), td:nth-child(2) {{ width: 58%; }}
th:nth-child(3), td:nth-child(3) {{ width: 12%; }}
.ratio {{ text-align: right; white-space: nowrap; }}
strong {{ font-weight: 800; }}
</style>
</head>
<body>
<table>
<thead><tr><th>Dimension</th><th>Subdimension</th><th>Mention Ratio</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body>
</html>
"""
    actual_path.write_text(document, encoding="utf-8")
    return actual_path


def save_table_svg(path: Path, summary_rows: list[dict[str, str]]) -> Path:
    actual_path = fallback_path(path, ".svg")
    width = 1600
    margin = 28
    dimension_width = 450
    ratio_width = 150
    table_width = width - 2 * margin
    subdimension_width = table_width - dimension_width - ratio_width
    header_height = 52
    padding = 16
    line_height = 18
    prepared = []
    total_height = margin + header_height
    for row in summary_rows:
        dimension_lines = svg_text_lines(row["Dimension"], 38)
        subdimension_lines = svg_text_lines(row["Subdimension"], 112)
        row_height = max(64, (max(len(dimension_lines), len(subdimension_lines)) * line_height) + 2 * padding)
        prepared.append((row, dimension_lines, subdimension_lines, row_height))
        total_height += row_height
    total_height += margin

    x1 = margin
    x2 = x1 + dimension_width
    x3 = x2 + subdimension_width
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_height}" viewBox="0 0 {width} {total_height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<rect x="{x1}" y="{margin}" width="{table_width}" height="{header_height}" fill="#24313a"/>',
        f'<text x="{x1 + padding}" y="{margin + 33}" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="white">Dimension</text>',
        f'<text x="{x2 + padding}" y="{margin + 33}" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="white">Subdimension</text>',
        f'<text x="{x3 + padding}" y="{margin + 33}" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="white">Mention Ratio</text>',
    ]
    y = margin + header_height
    for index, (row, dimension_lines, subdimension_lines, row_height) in enumerate(prepared):
        fill = "#f3f6fa" if index % 2 else "#ffffff"
        parts.append(f'<rect x="{x1}" y="{y}" width="{table_width}" height="{row_height}" fill="{fill}"/>')
        parts.append(f'<rect x="{x1}" y="{y}" width="{dimension_width}" height="{row_height}" fill="none" stroke="#d8dee6"/>')
        parts.append(f'<rect x="{x2}" y="{y}" width="{subdimension_width}" height="{row_height}" fill="none" stroke="#d8dee6"/>')
        parts.append(f'<rect x="{x3}" y="{y}" width="{ratio_width}" height="{row_height}" fill="none" stroke="#d8dee6"/>')
        text_y = y + padding + 15
        for line in dimension_lines:
            parts.append(
                f'<text x="{x1 + padding}" y="{text_y}" font-family="Arial, sans-serif" font-size="15" fill="#0f1f2e">{svg_escape(line)}</text>'
            )
            text_y += line_height
        text_y = y + padding + 15
        for line in subdimension_lines:
            x_cursor = x2 + padding
            parts.append(f'<text x="{x_cursor}" y="{text_y}" font-family="Arial, sans-serif" font-size="15" fill="#0f1f2e">')
            for part in re.split(r"(\|)", line):
                if not part:
                    continue
                weight = ' font-weight="800"' if part == "|" else ""
                parts.append(f'<tspan{weight}>{svg_escape(part)}</tspan>')
            parts.append("</text>")
            text_y += line_height
        parts.append(
            f'<text x="{x3 + ratio_width - padding}" y="{y + row_height / 2 + 5:.1f}" '
            f'text-anchor="end" font-family="Arial, sans-serif" font-size="15" fill="#0f1f2e">{svg_escape(row["Mention Ratio"])}</text>'
        )
        y += row_height
    parts.append("</svg>")
    actual_path.write_text("\n".join(parts), encoding="utf-8")
    return actual_path


def save_table_image(path: Path, summary_rows: list[dict[str, str]]) -> Path:
    if path.suffix.lower() == ".svg":
        return save_table_svg(path, summary_rows)
    if path.suffix.lower() == ".html":
        return save_table_html(path, summary_rows)
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        note_missing("matplotlib")
        return save_table_svg(path, summary_rows)

    display_rows = [
        [
            wrap_text(row["Dimension"], 34),
            format_subdimension_text(wrap_text(row["Subdimension"], 105)),
            row["Mention Ratio"],
        ]
        for row in summary_rows
    ]
    row_heights = [
        max(0.45, 0.23 * max(cell.count("\n") + 1 for cell in row))
        for row in display_rows
    ]
    fig_height = max(2.0, 0.7 + sum(row_heights))
    fig_width = 16

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")
    table = ax.table(
        cellText=display_rows,
        colLabels=["Dimension", "Subdimension", "Mention Ratio"],
        loc="center",
        cellLoc="left",
        colLoc="left",
        colWidths=[0.30, 0.58, 0.12],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)

    header_color = "#24313a"
    border_color = "#d8dee6"
    alternate_color = "#f3f6fa"

    for (row_index, col_index), cell in table.get_celld().items():
        cell.set_edgecolor(border_color)
        cell.set_linewidth(0.75)
        if row_index == 0:
            cell.set_facecolor(header_color)
            cell.set_text_props(color="white", weight="bold", ha="left", va="center")
            cell.set_height(0.28)
        else:
            cell.set_facecolor(alternate_color if row_index % 2 == 0 else "white")
            horizontal = "right" if col_index == 2 else "left"
            cell.set_text_props(color="#0f1f2e", ha=horizontal, va="center")
            cell.set_height(row_heights[row_index - 1])

    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def cleanup_work_folder(raw_path: str) -> str:
    if not raw_path:
        return ""
    folder = Path(raw_path).expanduser().resolve()
    if not folder.exists():
        return ""
    if not folder.is_dir():
        raise ValueError(f"Cleanup target is not a folder: {folder}")
    if folder.name != ".abstract_annotation_work":
        raise ValueError("Refusing to clean up a folder not named .abstract_annotation_work.")
    shutil.rmtree(folder)
    return str(folder)


def main() -> int:
    args = parse_args()
    articles_csv = Path(args.articles_csv).expanduser().resolve()
    mapping_csv = Path(args.mapping_csv).expanduser().resolve()
    output_folder = Path(args.output_folder).expanduser().resolve()
    output_folder.mkdir(parents=True, exist_ok=True)

    article_fields, articles = read_csv(articles_csv)
    if not article_fields:
        print("Article CSV has no header row.", file=sys.stderr)
        return 2
    if not articles:
        print("Article CSV has no rows.", file=sys.stderr)
        return 2

    if args.extractions_csv:
        merge_extractions(articles, article_fields, Path(args.extractions_csv).expanduser().resolve(), args.extracted_column)
    elif args.extracted_column not in article_fields:
        print(
            f"Article CSV must include '{args.extracted_column}' or provide --extractions-csv.",
            file=sys.stderr,
        )
        return 2

    try:
        dimensions, variable_to_mapping, variable_assignments = load_mapping(mapping_csv)
        dimension_counts, enriched_rows = collect_mentions(
            articles, dimensions, variable_to_mapping, args.extracted_column
        )
        summary_rows = build_summary_rows(dimensions, dimension_counts, len(articles))
        final_path = output_folder / args.final_name
        dimension_variables_path = output_folder / args.dimension_variables_name
        write_final_csv(
            final_path,
            enriched_rows,
            article_fields,
            dimensions.keys(),
            args.extracted_column,
        )
        write_dimension_variables_csv(dimension_variables_path, variable_assignments, dimensions)
        chart_path = save_bar_chart(output_folder / args.chart_name, summary_rows, args.topic_label)
        table_path = save_table_image(output_folder / args.table_name, summary_rows)
        cleaned_folder = cleanup_work_folder(args.cleanup_work_folder)
    except Exception as exc:
        print(f"Failed to finalize outputs: {exc}", file=sys.stderr)
        return 1

    outputs = {
        "final_csv": str(final_path),
        "bar_chart": str(chart_path),
        "table_image": str(table_path),
        "dimension_variables_csv": str(dimension_variables_path),
        "article_count": len(articles),
        "dimension_count": len(dimensions),
    }
    if cleaned_folder:
        outputs["cleaned_work_folder"] = cleaned_folder
    print(json.dumps(outputs, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
