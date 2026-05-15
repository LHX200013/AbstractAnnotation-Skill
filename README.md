<p align="center">
  <img src="assets/logo.svg" alt="Abstract Annotation Skill logo" width="96" />
</p>

# Abstract Annotation Workflow for Relevant Variables

This repository documents a reusable workflow for extracting exact relevant mentions from academic abstracts, grouping them into literature-review dimensions, and producing article-level annotation outputs.

The workflow is designed for **Codex or Claude Code** skill-style execution. It supports CSV-based literature annotation tasks where raw relevant variables and terms are extracted according to a specific task.

## Use as an Agent Skill

This repository is intended to be used by installing the complete `abstract-annotation/` folder as an agent skill. Keep the folder name and internal structure unchanged:

```text
abstract-annotation/
  SKILL.md
  agents/
  references/
  scripts/
```

For Codex in Windows, copy the full `abstract-annotation/` folder into your Codex skills directory:

```text
C:\Users\<YOUR_USER>\.codex\skills\abstract-annotation
```

For Claude Code, copy the full `abstract-annotation/` folder into the Claude Code skills directory used by your personal or project setup. The copied folder must contain `SKILL.md`, `scripts/`, and `references/`.

After copying or updating the folder, restart Codex or Claude Code, then ask the agent to use `abstract-annotation` for CSV-based abstract extraction.

## Example Use Case: Street-View Visual Variables

One example run applies the workflow to a street-view visual variable extraction task. The workflow extracts exact variable spans from abstracts, then groups them into user-approved dimensions and subdimensions.

| Dimension | Subdimensions | Mention Ratio |
|---|---|---:|
| Green, Natural, and Climate Conditions | Vegetation and Green Visibility; Open Space, Terrain, and Landscape Elements; Shade, Thermal, Weather, and Sound Conditions | 0.700 |
| Street Network, Mobility, and Accessibility | Road Type and Street Configuration; Pedestrian, Cycling, and Transit Infrastructure; Accessibility, Route Efficiency, and Travel Activity | 0.467 |
| Land Use, Density, Functions, and Facilities | Density, Morphology, and Spatial Structure; Land Use, Commercial Activity, and Functional Mix; Amenities, Services, and Urban Facilities | 0.500 |
| Architecture, Surfaces, and Street Objects | Building Form and Facades; Street Objects, Barriers, and Edges; Surfaces, Hardscape, and Physical Disorder | 0.433 |
| Visual Composition, and Streetscape Quality | Openness, Enclosure, Sky, and Visibility; Color, Light, and Visual Texture; Streetscape Quality, Diversity, and Visual Attention | 0.500 |
| Perceptual, Emotional, and Social Experience | Safety, Comfort, and Fear-Related Perception; Aesthetic, Place, and Environmental Perception; Vitality, Liveliness, Wealth, and Social Sentiment; Negative Affect and Appraisal | 0.433 |

<img src="examples/street-view-visual-variable-bar-chart-v3.svg" alt="Example mention-ratio bar chart" width="100%" />

See [examples/street-view-visual-variable-use-case.md](examples/street-view-visual-variable-use-case.md) for the example table.

## Workflow Summary

1. Inspect CSV headers and identify abstract, language, year, and source-title fields.
2. Approve an extraction prompt for the target review task.
3. Filter records by selected metadata fields.
4. Extract exact relevant spans from each abstract.
5. Remove generic container terms that are not usable review items.
6. Group unique extracted items into dimensions and subdimensions.
7. Generate article-level binary dimension columns, a variable assignment table, a mention-ratio chart, and a styled dimension table.

## Outputs

- `final_articles_with_dimensions.csv`: original article rows plus `extracted_variables` and one binary column per approved dimension.
- `dimension_original_variables.csv`: exact extracted variables or relevant items assigned to one dimension and one subdimension.
- `dimension_mention_ratio_barplot.png`: article mention ratio by dimension.
- `dimension_mention_ratio_table.png`: styled table of dimensions, subdimensions, and mention ratios.

## Reuse Notes

The workflow is designed for literature-review screening tasks where article-level extraction must preserve exact wording from abstracts. Dimension and subdimension names are interpretive, but extracted items remain exact abstract spans.
