---
name: abstract-annotation
description: Reusable workflow for extracting literature variables, methods, data sources, indicators, indices, metrics, scores, factors, constructs, measures, predictors, or requested outcomes from CSV abstracts, grouping them into dimensions/subdimensions, and producing mapped article CSV, variable-assignment CSV, mention-ratio chart, and styled dimension table. Use when a user wants to analyze batches of academic abstracts with a custom extraction task, especially in geography, urban studies, remote sensing, economic analysis, built-environment research, visual perception, or related literature-review workflows.
---

# Abstract Annotation

Use this skill for reusable literature-analysis workflows over CSV files. The workflow is interactive and all skill instructions and user-facing workflow text must be written in English.

## Agent compatibility

- This is a generic Agent Skill. It follows the portable `SKILL.md` folder pattern used by Claude Code and Codex.
- Required portable files are `SKILL.md`, `scripts/`, and `references/`.
- `agents/openai.yaml` is optional Codex UI metadata. Other agents can ignore it.
- For installation paths and sharing notes, read `references/installation.md`.

## Runtime preference

- On Windows, use the bundled PowerShell scripts first. Do not spend time looking for Python before trying the PowerShell scripts.
- The PowerShell path requires no separate Python installation.
- On macOS or Linux, use `python3` with the bundled Python scripts.
- Python CSV processing uses only the standard library.
- Python chart/table rendering tries `matplotlib` for PNG outputs. If `matplotlib` is unavailable, automatically fall back to SVG outputs instead of failing; HTML table output is also supported when explicitly requested.

## Question style

- Ask one question at a time. Do not combine extraction task, abstract column, filters, and output folder into one message.
- After inspecting headers, use short choice-style questions whenever possible.
- Treat the first listed choice as the default when the user answers yes or gives a brief confirmation.
- Do not use a short one-sentence user task directly for article extraction. First expand it into a complete extraction prompt, then ask the user to approve or edit that prompt.

## Exact extraction rule

- Values in `extracted_variables` must be exact text spans copied from the abstract.
- Do not paraphrase, summarize, translate, standardize, lemmatize, or replace extracted values with synonyms.
- Do not infer a broader concept when the exact phrase is absent from the abstract.
- If abstracts contain non-English exact spans, extracted values may preserve the original abstract wording. Do not translate those spans into English.
- Subjective grouping is allowed only after all article-level `extracted_variables` are complete, when drafting dimensions and subdimensions from the unique extracted values.

## Core workflow

1. Ask the user for the folder containing CSV files.
2. Inspect headers and identify abstract, language, year, and journal/source-title candidate columns. Use `scripts/read_and_filter_csvs.ps1 -InspectOnly` on Windows or `python3 scripts/read_and_filter_csvs.py --inspect-only` on macOS/Linux.
3. Ask the user to choose the extraction task type for all abstracts:
   - methods used in each study
   - variables that influence, explain, predict, or correlate with a topic
   - datasets or data sources used in each study
   - a custom task written by the user
4. Ask the user for a one-sentence extraction goal, then expand it into a full English extraction prompt with task, include rules, exclude rules, output constraints, and empty-result behavior. Show the prompt and ask whether to approve or edit it.
5. Ask whether to use the detected abstract column, such as `Use Abstract?`; choices are yes or manual column name. If no abstract candidate is detected, show all columns and ask for a manual column name.
6. Ask optional filter questions only when a related candidate column exists:
   - if language columns exist, ask whether to keep all languages or keep only English
   - if year columns exist, show the detected year range and ask whether to keep all years or use a manual range such as `2010-2024`
   - if journal/source-title columns exist, ask whether to keep all source titles, include only specified source titles, or exclude specified source titles
   Skip a filter silently or with a short note when no related column exists.
7. Ask for the final output folder.
8. Run the bundled read/filter script in a temporary work folder to merge and filter the CSV files.
9. Apply the approved extraction prompt to every filtered abstract. Store only exact abstract text spans as JSON arrays in a new `extracted_variables` column.
10. Collect all unique extracted text spans. First draft the dimension categories, then assign every original variable to exactly one dimension. After assignment, summarize the variables inside each dimension into diverse, specific subdimensions and assign every original variable to exactly one subdimension. This is the first step where interpretive summarization or subjective grouping is allowed.
11. Show the draft dimensions/subdimensions to the user and ask a choice-style approval question:
    - `Approve and generate final outputs`
    - `No, I want to revise`
12. If the user approves, run the bundled finalization script to create the final CSV, bar chart, styled table, and variable-assignment CSV.
13. If the user does not approve, ask a follow-up choice:
    - `Stop here`
    - `Revise the extraction prompt and rerun extraction`
    If rerunning, ask the user for the revised prompt, rerun extraction on the same filtered articles, regenerate variables and dimensions, then ask for dimension approval again.

## Required behavior

- Do not hard-code local paths. All paths must come from the user or from files produced during the current run.
- Preserve the original CSV columns in the final output.
- Append new columns after the original columns: `extracted_variables`, then one binary column per approved dimension.
- Keep `extracted_variables` faithful to the abstract wording. Article-level extraction is evidence capture, not summarization.
- Before extracting articles, convert the user's brief extraction goal into an approved full prompt. For influence/correlation tasks, the prompt must name the target topic, give non-exhaustive examples of explanatory/predictor/influencing variable types, exclude the outcome itself unless the user explicitly asks to extract outcomes, exclude methods/models/datasets/tools unless explicitly requested, set a maximum variable count, and define empty-string behavior when nothing relevant is found.
- Keep the user-approved extraction prompt as the task authority. Use topic-specific gates only to reduce obvious noise, not to override a clearly approved broad or high-recall task.
- For variable-like extraction tasks across geography, urban studies, remote sensing, economic analysis, built-environment research, visual perception, or related domains, use high recall for exact variable spans. Include named variables, indicators, indices, metrics, scores, factors, constructs, measures, predictors, or requested outcomes when the abstract studies, evaluates, models, explains, predicts, correlates, or discusses them as analytical items.
- For geography and urban-analysis tasks, acceptable exact spans may include terms such as `land-use mix`, `accessibility`, `population density`, `road network density`, `street connectivity`, `urban vitality`, `spatial inequality`, `built environment`, and other named urban, spatial, social, environmental, transportation, or economic variables.
- For remote-sensing and economic-analysis tasks, acceptable exact spans may include terms such as `nighttime light`, `NDVI`, `land surface temperature`, `built-up index`, `impervious surface`, `GDP`, `economic activity`, `poverty`, `employment`, `carbon emissions`, and other named remotely sensed, environmental, or socioeconomic indicators.
- For visual, streetscape, landscape, and built-environment perception tasks, acceptable exact spans may include terms such as `greenery index`, `landscape index`, `streetscape quality`, `landscape quality`, `visual quality`, `greenness`, `openness`, `enclosure`, and other visual qualities, perception scores, scene attributes, or appearance-based indicators when they are treated as variables.
- Continue to filter generic container terms that do not name a usable variable, such as `visual features`, `visual elements`, `visual traits`, `physical features`, `objects`, `data`, `information`, `semantic information`, `scene-text information`, `holistic visual data`, and `street-view image variables`, unless the user explicitly approves keeping broad containers.
- If an approved prompt asks for a comma-separated raw answer, convert that answer to a valid JSON array before writing `extracted_variables`.
- Assign every unique original variable to one and only one dimension, then to one and only one subdimension within that dimension.
- Preserve subdimension diversity. Do not over-merge subdimensions when variables focus on different constructs, perceptual qualities, object classes, indicators, scales, or mechanisms. Prefer keeping distinct subdimensions when the variable meanings differ in a way a literature reviewer would want to compare.
- Aim for at least 4 total subdimensions across the whole mapping whenever the extracted variable set supports it, but do not exceed 20 total subdimensions unless the user explicitly approves a larger taxonomy.
- If fewer than 4 meaningful subdimensions are possible because the extracted variables are very sparse or homogeneous, explain that briefly in the draft dimension approval message.
- Do not automatically split subdimension labels by commas or `and`. Use separate subdimension labels only when they represent genuinely different categories within the same dimension.
- Do not create residual catch-all dimensions only to house low-specificity container terms. Remove those terms or ask the user to approve them before dimension mapping.
- Use `1` when an article mentions at least one variable assigned to a dimension; otherwise use `0`.
- Use the same mention ratio in the bar chart and table: articles mentioning the dimension divided by all filtered articles.
- Wait for explicit user approval of dimensions/subdimensions before generating final outputs. If approval is denied, offer to stop or revise the extraction prompt and rerun.
- Leave only four user-facing output files in the final output folder: `final_articles_with_dimensions.csv`, `dimension_original_variables.csv`, a bar chart file, and a styled table file. Prefer PNG on Windows or when plotting libraries are available; use SVG fallback on macOS/Linux when plotting libraries are unavailable.
- Render the bar chart with adaptive width/height based on dimension count and label length; avoid fixed-height canvases that leave large blank areas.
- Store intermediate files in a temporary work folder and remove that folder after the final outputs are created.

## Bundled references

Read `references/workflow.md` when you need exact command examples, expected intermediate files, extraction guidance, mapping format, or output details. Read `references/installation.md` when installing or sharing the skill across Claude Code, Codex, or another `SKILL.md`-compatible agent.
