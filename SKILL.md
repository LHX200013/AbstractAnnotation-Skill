---
name: abstract-annotation
description: Extract exact variable mentions from academic abstracts, group them into dimensions and subdimensions, and generate review-ready article and dimension outputs.
---

# Abstract Annotation

Use this skill for literature-analysis workflows over CSV files containing academic abstracts.

## Purpose

This skill helps a researcher annotate abstracts by extracting exact text spans for variables, indicators, indices, metrics, factors, constructs, measures, predictors, methods, or data sources, then grouping extracted items into review-ready dimensions.

The default example task focuses on urban built environment and street visual elements.

## Core Rules

- Extracted values must be exact spans copied from the abstract.
- Do not paraphrase, translate, standardize, or infer missing concepts.
- Keep article-level extraction separate from later interpretive grouping.
- Assign every unique extracted variable to exactly one dimension and one subdimension.
- Use binary article columns where `1` means the article mentions at least one variable in that dimension.

## Expected Inputs

- One or more CSV files.
- An abstract column.
- Optional language, year, and source-title columns for filtering.
- A user-approved extraction prompt.

## Expected Outputs

- `final_articles_with_dimensions.csv`
- `dimension_original_variables.csv`
- `dimension_mention_ratio_barplot.png`
- `dimension_mention_ratio_table.png`

## Suggested Workflow

1. Inspect CSV headers.
2. Identify the abstract column and optional filter columns.
3. Ask the user to approve a complete extraction prompt.
4. Merge and filter CSV rows.
5. Extract exact spans from each abstract.
6. Validate that every span appears literally in its abstract.
7. Draft dimensions and subdimensions.
8. Ask the user to approve the dimension structure.
9. Generate final outputs.
