param(
    [Parameter(Mandatory = $true)]
    [string]$InputFolder,
    [string]$OutputFolder = "",
    [switch]$InspectOnly,
    [string]$AbstractColumn = "",
    [string]$LanguageColumn = "",
    [string]$LanguageKeep = "",
    [string]$YearColumn = "",
    [Nullable[int]]$YearStart = $null,
    [Nullable[int]]$YearEnd = $null,
    [string]$JournalColumn = "",
    [string]$JournalKeep = "",
    [string]$JournalExclude = "",
    [string]$FilteredName = "filtered_articles.csv",
    [string]$WorklistName = "extraction_worklist.csv",
    [string]$MetadataName = "",
    [string]$InspectName = ""
)

$ErrorActionPreference = "Stop"

$GeneratedFileNames = @(
    "filtered_articles.csv",
    "extraction_worklist.csv",
    "final_articles_with_dimensions.csv",
    "dimension_original_variables.csv"
)

function Normalize-Text {
    param([object]$Value)
    if ($null -eq $Value) { return "" }
    return ([regex]::Replace([string]$Value, "\s+", " ")).Trim()
}

function Normalize-Key {
    param([object]$Value)
    return (Normalize-Text $Value).ToLowerInvariant()
}

function Compact-Key {
    param([object]$Value)
    return [regex]::Replace((Normalize-Key $Value), "[^a-z0-9]+", "")
}

function Split-Values {
    param([string]$Raw)
    if ([string]::IsNullOrWhiteSpace($Raw)) { return @() }
    return @($Raw -split "[|;,]" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Parse-Year {
    param([object]$Value)
    $text = Normalize-Text $Value
    $match = [regex]::Match($text, "\b(18|19|20|21)\d{2}\b")
    if ($match.Success) { return [int]$match.Value }
    return $null
}

function Get-Cell {
    param([object]$Row, [string]$Column)
    if ([string]::IsNullOrWhiteSpace($Column)) { return "" }
    $property = $Row.PSObject.Properties[$Column]
    if ($null -eq $property) { return "" }
    return [string]$property.Value
}

function Get-CsvFiles {
    param([string]$Folder)
    return @(Get-ChildItem -LiteralPath $Folder -Filter "*.csv" -File |
        Where-Object { $GeneratedFileNames -notcontains $_.Name } |
        Sort-Object { $_.Name.ToLowerInvariant() })
}

function Add-FieldOrder {
    param([System.Collections.Generic.List[string]]$FieldOrder, [string[]]$Fields)
    foreach ($field in $Fields) {
        if (-not $FieldOrder.Contains($field)) {
            [void]$FieldOrder.Add($field)
        }
    }
}

function Get-FieldNames {
    param([object[]]$Rows)
    if ($Rows.Count -eq 0) { return @() }
    return @($Rows[0].PSObject.Properties.Name)
}

function Classify-Columns {
    param([string[]]$Columns)
    $candidates = [ordered]@{
        abstract = @()
        language = @()
        year = @()
        journal = @()
    }
    foreach ($column in $Columns) {
        $key = Compact-Key $column
        if ($key -in @("abstract", "ab", "summary") -or $key.Contains("abstract")) {
            $candidates.abstract += $column
        }
        if ($key -in @("language", "lang", "documentlanguage") -or $key.Contains("language")) {
            $candidates.language += $column
        }
        if ($key -in @("year", "publicationyear", "pubyear") -or $key.EndsWith("year")) {
            $candidates.year += $column
        }
        foreach ($token in @("journal", "sourcetitle", "publicationname", "source", "periodical")) {
            if ($key.Contains($token)) {
                $candidates.journal += $column
                break
            }
        }
    }
    return $candidates
}

function Inspect-Headers {
    param([object[]]$CsvFiles)
    $fieldOrder = [System.Collections.Generic.List[string]]::new()
    $columnsByFile = [ordered]@{}
    $rowCounts = [ordered]@{}
    $sampleValues = @{}
    $valueCounts = @{}
    $yearValues = @{}

    foreach ($file in $CsvFiles) {
        $rows = @(Import-Csv -LiteralPath $file.FullName)
        $fields = Get-FieldNames $rows
        Add-FieldOrder $fieldOrder $fields
        $columnsByFile[$file.Name] = @($fields)
        $rowCounts[$file.Name] = $rows.Count

        foreach ($row in $rows) {
            foreach ($field in $fields) {
                $value = Normalize-Text (Get-Cell $row $field)
                if ($value) {
                    if (-not $sampleValues.ContainsKey($field)) { $sampleValues[$field] = @() }
                    if ($sampleValues[$field].Count -lt 8 -and $sampleValues[$field] -notcontains $value) {
                        $sampleValues[$field] += $value
                    }
                    if (-not $valueCounts.ContainsKey($field)) { $valueCounts[$field] = @{} }
                    if (-not $valueCounts[$field].ContainsKey($value)) { $valueCounts[$field][$value] = 0 }
                    $valueCounts[$field][$value] += 1

                    $year = Parse-Year $value
                    if ($null -ne $year) {
                        if (-not $yearValues.ContainsKey($field)) { $yearValues[$field] = @() }
                        $yearValues[$field] += $year
                    }
                }
            }
        }
    }

    $columns = @($fieldOrder.ToArray())
    $candidates = Classify-Columns $columns
    $candidateFilterFields = @($candidates.language + $candidates.year + $candidates.journal)

    $topValues = [ordered]@{}
    foreach ($field in $candidateFilterFields) {
        if (-not $valueCounts.ContainsKey($field)) { continue }
        $topValues[$field] = @($valueCounts[$field].GetEnumerator() |
            Sort-Object @{Expression = "Value"; Descending = $true}, @{Expression = "Key"; Descending = $false} |
            Select-Object -First 30 |
            ForEach-Object { [ordered]@{ value = $_.Key; count = $_.Value } })
    }

    $yearRanges = [ordered]@{}
    foreach ($field in $candidates.year) {
        if ($yearValues.ContainsKey($field) -and $yearValues[$field].Count -gt 0) {
            $values = @($yearValues[$field])
            $yearRanges[$field] = [ordered]@{
                min = ($values | Measure-Object -Minimum).Minimum
                max = ($values | Measure-Object -Maximum).Maximum
            }
        }
    }

    $filteredSamples = [ordered]@{}
    foreach ($field in $candidateFilterFields) {
        if ($sampleValues.ContainsKey($field)) {
            $filteredSamples[$field] = @($sampleValues[$field])
        }
    }

    return [ordered]@{
        csv_files = @($CsvFiles | ForEach-Object { $_.Name })
        row_counts = $rowCounts
        columns = $columns
        columns_by_file = $columnsByFile
        candidates = $candidates
        available_filters = [ordered]@{
            language = ($candidates.language.Count -gt 0)
            year = ($candidates.year.Count -gt 0)
            journal = ($candidates.journal.Count -gt 0)
        }
        sample_values = $filteredSamples
        top_values = $topValues
        year_ranges = $yearRanges
    }
}

function Test-RowPassesFilters {
    param([object]$Row)
    $abstract = Normalize-Text (Get-Cell $Row $AbstractColumn)
    if (-not $abstract) { return @{ keep = $false; reason = "empty_abstract" } }

    $languageValues = @(Split-Values $LanguageKeep | ForEach-Object { Normalize-Key $_ })
    if ($LanguageColumn -and $languageValues.Count -gt 0) {
        if ($languageValues -notcontains (Normalize-Key (Get-Cell $Row $LanguageColumn))) {
            return @{ keep = $false; reason = "language" }
        }
    }

    if ($YearColumn -and ($null -ne $YearStart -or $null -ne $YearEnd)) {
        $year = Parse-Year (Get-Cell $Row $YearColumn)
        if ($null -eq $year) { return @{ keep = $false; reason = "year_missing" } }
        if ($null -ne $YearStart -and $year -lt $YearStart) { return @{ keep = $false; reason = "year_before_start" } }
        if ($null -ne $YearEnd -and $year -gt $YearEnd) { return @{ keep = $false; reason = "year_after_end" } }
    }

    $journalKeepValues = @(Split-Values $JournalKeep | ForEach-Object { Normalize-Key $_ })
    if ($JournalColumn -and $journalKeepValues.Count -gt 0) {
        if ($journalKeepValues -notcontains (Normalize-Key (Get-Cell $Row $JournalColumn))) {
            return @{ keep = $false; reason = "journal" }
        }
    }

    $journalExcludeValues = @(Split-Values $JournalExclude | ForEach-Object { Normalize-Key $_ })
    if ($JournalColumn -and $journalExcludeValues.Count -gt 0) {
        if ($journalExcludeValues -contains (Normalize-Key (Get-Cell $Row $JournalColumn))) {
            return @{ keep = $false; reason = "journal_excluded" }
        }
    }

    return @{ keep = $true; reason = "kept" }
}

$resolvedInput = (Resolve-Path -LiteralPath $InputFolder).Path
if (-not (Test-Path -LiteralPath $resolvedInput -PathType Container)) {
    throw "Input folder does not exist or is not a folder: $InputFolder"
}

$csvFiles = @(Get-CsvFiles $resolvedInput)
if ($csvFiles.Count -eq 0) {
    throw "No CSV files found in: $resolvedInput"
}

if ($InspectOnly) {
    $inspection = Inspect-Headers $csvFiles
    if ($OutputFolder -and $InspectName) {
        New-Item -ItemType Directory -Force -Path $OutputFolder | Out-Null
        $inspectPath = Join-Path $OutputFolder $InspectName
        $inspection | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $inspectPath -Encoding UTF8
        $inspection["outputs"] = [ordered]@{ column_inspection = (Resolve-Path -LiteralPath $inspectPath).Path }
    }
    $inspection | ConvertTo-Json -Depth 12
    exit 0
}

if (-not $AbstractColumn) { throw "Missing required -AbstractColumn. Run -InspectOnly first if you need column suggestions." }
if (-not $OutputFolder) { throw "Missing required -OutputFolder." }

New-Item -ItemType Directory -Force -Path $OutputFolder | Out-Null
$fieldOrder = [System.Collections.Generic.List[string]]::new()
$allSourceRows = @()

foreach ($file in $csvFiles) {
    $rows = @(Import-Csv -LiteralPath $file.FullName)
    $fields = Get-FieldNames $rows
    Add-FieldOrder $fieldOrder $fields
    for ($index = 0; $index -lt $rows.Count; $index++) {
        $allSourceRows += [pscustomobject]@{
            File = $file
            SourceRow = $index + 2
            Row = $rows[$index]
        }
    }
}

$columns = @($fieldOrder.ToArray())
if ($columns -notcontains $AbstractColumn) {
    throw "Abstract column '$AbstractColumn' was not found. Available columns: $($columns -join ', ')"
}

$filteredRows = @()
$worklistRows = @()
$sourceCounts = [ordered]@{}
$filterCounts = [ordered]@{}
foreach ($file in $csvFiles) { $sourceCounts[$file.Name] = 0 }

foreach ($entry in $allSourceRows) {
    $result = Test-RowPassesFilters $entry.Row
    if (-not $filterCounts.Contains($result.reason)) { $filterCounts[$result.reason] = 0 }
    $filterCounts[$result.reason] += 1
    if (-not $result.keep) { continue }

    $ordered = [ordered]@{}
    foreach ($field in $columns) {
        $ordered[$field] = Get-Cell $entry.Row $field
    }
    $filteredRows += [pscustomobject]$ordered

    $worklistRows += [pscustomobject][ordered]@{
        row_index = [string]($filteredRows.Count - 1)
        source_file = $entry.File.Name
        source_row = [string]$entry.SourceRow
        abstract = Normalize-Text (Get-Cell $entry.Row $AbstractColumn)
    }
    $sourceCounts[$entry.File.Name] += 1
}

$filteredPath = Join-Path $OutputFolder $FilteredName
$worklistPath = Join-Path $OutputFolder $WorklistName
$filteredRows | Export-Csv -LiteralPath $filteredPath -NoTypeInformation -Encoding UTF8
$worklistRows | Export-Csv -LiteralPath $worklistPath -NoTypeInformation -Encoding UTF8

$metadata = [ordered]@{
    input_folder = $resolvedInput
    output_folder = (Resolve-Path -LiteralPath $OutputFolder).Path
    csv_files = @($csvFiles | ForEach-Object { $_.Name })
    total_rows_read = $allSourceRows.Count
    filtered_rows_kept = $filteredRows.Count
    source_counts = $sourceCounts
    filter_counts = $filterCounts
    abstract_column = $AbstractColumn
    original_columns = $columns
    outputs = [ordered]@{
        filtered_articles = (Resolve-Path -LiteralPath $filteredPath).Path
        extraction_worklist = (Resolve-Path -LiteralPath $worklistPath).Path
    }
}

if ($MetadataName) {
    $metadataPath = Join-Path $OutputFolder $MetadataName
    $metadata | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $metadataPath -Encoding UTF8
}

$metadata | ConvertTo-Json -Depth 12
