# Abstract Annotation Workflow Reference

This reference is for agents using the `abstract-annotation` skill. Keep all user-facing workflow text in English.

## Runtime preference

On Windows, use the bundled PowerShell scripts first. They do not require Python:

- `scripts/read_and_filter_csvs.ps1`
- `scripts/finalize_dimension_outputs.ps1`

On macOS or Linux, use `python3` with the bundled Python scripts:

- `scripts/read_and_filter_csvs.py`
- `scripts/finalize_dimension_outputs.py`

The Python read/filter script uses only the standard library. The Python finalization script tries `matplotlib` for PNG outputs. If `matplotlib` is unavailable, it automatically writes SVG fallback files:

- `dimension_mention_ratio_barplot.svg`
- `dimension_mention_ratio_table.svg`

For the table fallback, SVG is the default. HTML is also supported if the command explicitly sets `--table-name dimension_mention_ratio_table.html`.

PNG is preferred on Windows or when plotting libraries are available. SVG fallback is preferred for cross-platform use without extra dependencies.

## Runtime questions

Ask one question at a time. Do not ask the user to reply to multiple numbered questions in one message.

Ask only for the input folder before inspecting headers. Then inspect the CSV columns and ask the remaining questions conditionally.

1. Which folder contains the CSV files?
2. What type of extraction task should be applied to every abstract?
   - Methods used in each study.
   - Variables influencing, explaining, predicting, or correlating with a topic.
   - Datasets or data sources used in each study.
   - A custom task.
3. What is the one-sentence extraction goal? Example: `variables influencing retail vitality`.
4. Show an expanded extraction prompt and ask: `Use this extraction prompt?` Choices: `Approve` or `Edit prompt`.
5. If an abstract candidate is detected, ask: `Use <column> as the abstract column?` Choices: `Yes` or `Enter another column name`. If no abstract candidate is detected, show all columns and ask the user to enter the abstract column.
6. If a language column candidate exists, ask: `Which languages should be kept?` Choices: `Keep all languages` or `Keep only English`.
7. If a year column candidate exists, show its detected range from `year_ranges`, then ask: `Which years should be kept?` Choices: `Keep all years (<min>-<max>)` or `Enter a year range`.
8. If a journal/source-title column candidate exists, ask: `Which source titles should be kept?` Choices: `Keep all source titles`, `Include only specific source titles`, or `Exclude specific source titles`.
9. Where should the final outputs be written?

Do not ask about a filter when no related column is detected. Say briefly that the filter was skipped because no matching column was found.

Use a temporary work folder for intermediate files, such as:

```text
<final-output-folder>\.abstract_annotation_work
```

Remove the temporary work folder after the final outputs are created. The final output folder should only contain the final article CSV, original-variable assignment CSV, bar chart, and table image created by this workflow.

## Step 0: Inspect CSV headers

Run this after the user provides the input folder:

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\read_and_filter_csvs.ps1 `
  -InputFolder "C:\path\to\csv_folder" `
  -InspectOnly
```

macOS/Linux:

```bash
python3 scripts/read_and_filter_csvs.py \
  --input-folder "/path/to/csv_folder" \
  --inspect-only
```

The inspection output includes:

- `columns`: merged column names from all CSV files.
- `candidates.abstract`: likely abstract columns.
- `candidates.language`: likely language columns.
- `candidates.year`: likely year columns.
- `candidates.journal`: likely journal/source-title columns.
- `available_filters`: booleans indicating whether language, year, and journal filters can be offered.
- `sample_values`: example values for candidate filter columns.
- `top_values`: frequent values for candidate language and journal/source-title columns.
- `year_ranges`: detected min/max years for candidate year columns.

Use this output to decide which questions to ask next.

## One-by-one question pattern

Use this sequence after inspection:

```text
What type of extraction task should I apply to every abstract?
Choices: methods | influencing variables | datasets/data sources | custom task
```

```text
In one sentence, what should I extract? For example: variables influencing retail vitality
```

```text
I expanded your task into the extraction prompt below. Use this prompt?
Choices: Approve | Edit prompt
```

```text
I detected `Abstract` as the abstract column. Use this column?
Choices: Yes | Enter another column name
```

```text
I detected `Language` as the language column. Which languages should be kept?
Choices: Keep all languages | Keep only English
```

```text
I detected `Year` as the year column, with years ranging from 2010 to 2024. Which years should be kept?
Choices: Keep all years (2010-2024) | Enter a year range
```

```text
I detected `Source title` as the source-title column. Which source titles should be kept?
Choices: Keep all source titles | Include only specific source titles | Exclude specific source titles
```

```text
Where should I save the final output files?
```

When the user chooses a manual option, ask a follow-up for the exact value before moving to the next question.

## Step 0.5: Refine the extraction prompt

Do not apply a short user phrase directly to article extraction. First convert the chosen task type and one-sentence goal into a complete English extraction prompt, show it to the user, and wait for approval or edits.

For every expanded prompt:

- Address the model as extracting information from academic abstracts, or variables specifically when the selected task is variable extraction.
- State the task in one sentence.
- Define what should be included.
- Define what should be excluded.
- Require exact text spans from the abstract, not paraphrases.
- Prefer short noun phrases when the task is variable-like.
- Set the output shape for the raw extraction answer.
- Define what to return when no relevant item is found.

After approval, use the approved prompt for every row in `extraction_worklist.csv`. If the raw prompt asks for a comma-separated list, convert it to a JSON array before writing `extracted_variables`.

### Influencing-variable prompt builder

Use this template when the task type is `influencing variables`. Replace `<target topic>` with the topic inferred from the user's one-sentence goal. If the user gives a broad phrase such as `retail vitality`, preserve it as the target topic and include close variants only when they are clearly implied by the user's wording, such as `retail vitality or urban vitality`. Use `Maximum 8 variables` by default, but preserve a different maximum when the user explicitly gives one. If the user's goal asks for a high-recall review, use broader include rules and let dimension mapping handle noisy but potentially relevant exact spans. If the user's goal includes `detected from` or `derived from`, interpret that as permission to extract named variables, indicators, indices, metrics, scores, factors, constructs, measures, predictors, or requested outcomes detected or derived in the study.

```text
You are extracting variables from academic abstracts.

Task:
Identify variables that the study examines as factors associated with, correlated with, explaining, predicting, influencing, or affecting <target topic>.

Extract exact spans for variables, indicators, indices, metrics, scores, factors, constructs, measures, predictors, or requested outcomes that are clearly connected to <target topic>. Use high recall when the user asks for broad literature mapping. Examples include, but are not limited to:
- explanatory variables
- influencing factors
- independent variables
- predictors
- indicators, indices, metrics, measures, scores, factors, and constructs
- built environment variables
- geography and urban-analysis variables
- remote-sensing and environmental indicators
- economic and socioeconomic variables
- streetscape, landscape, and visual-perception variables
- land-use variables
- spatial configuration variables
- social or economic contextual variables

Do NOT include:
- the outcome variable itself, such as <target topic> or close outcome synonyms, unless the user explicitly asks to extract outcomes
- broad research topics, methods, models, datasets, or tools
- generic data or feature containers such as data, information, features, variables, indicators, factors, objects, semantic information, visual features, physical features, or street-view image variables unless the user explicitly approves broad containers
- policy recommendations or planning strategies
- variables not clearly connected to <target topic> or correlation/association analysis

Prefer exact short noun phrases copied from the abstract, usually 1 to 3 words.
Return ONLY a comma-separated list.
Maximum 8 variables.
If no relevant variables are found, return an empty string.
Do not explain.
```

For the user goal `variables influencing retail vitality`, generate a prompt like:

```text
You are extracting variables from academic abstracts.

Task:
Identify variables that the study examines as factors associated with, correlated with, explaining, predicting, influencing, or affecting retail vitality or urban vitality.

Extract exact spans for variables, indicators, indices, metrics, scores, factors, constructs, measures, predictors, or requested outcomes that are clearly connected to retail vitality or urban vitality. Examples include, but are not limited to:
- explanatory variables
- influencing factors
- independent variables
- predictors
- indicators, indices, metrics, measures, scores, factors, and constructs
- built environment variables
- geography and urban-analysis variables
- remote-sensing and environmental indicators
- economic and socioeconomic variables
- streetscape, landscape, and visual-perception variables
- land-use variables
- spatial configuration variables
- social or economic contextual variables

Do NOT include:
- the outcome variable itself, such as retail vitality, urban vitality, commercial vitality, unless the user explicitly asks to extract outcomes
- broad research topics, methods, models, datasets, or tools
- generic data or feature containers such as data, information, features, variables, indicators, factors, objects, semantic information, visual features, physical features, or street-view image variables unless the user explicitly approves broad containers
- policy recommendations or planning strategies
- variables not clearly connected to vitality, retail activity, commercial activity, or correlation/association analysis

Prefer exact short noun phrases copied from the abstract, usually 1 to 3 words.
Return ONLY a comma-separated list.
Maximum 8 variables.
If no relevant variables are found, return an empty string.
Do not explain.
```

For the user goal `urban heat risk`, the target topic must become `urban heat risk`; do not keep vitality terms from the example.

### Topic-specific variable gates

Use topic-specific gates after extraction and before writing `extracted_variables`. Gates should reduce obvious noise while respecting the user-approved extraction prompt. Prefer high recall for literature mapping tasks, then let dimension mapping and user approval refine the taxonomy.

Keep exact spans when the abstract treats them as variables, indicators, indices, metrics, scores, factors, constructs, measures, predictors, or requested outcomes.

General geography and urban-analysis examples:

- `land-use mix`
- `accessibility`
- `population density`
- `road network density`
- `street connectivity`
- `urban vitality`
- `spatial inequality`
- `built environment`

Remote-sensing, environmental, and economic-analysis examples:

- `nighttime light`
- `NDVI`
- `land surface temperature`
- `built-up index`
- `impervious surface`
- `GDP`
- `economic activity`
- `poverty`
- `employment`
- `carbon emissions`

Visual, streetscape, landscape, and built-environment perception examples:

- `greenery index`
- `green visual index`
- `landscape index`
- `streetscape quality`
- `landscape quality`
- `visual quality`
- `sky view factor`
- `tree canopy`
- `building height`
- `facade color`
- `signage density`
- `greenness`
- `openness`
- `enclosure`

Remove generic container terms before writing `extracted_variables` unless the user explicitly approves broad containers, including:

- `visual features`
- `visual elements`
- `visual traits`
- `physical features`
- `objects`
- `artificial objects`
- `data`
- `information`
- `features`
- `variables`
- `indicators`
- `factors`
- `semantic information`
- `scene-text information`
- `holistic visual data`
- `street-view image variables`

Do not remove a broad quality or construct term solely because it is broad. Keep terms such as `landscape quality`, `visual quality`, `urban vitality`, or `economic activity` when the abstract clearly studies, evaluates, models, predicts, or correlates them as analytical variables. If an abstract only provides generic container terms and no usable variable-like span, write an empty JSON array for `extracted_variables`.

### Method prompt builder

Use this template when the task type is `methods`:

```text
You are extracting methods from academic abstracts.

Task:
Identify exact method names, analytical techniques, modeling approaches, statistical methods, or computational workflows used in the study for <user goal>.

Extract only methods that are explicitly named in the abstract.

Do NOT include:
- research topics or outcomes
- variables, indicators, datasets, sensors, software, or study locations unless they are part of an exact method name
- vague phrases such as approach, framework, analysis, or method unless a specific named method is provided
- policy recommendations or substantive findings

Prefer exact short method phrases copied from the abstract.
Return ONLY a comma-separated list.
Maximum 8 methods.
If no relevant methods are found, return an empty string.
Do not explain.
```

### Dataset/data-source prompt builder

Use this template when the task type is `datasets/data sources`:

```text
You are extracting data sources from academic abstracts.

Task:
Identify exact datasets, data sources, sensors, platforms, databases, imagery sources, survey sources, or observational sources used in the study for <user goal>.

Extract only data-source phrases that are explicitly named in the abstract.

Do NOT include:
- methods, models, software, variables, outcomes, or study locations unless they are part of an exact data-source name
- vague phrases such as data, dataset, samples, observations, or information unless a specific source is named
- policy recommendations or substantive findings

Prefer exact short source phrases copied from the abstract.
Return ONLY a comma-separated list.
Maximum 8 data sources.
If no relevant data sources are found, return an empty string.
Do not explain.
```

### Custom-task prompt builder

For a custom task, infer the target object and output type from the user's one-sentence goal, then generate a prompt with the same structure:

```text
You are extracting information from academic abstracts.

Task:
<clear rewritten task based on the user's goal>

Extract only:
- <specific included item types>

Do NOT include:
- <specific excluded item types>
- broad research topics, methods, datasets, tools, or outcomes unless the custom task explicitly asks for them
- vague umbrella terms unless specific named items are provided

Use exact text spans copied from the abstract.
Return ONLY a comma-separated list.
Maximum 8 items.
If no relevant items are found, return an empty string.
Do not explain.
```

Always show the expanded prompt before extraction:

```text
I expanded your task into this extraction prompt:

<prompt>

Use this extraction prompt?
Choices: Approve | Edit prompt
```

If the user chooses `Edit prompt`, ask them to provide the revised full prompt, then show it once more for approval before extraction.

## Step 1: Read and filter CSV files

Example command:

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\read_and_filter_csvs.ps1 `
  -InputFolder "C:\path\to\csv_folder" `
  -OutputFolder "C:\path\to\outputs\.abstract_annotation_work" `
  -AbstractColumn "Abstract" `
  -LanguageColumn "Language of Original Document" `
  -LanguageKeep "English" `
  -YearColumn "Year" `
  -YearStart 2015 `
  -YearEnd 2026 `
  -JournalColumn "Source title" `
  -JournalKeep "Cities|Landscape and Urban Planning"
```

macOS/Linux:

```bash
python3 scripts/read_and_filter_csvs.py \
  --input-folder "/path/to/csv_folder" \
  --output-folder "/path/to/outputs/.abstract_annotation_work" \
  --abstract-column "Abstract" \
  --language-column "Language of Original Document" \
  --language-keep "English" \
  --year-column "Year" \
  --year-start 2015 \
  --year-end 2026 \
  --journal-column "Source title" \
  --journal-keep "Cities|Landscape and Urban Planning"
```

To exclude source titles instead:

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\read_and_filter_csvs.ps1 `
  -InputFolder "C:\path\to\csv_folder" `
  -OutputFolder "C:\path\to\outputs\.abstract_annotation_work" `
  -AbstractColumn "Abstract" `
  -JournalColumn "Source title" `
  -JournalExclude "Non-target Journal|Another Journal"
```

macOS/Linux:

```bash
python3 scripts/read_and_filter_csvs.py \
  --input-folder "/path/to/csv_folder" \
  --output-folder "/path/to/outputs/.abstract_annotation_work" \
  --abstract-column "Abstract" \
  --journal-column "Source title" \
  --journal-exclude "Non-target Journal|Another Journal"
```

Temporary work files:

- `filtered_articles.csv`: filtered rows with original columns preserved.
- `extraction_worklist.csv`: `row_index`, source trace columns, and abstract text for extraction.

Omit filter arguments when the user does not want that filter. The files from this step are intermediate work files and should remain in the temporary work folder.

## Step 2: Extract variables

Apply the same approved extraction prompt to every row in `extraction_worklist.csv`.

Write or maintain an extraction CSV with:

```csv
row_index,extracted_variables
0,"[""street connectivity"", ""land use mix""]"
1,"[""nighttime light data"", ""POI data""]"
```

Rules:

- `extracted_variables` must be a valid JSON array string.
- Each value in `extracted_variables` must be an exact text span copied from the abstract.
- If the approved extraction prompt returns a comma-separated raw list, split that list into items, trim whitespace, drop empty items, and write the result as a JSON array string.
- Do not paraphrase, summarize, translate, standardize, lemmatize, or replace an extracted value with a synonym.
- Do not infer a broader variable name when that phrase is not present in the abstract.
- Preserve the abstract's original wording, spelling, hyphenation, and plurality unless trimming surrounding punctuation or whitespace is needed.
- If the exact span is not in English, preserve the original wording from the abstract. Do not translate it into English.
- Do not include locations, methods, datasets, or outcomes unless the chosen task asks for them and the exact phrase appears in the abstract.
- For influence/correlation tasks, extract only exact abstract phrases that are used to influence, explain, predict, assess, or correlate with the target topic.
- For influence/correlation tasks, do not include the target topic or close outcome synonyms as extracted variables unless the user explicitly asks to extract outcomes.
- For variable-like tasks, apply the topic-specific variable gates after extraction and before writing `extracted_variables`. Delete generic data, feature, visual, or semantic container terms unless the user explicitly approved broad containers.
- For method tasks, extract exact method names as written in the abstract.
- For data-source tasks, extract exact dataset, sensor, platform, database, or source-type names as written in the abstract.
- Bad: abstract says `built environment characteristics`, but `extracted_variables` says `urban form`.
- Good: abstract says `street connectivity` and `land use mix`, so `extracted_variables` contains `["street connectivity", "land use mix"]`.

## Step 3: Draft and approve dimensions

Collect unique values from `extracted_variables`, then draft a mapping table for user approval. Dimension and subdimension names may be interpretive summaries, but the `variable` column must keep the exact extracted phrase.

Use this more robust order:

1. Draft the major dimensions from the full set of unique original variables.
2. Assign every original variable to exactly one dimension.
3. For each dimension, review only the variables assigned to that dimension.
4. Summarize those variables into diverse, specific subdimensions. Do not over-merge variables with different substantive meanings.
5. Assign every original variable to exactly one subdimension within its dimension.

The final mapping CSV must have one row per exact original variable assignment:

```csv
variable,dimension,subdimension
street connectivity,Transportation Conditions,Road and Street Network Connectivity
land use mix,Spatial Morphology and Land Use Structure,Land-Use Mix and Functional Diversity
visible vegetation,Greener and Natural Elements,Visible Vegetation
natural views,Greener and Natural Elements,Natural Views
landscape features,Greener and Natural Elements,Landscape Features
```

Do not automatically split subdimension labels by commas or `and`. For example, `Safety, Comfort, Aesthetics, Vitality, and Sensory Response` is one broad subdimension label unless the variables clearly support separate categories. Use the table display separator ` | ` only when there are genuinely different subdimension categories under the same dimension, such as `Visible Vegetation | Natural Views | Landscape Features`.

Subdimension diversity rules:

- Preserve more subdimensions when variables focus on different constructs, perceptual qualities, object classes, indicators, scales, or mechanisms.
- Do not collapse distinct variable foci into one broad label only to simplify the table.
- Aim for at least 4 total subdimensions across the whole mapping whenever the extracted variable set supports it.
- Do not exceed 20 total subdimensions unless the user explicitly asks for or approves a more granular taxonomy.
- If fewer than 4 meaningful subdimensions are possible because the extracted variables are sparse or homogeneous, say so briefly when showing the draft dimensions for approval.
- Keep each original variable assigned to exactly one subdimension; increase subdimension granularity by changing labels and assignments, not by duplicating variables.

Do not create residual or catch-all dimensions solely because generic container terms remain in the variable list. If low-specificity terms such as `features`, `variables`, `indicators`, `data`, `information`, `visual features`, `visual elements`, `objects`, `physical features`, `visual traits`, `holistic visual data`, or `scene-text information` appear at this stage, remove them from the mapping or ask the user to explicitly approve keeping them. Do not give them their own dimension by default.

Show the draft dimensions/subdimensions to the user before finalization. Ask a single choice-style question:

```text
Is this dimension structure acceptable?
Choices: Approve and generate final outputs | No, I want to revise
```

If the user approves, proceed to final output generation.

If the user chooses `No, I want to revise`, ask this follow-up:

```text
How would you like to proceed?
Choices: Stop here | Revise the extraction prompt and rerun extraction
```

If the user chooses `Stop here`, stop without generating final outputs and leave the temporary work files available if they still exist.

If the user chooses `Revise the extraction prompt and rerun extraction`, ask for the revised extraction prompt, rerun extraction on the same filtered articles, regenerate `extracted_variables`, draft a new dimension/subdimension mapping, and return to the approval question.

Do not generate final outputs until the user explicitly chooses `Approve and generate final outputs`.

## Step 4: Generate final outputs

Example command:

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\finalize_dimension_outputs.ps1 `
  -ArticlesCsv "C:\path\to\outputs\.abstract_annotation_work\filtered_articles.csv" `
  -ExtractionsCsv "C:\path\to\outputs\.abstract_annotation_work\extracted_variables.csv" `
  -MappingCsv "C:\path\to\outputs\.abstract_annotation_work\dimension_mapping.csv" `
  -OutputFolder "C:\path\to\outputs" `
  -TopicLabel "Vitality" `
  -CleanupWorkFolder "C:\path\to\outputs\.abstract_annotation_work"
```

macOS/Linux:

```bash
python3 scripts/finalize_dimension_outputs.py \
  --articles-csv "/path/to/outputs/.abstract_annotation_work/filtered_articles.csv" \
  --extractions-csv "/path/to/outputs/.abstract_annotation_work/extracted_variables.csv" \
  --mapping-csv "/path/to/outputs/.abstract_annotation_work/dimension_mapping.csv" \
  --output-folder "/path/to/outputs" \
  --topic-label "Vitality" \
  --cleanup-work-folder "/path/to/outputs/.abstract_annotation_work"
```

Outputs:

- `final_articles_with_dimensions.csv`
- `dimension_original_variables.csv`
- `dimension_mention_ratio_barplot.png`, or `dimension_mention_ratio_barplot.svg` if PNG rendering is unavailable
- `dimension_mention_ratio_table.png`, or `dimension_mention_ratio_table.svg` if PNG rendering is unavailable. Use `dimension_mention_ratio_table.html` only when an HTML table is explicitly requested.

The final CSV appends `extracted_variables` and binary dimension columns after the original columns. The table image has exactly:

```csv
Dimension,Subdimension,Mention Ratio
```

The bar chart and table must use the same mention ratio for each dimension.

The `dimension_original_variables.csv` file is for manual checking and has exactly:

```csv
Dimension,Subdimension,Original Variable
```

It should show which exact original variables were assigned to each dimension and subdimension.

The bar chart should use an adaptive aspect ratio:

- Increase height as the number of dimensions increases.
- Increase left label space when dimension names are long.
- Keep the x-axis label close to the axis.
- Avoid large blank areas below or around the bars.

The table image should use a dark header, alternating row backgrounds, fixed-width cells, automatic wrapping inside each cell, and bold `|` separators between subdimension entries.
