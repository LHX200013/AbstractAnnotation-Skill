<p align="center">
  <img src="assets/logo.svg" alt="Abstract Annotation Skill logo" width="96" />
</p>

# Abstract Annotation Workflow for Relevant Variables

This repository documents a reusable workflow for extracting exact relevant mentions from academic abstracts, grouping them into literature-review dimensions, and producing article-level annotation outputs.

The workflow is designed for Codex or Claude Code skill-style execution. It supports CSV-based literature annotation tasks where article-level extraction must preserve exact wording from abstracts.

## Workflow Summary

1. Inspect CSV headers and identify abstract, language, year, and source-title fields.
2. Approve an extraction prompt for the target review task.
3. Filter records by selected metadata fields.
4. Extract exact relevant spans from each abstract.
5. Remove generic container terms that are not usable review items.
6. Group unique extracted items into dimensions and subdimensions.
7. Generate article-level binary dimension columns, a variable assignment table, a mention-ratio chart, and a styled dimension table.

## Example Use Case

For a user-defined review topic, the workflow can extract relevant variables, indicators, indices, metrics, factors, constructs, measures, predictors, methods, data sources, or other analytical items from each abstract.

The extracted items are then mapped into dimensions and subdimensions approved by the user.

## Outputs

- `final_articles_with_dimensions.csv`: original article rows plus `extracted_variables` and one binary column per approved dimension.
- `dimension_original_variables.csv`: exact extracted variables or relevant items assigned to one dimension and one subdimension.
- `dimension_mention_ratio_barplot.png`: article mention ratio by dimension.
- `dimension_mention_ratio_table.png`: styled table of dimensions, subdimensions, and mention ratios.

## Reuse Notes

The workflow is designed for literature-review screening tasks where article-level extraction must preserve exact wording from abstracts. Dimension and subdimension names are interpretive, but extracted items remain exact abstract spans.

For public repositories, review the license and redistribution rights for any raw bibliographic exports or abstracts before publishing them. If needed, publish only aggregate outputs, mapping tables, prompts, and documentation.
