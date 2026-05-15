<p align="center">
  <img src="assets/logo.svg" alt="Abstract Annotation Skill logo" width="96" />
</p>

# Abstract Annotation Workflow for Urban Built Environment Variables

This repository documents a reusable workflow for extracting exact variable mentions from academic abstracts, grouping them into literature-review dimensions, and producing article-level annotation outputs.

The current workflow is designed for Codex or Claude Code skill-style execution. It supports CSV-based literature annotation tasks where article-level extraction must preserve exact wording from abstracts.

## Workflow Summary

1. Inspect CSV headers and identify abstract, language, year, and source-title fields.
2. Approve an extraction prompt for the target review task.
3. Filter records by selected metadata fields.
4. Extract exact variable spans from each abstract.
5. Remove generic container terms that are not usable variables.
6. Group unique variables into dimensions and subdimensions.
7. Generate article-level binary dimension columns, a variable assignment table, a mention-ratio chart, and a styled dimension table.

## Example Use Case

The first workflow run focused on variables related to urban built environment and street visual elements. Extracted variables were mapped into six dimensions:

| Dimension | Subdimensions |
|---|---|
| Green, Natural, and Climate Conditions | Vegetation and Green Visibility; Open Space, Terrain, and Landscape Elements; Shade, Thermal, Weather, and Sound Conditions |
| Street Network, Mobility, and Accessibility | Road Type and Street Configuration; Pedestrian, Cycling, and Transit Infrastructure; Accessibility, Route Efficiency, and Travel Activity |
| Land Use, Density, Functions, and Facilities | Density, Morphology, and Spatial Structure; Land Use, Commercial Activity, and Functional Mix; Amenities, Services, and Urban Facilities |
| Architecture, Surfaces, and Street Objects | Building Form and Facades; Street Objects, Barriers, and Edges; Surfaces, Hardscape, and Physical Disorder |
| Visual Composition, Streetscape Quality, and Spatial Openness | Openness, Enclosure, Sky, and Visibility; Color, Light, and Visual Texture; Streetscape Quality, Diversity, and Visual Attention |
| Perceptual, Emotional, and Social Experience | Safety, Comfort, and Fear-Related Perception; Aesthetic, Place, and Environmental Perception; Vitality, Liveliness, Wealth, and Social Sentiment; Negative Affect and Appraisal |

## Expected Outputs

- `final_articles_with_dimensions.csv`: original article rows plus `extracted_variables` and one binary column per approved dimension.
- `dimension_original_variables.csv`: exact extracted variables assigned to one dimension and one subdimension.
- `dimension_mention_ratio_barplot.png`: article mention ratio by dimension.
- `dimension_mention_ratio_table.png`: styled table of dimensions, subdimensions, and mention ratios.

## Publication Note

Raw bibliographic exports and full abstracts may be subject to database or publisher restrictions. For public repositories, publish workflow documentation, prompts, scripts, aggregate outputs, and sanitized examples unless redistribution rights are clear.
