# Workflow Introduction

## Purpose

This workflow supports structured literature annotation from CSV exports of academic records. It is useful when a researcher needs to identify relevant variables, indicators, data sources, methods, or other analytical items across many abstracts and summarize them into review-ready categories.

## Input

The input is a CSV export with article metadata and an abstract column. Candidate metadata fields may include:

- Abstract column
- Language column
- Year column
- Source-title or journal column

## Extraction Rule

Article-level extracted values must be exact text spans copied from the abstract. They are not paraphrased, translated, standardized, or inferred.

The approved prompt can set a maximum number of extracted spans per article and should define what to return when no relevant item is present.

## Processing Steps

1. Merge CSV files from the selected folder.
2. Inspect columns and candidate filters.
3. Apply approved language, year, and source-title filters.
4. Extract exact relevant spans from each filtered abstract.
5. Validate that extracted spans are literal substrings of their abstracts.
6. Collect unique extracted items and draft dimensions.
7. Assign every unique extracted item to exactly one dimension.
8. Assign every unique extracted item to exactly one subdimension.
9. Generate final article-level and dimension-level outputs.

## Output Interpretation

The final article CSV keeps all original columns and appends:

- `extracted_variables`: JSON array of exact relevant spans.
- One binary column per approved dimension, where `1` means the article mentions at least one extracted item assigned to that dimension.

The mention ratio is calculated as:

```text
articles mentioning the dimension / all filtered articles
```

This same ratio is used in both the bar chart and styled table.

## Suggested Repository Structure

```text
.
+-- README.md
+-- LICENSE
+-- .gitignore
+-- SKILL.md
+-- docs/
|   +-- workflow-introduction.md
|   +-- github-upload.md
+-- assets/
|   +-- logo.svg
+-- examples/
|   +-- street-view-visual-variable-use-case.md
|   +-- street-view-visual-variable-bar-chart.svg
+-- final_articles_with_dimensions.csv
+-- dimension_original_variables.csv
+-- dimension_mention_ratio_barplot.png
+-- dimension_mention_ratio_table.png
```
