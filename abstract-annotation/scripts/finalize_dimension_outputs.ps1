param(
    [Parameter(Mandatory = $true)]
    [string]$ArticlesCsv,
    [Parameter(Mandatory = $true)]
    [string]$MappingCsv,
    [Parameter(Mandatory = $true)]
    [string]$OutputFolder,
    [string]$ExtractionsCsv = "",
    [string]$ExtractedColumn = "extracted_variables",
    [string]$TopicLabel = "",
    [string]$FinalName = "final_articles_with_dimensions.csv",
    [string]$ChartName = "dimension_mention_ratio_barplot.png",
    [string]$TableName = "dimension_mention_ratio_table.png",
    [string]$DimensionVariablesName = "dimension_original_variables.csv",
    [string]$CleanupWorkFolder = ""
)

$ErrorActionPreference = "Stop"

function Normalize-Text {
    param([object]$Value)
    if ($null -eq $Value) { return "" }
    return ([regex]::Replace([string]$Value, "\s+", " ")).Trim()
}

function Normalize-Variable {
    param([object]$Value)
    $text = (Normalize-Text $Value).ToLowerInvariant()
    $text = [regex]::Replace($text, "^[`\"'']+|[`\"'',.;:]+$", "")
    return ([regex]::Replace($text, "\s+", " ")).Trim()
}

function Get-Cell {
    param([object]$Row, [string]$Column)
    if ([string]::IsNullOrWhiteSpace($Column)) { return "" }
    $property = $Row.PSObject.Properties[$Column]
    if ($null -eq $property) { return "" }
    return [string]$property.Value
}

function Get-FieldNames {
    param([object[]]$Rows)
    if ($Rows.Count -eq 0) { return @() }
    return @($Rows[0].PSObject.Properties.Name)
}

function Compact-Key {
    param([object]$Value)
    return [regex]::Replace((Normalize-Text $Value).ToLowerInvariant(), "[^a-z0-9]+", "")
}

function Get-MatchingColumn {
    param([string[]]$Fields, [string[]]$Names)
    $lookup = @{}
    foreach ($field in $Fields) {
        $lookup[(Compact-Key $field)] = $field
    }
    foreach ($name in $Names) {
        $key = Compact-Key $name
        if ($lookup.ContainsKey($key)) { return $lookup[$key] }
    }
    return ""
}

function Split-Values {
    param([string]$Raw)
    $text = Normalize-Text $Raw
    if (-not $text) { return @() }
    if ($text.StartsWith("[")) {
        try {
            $parsed = ConvertFrom-Json -InputObject $text
            if ($null -ne $parsed) {
                return @($parsed | ForEach-Object { Normalize-Text $_ } | Where-Object { $_ })
            }
        } catch {
        }
    }
    return @($text -split "[|;`n]" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Load-Mapping {
    param([string]$Path)
    $rows = @(Import-Csv -LiteralPath $Path)
    if ($rows.Count -eq 0) { throw "Mapping CSV has no rows." }
    $fields = Get-FieldNames $rows
    $dimensionColumn = Get-MatchingColumn $fields @("dimension")
    $subdimensionColumn = Get-MatchingColumn $fields @("subdimension", "sub_dimension", "sub-dimension")
    $variableColumn = Get-MatchingColumn $fields @("variable")
    $variablesColumn = Get-MatchingColumn $fields @("variables", "original variables", "original_variables")

    if (-not $dimensionColumn -or -not $subdimensionColumn) {
        throw "Mapping CSV must include Dimension and Subdimension columns."
    }

    $dimensions = [ordered]@{}
    $variableMap = @{}
    $variableAssignments = [ordered]@{}

    foreach ($row in $rows) {
        $dimension = Normalize-Text (Get-Cell $row $dimensionColumn)
        $subdimension = Normalize-Text (Get-Cell $row $subdimensionColumn)
        if (-not $dimension) { continue }
        if (-not $subdimension) { $subdimension = "Unspecified" }

        if (-not $dimensions.Contains($dimension)) {
            $dimensions[$dimension] = [System.Collections.Generic.List[string]]::new()
        }
        if (-not $dimensions[$dimension].Contains($subdimension)) {
            [void]$dimensions[$dimension].Add($subdimension)
        }

        $variables = @()
        if ($variableColumn) { $variables += Split-Values (Get-Cell $row $variableColumn) }
        if ($variablesColumn) { $variables += Split-Values (Get-Cell $row $variablesColumn) }

        foreach ($variable in $variables) {
            $key = Normalize-Variable $variable
            if ($key) {
                $variableMap[$key] = [pscustomobject]@{
                    Dimension = $dimension
                    Subdimension = $subdimension
                }
                $variableAssignments[$key] = [pscustomobject]@{
                    Dimension = $dimension
                    Subdimension = $subdimension
                    OriginalVariable = (Normalize-Text $variable)
                }
            }
        }
    }

    if ($dimensions.Count -eq 0) { throw "Mapping CSV did not contain any dimensions." }
    if ($variableMap.Count -eq 0) { throw "Mapping CSV did not contain any variables to map." }
    return [pscustomobject]@{
        Dimensions = $dimensions
        VariableMap = $variableMap
        VariableAssignments = $variableAssignments
    }
}

function Merge-Extractions {
    param([object[]]$Articles, [string]$Path, [string]$ColumnName)
    $rows = @(Import-Csv -LiteralPath $Path)
    if ($rows.Count -eq 0) { throw "Extractions CSV has no rows." }
    $fields = Get-FieldNames $rows
    if ($fields -notcontains $ColumnName) { throw "Extractions CSV must include '$ColumnName'." }

    if ($fields -contains "row_index") {
        foreach ($row in $rows) {
            $indexText = Normalize-Text (Get-Cell $row "row_index")
            $index = 0
            if ([int]::TryParse($indexText, [ref]$index) -and $index -ge 0 -and $index -lt $Articles.Count) {
                $Articles[$index] | Add-Member -NotePropertyName $ColumnName -NotePropertyValue (Get-Cell $row $ColumnName) -Force
            }
        }
    } else {
        if ($rows.Count -ne $Articles.Count) {
            throw "Extractions CSV has no row_index column and its row count does not match the article CSV."
        }
        for ($i = 0; $i -lt $Articles.Count; $i++) {
            $Articles[$i] | Add-Member -NotePropertyName $ColumnName -NotePropertyValue (Get-Cell $rows[$i] $ColumnName) -Force
        }
    }
}

function Build-Outputs {
    param(
        [object[]]$Articles,
        [string[]]$OriginalFields,
        [System.Collections.Specialized.OrderedDictionary]$Dimensions,
        [hashtable]$VariableMap,
        [string]$ColumnName
    )

    $dimensionCounts = [ordered]@{}
    foreach ($dimension in $Dimensions.Keys) { $dimensionCounts[$dimension] = 0 }

    $enrichedRows = @()
    foreach ($article in $Articles) {
        $variables = @(Split-Values (Get-Cell $article $ColumnName))
        $mentionedDimensions = @{}
        foreach ($variable in $variables) {
            $key = Normalize-Variable $variable
            if ($VariableMap.ContainsKey($key)) {
                $mentionedDimensions[$VariableMap[$key].Dimension] = $true
            }
        }

        foreach ($dimension in $mentionedDimensions.Keys) {
            $dimensionCounts[$dimension] += 1
        }

        $ordered = [ordered]@{}
        foreach ($field in $OriginalFields) {
            if ($field -ne $ColumnName -and -not $Dimensions.Contains($field)) {
                $ordered[$field] = Get-Cell $article $field
            }
        }
        $ordered[$ColumnName] = ConvertTo-Json -InputObject @($variables | ForEach-Object { Normalize-Text $_ } | Where-Object { $_ }) -Compress
        foreach ($dimension in $Dimensions.Keys) {
            $ordered[$dimension] = if ($mentionedDimensions.ContainsKey($dimension)) { "1" } else { "0" }
        }
        $enrichedRows += [pscustomobject]$ordered
    }

    $summaryRows = @()
    $denominator = [math]::Max($Articles.Count, 1)
    foreach ($dimension in $Dimensions.Keys) {
        $ratio = [double]$dimensionCounts[$dimension] / [double]$denominator
        $summaryRows += [pscustomobject]@{
            Dimension = $dimension
            Subdimension = ($Dimensions[$dimension].ToArray() -join " | ")
            MentionRatio = "{0:N1} %" -f ($ratio * 100)
            Ratio = $ratio
        }
    }
    $summaryRows = @($summaryRows | Sort-Object -Property Ratio -Descending)

    return [pscustomobject]@{
        Rows = $enrichedRows
        Summary = $summaryRows
    }
}

function Load-Drawing {
    try {
        Add-Type -AssemblyName System.Drawing
    } catch {
        throw "PowerShell PNG rendering requires Windows System.Drawing. Run this in Windows PowerShell or use the cross-platform python3 fallback."
    }
}

function New-Font {
    param([float]$Size, [string]$Style = "Regular")
    $fontStyle = [System.Drawing.FontStyle]::$Style
    return [System.Drawing.Font]::new("Segoe UI", $Size, $fontStyle)
}

function Save-BarChart {
    param([string]$Path, [object[]]$SummaryRows, [string]$Topic)
    Load-Drawing
    $longestLabel = 0
    foreach ($row in $SummaryRows) {
        if ($row.Dimension.Length -gt $longestLabel) { $longestLabel = $row.Dimension.Length }
    }
    $left = [Math]::Min(500, [Math]::Max(280, 54 + ($longestLabel * 7)))
    $right = 120
    $top = 58
    $barHeight = 21
    $gap = 13
    $rowStep = $barHeight + $gap
    $bottom = 64
    $plotWidth = [Math]::Max(560, [Math]::Min(920, 700 + ($SummaryRows.Count * 12)))
    $width = $left + $plotWidth + $right
    $axisY = $top + ($SummaryRows.Count * $rowStep) - $gap + 12
    $height = [Math]::Max(240, $axisY + $bottom)
    $bitmap = [System.Drawing.Bitmap]::new($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.Clear([System.Drawing.Color]::White)

    $titleFont = New-Font 12 "Regular"
    $labelFont = New-Font 9 "Regular"
    $axisFont = New-Font 10 "Regular"
    $barBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(31, 119, 180))
    $textBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(15, 31, 46))
    $axisPen = [System.Drawing.Pen]::new([System.Drawing.Color]::Black, 1)
    $gridPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(230, 234, 240), 1)

    $title = "Proportion of Mentions across Different Dimensions"
    if ($Topic) { $title += " under the Topic of $Topic" }
    $titleSize = $graphics.MeasureString($title, $titleFont)
    $graphics.DrawString($title, $titleFont, $textBrush, [Math]::Max(12, ($width - $titleSize.Width) / 2), 14)

    $maxRatio = 0.05
    foreach ($row in $SummaryRows) { if ($row.Ratio -gt $maxRatio) { $maxRatio = $row.Ratio } }
    $xMax = [Math]::Min(1.08, [Math]::Max(0.10, $maxRatio + 0.08))

    foreach ($tick in @(0, 0.25, 0.50, 0.75, 1.00)) {
        if ($tick -gt $xMax) { continue }
        $x = $left + (($tick / $xMax) * $plotWidth)
        $graphics.DrawLine($gridPen, $x, $top - 7, $x, $axisY)
    }

    for ($i = 0; $i -lt $SummaryRows.Count; $i++) {
        $row = $SummaryRows[$i]
        $y = $top + ($i * $rowStep)
        $labelSize = $graphics.MeasureString($row.Dimension, $labelFont)
        $graphics.DrawString($row.Dimension, $labelFont, $textBrush, $left - $labelSize.Width - 12, $y + 2)
        $barWidth = [Math]::Max(1, [int](($row.Ratio / $xMax) * $plotWidth))
        $graphics.FillRectangle($barBrush, $left, $y, $barWidth, $barHeight)
        $graphics.DrawString(("{0:N1}%" -f ($row.Ratio * 100)), $labelFont, $textBrush, $left + $barWidth + 8, $y + 1)
    }

    $graphics.DrawLine($axisPen, $left, $axisY, $left + $plotWidth, $axisY)
    foreach ($tick in @(0, 0.25, 0.50, 0.75, 1.00)) {
        if ($tick -gt $xMax) { continue }
        $x = $left + (($tick / $xMax) * $plotWidth)
        $graphics.DrawLine($axisPen, $x, $axisY, $x, $axisY + 4)
        $tickText = "{0:0.##}" -f $tick
        $tickSize = $graphics.MeasureString($tickText, $labelFont)
        $graphics.DrawString($tickText, $labelFont, $textBrush, $x - ($tickSize.Width / 2), $axisY + 7)
    }
    $xLabel = "Proportion of Articles Mentioning Dimension"
    $xLabelSize = $graphics.MeasureString($xLabel, $axisFont)
    $graphics.DrawString($xLabel, $axisFont, $textBrush, $left + (($plotWidth - $xLabelSize.Width) / 2), $axisY + 28)

    $graphics.Dispose()
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
}

function Get-WrappedLines {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [float]$MaxWidth
    )
    $words = @((Normalize-Text $Text) -split " ")
    $lines = [System.Collections.Generic.List[string]]::new()
    $current = ""
    foreach ($word in $words) {
        if (-not $word) { continue }
        $candidate = if ($current) { "$current $word" } else { $word }
        if ($Graphics.MeasureString($candidate, $Font).Width -le $MaxWidth -or -not $current) {
            $current = $candidate
        } else {
            [void]$lines.Add($current)
            $current = $word
        }
    }
    if ($current) { [void]$lines.Add($current) }
    if ($lines.Count -eq 0) { [void]$lines.Add("") }
    return @($lines.ToArray())
}

function Draw-RichSeparatorText {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$Line,
        [System.Drawing.Font]$RegularFont,
        [System.Drawing.Font]$BoldFont,
        [System.Drawing.Brush]$Brush,
        [float]$X,
        [float]$Y
    )
    $xPos = $X
    foreach ($part in [regex]::Split($Line, "(\|)")) {
        if ($part -eq "") { continue }
        $font = if ($part -eq "|") { $BoldFont } else { $RegularFont }
        $Graphics.DrawString($part, $font, $Brush, $xPos, $Y)
        $xPos += $Graphics.MeasureString($part, $font).Width - 2
    }
}

function Save-TableImage {
    param([string]$Path, [object[]]$SummaryRows)
    Load-Drawing
    $width = 1600
    $margin = 28
    $dimensionWidth = 450
    $ratioWidth = 150
    $subdimensionWidth = $width - (2 * $margin) - $dimensionWidth - $ratioWidth
    $headerHeight = 46
    $padding = 14

    $regularFont = New-Font 10 "Regular"
    $boldFont = New-Font 10 "Bold"
    $headerFont = New-Font 11 "Bold"

    $measureBitmap = [System.Drawing.Bitmap]::new(10, 10)
    $measureGraphics = [System.Drawing.Graphics]::FromImage($measureBitmap)
    $lineHeight = [Math]::Ceiling($measureGraphics.MeasureString("Ag", $regularFont).Height)

    $prepared = @()
    $totalHeight = $margin + $headerHeight
    foreach ($row in $SummaryRows) {
        $dimensionLines = @(Get-WrappedLines $measureGraphics $row.Dimension $regularFont ($dimensionWidth - (2 * $padding)))
        $subText = $row.Subdimension -replace " \| ", " | "
        $subdimensionLines = @(Get-WrappedLines $measureGraphics $subText $regularFont ($subdimensionWidth - (2 * $padding)))
        $lineCount = [Math]::Max($dimensionLines.Count, $subdimensionLines.Count)
        $rowHeight = [Math]::Max(60, ($lineCount * ($lineHeight + 3)) + (2 * $padding))
        $prepared += [pscustomobject]@{
            Row = $row
            DimensionLines = $dimensionLines
            SubdimensionLines = $subdimensionLines
            Height = $rowHeight
        }
        $totalHeight += $rowHeight
    }
    $totalHeight += $margin
    $measureGraphics.Dispose()
    $measureBitmap.Dispose()

    $bitmap = [System.Drawing.Bitmap]::new($width, $totalHeight)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.Clear([System.Drawing.Color]::White)

    $headerBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(36, 49, 58))
    $whiteBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
    $textBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(15, 31, 46))
    $altBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(243, 246, 250))
    $borderPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(216, 222, 230), 1)

    $x1 = $margin
    $x2 = $x1 + $dimensionWidth
    $x3 = $x2 + $subdimensionWidth
    $y = $margin

    $graphics.FillRectangle($headerBrush, $x1, $y, $width - (2 * $margin), $headerHeight)
    $graphics.DrawString("Dimension", $headerFont, $whiteBrush, $x1 + $padding, $y + 12)
    $graphics.DrawString("Subdimension", $headerFont, $whiteBrush, $x2 + $padding, $y + 12)
    $graphics.DrawString("Mention Ratio", $headerFont, $whiteBrush, $x3 + $padding, $y + 12)
    $graphics.DrawRectangle($borderPen, $x1, $y, $width - (2 * $margin), $headerHeight)
    $y += $headerHeight

    for ($i = 0; $i -lt $prepared.Count; $i++) {
        $entry = $prepared[$i]
        if ($i % 2 -eq 1) {
            $graphics.FillRectangle($altBrush, $x1, $y, $width - (2 * $margin), $entry.Height)
        }
        $graphics.DrawRectangle($borderPen, $x1, $y, $dimensionWidth, $entry.Height)
        $graphics.DrawRectangle($borderPen, $x2, $y, $subdimensionWidth, $entry.Height)
        $graphics.DrawRectangle($borderPen, $x3, $y, $ratioWidth, $entry.Height)

        $textY = $y + $padding
        foreach ($line in $entry.DimensionLines) {
            $graphics.DrawString($line, $regularFont, $textBrush, $x1 + $padding, $textY)
            $textY += $lineHeight + 3
        }

        $textY = $y + $padding
        foreach ($line in $entry.SubdimensionLines) {
            Draw-RichSeparatorText $graphics $line $regularFont $boldFont $textBrush ($x2 + $padding) $textY
            $textY += $lineHeight + 3
        }

        $ratio = $entry.Row.MentionRatio
        $ratioSize = $graphics.MeasureString($ratio, $regularFont)
        $graphics.DrawString($ratio, $regularFont, $textBrush, $x3 + $ratioWidth - $padding - $ratioSize.Width, $y + (($entry.Height - $ratioSize.Height) / 2))
        $y += $entry.Height
    }

    $graphics.Dispose()
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
}

function Cleanup-WorkFolder {
    param([string]$Path)
    if (-not $Path) { return "" }
    $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue)
    if ($null -eq $resolved) { return "" }
    $folder = Get-Item -LiteralPath $resolved.Path
    if (-not $folder.PSIsContainer) { throw "Cleanup target is not a folder: $($folder.FullName)" }
    if ($folder.Name -ne ".abstract_annotation_work") {
        throw "Refusing to clean up a folder not named .abstract_annotation_work."
    }
    Remove-Item -LiteralPath $folder.FullName -Recurse -Force
    return $folder.FullName
}

New-Item -ItemType Directory -Force -Path $OutputFolder | Out-Null
$articles = @(Import-Csv -LiteralPath $ArticlesCsv)
if ($articles.Count -eq 0) { throw "Article CSV has no rows." }
$articleFields = Get-FieldNames $articles

if ($ExtractionsCsv) {
    Merge-Extractions $articles $ExtractionsCsv $ExtractedColumn
} elseif ($articleFields -notcontains $ExtractedColumn) {
    throw "Article CSV must include '$ExtractedColumn' or provide -ExtractionsCsv."
}

$mapping = Load-Mapping $MappingCsv
$built = Build-Outputs $articles $articleFields $mapping.Dimensions $mapping.VariableMap $ExtractedColumn

$finalPath = Join-Path $OutputFolder $FinalName
$chartPath = Join-Path $OutputFolder $ChartName
$tablePath = Join-Path $OutputFolder $TableName
$dimensionVariablesPath = Join-Path $OutputFolder $DimensionVariablesName

$built.Rows | Export-Csv -LiteralPath $finalPath -NoTypeInformation -Encoding UTF8
$dimensionOrder = @{}
$subdimensionOrder = @{}
$separator = [char]31
$dimensionIndex = 0
foreach ($dimension in $mapping.Dimensions.Keys) {
    $dimensionOrder[$dimension] = $dimensionIndex
    $subIndex = 0
    foreach ($subdimension in $mapping.Dimensions[$dimension]) {
        $subdimensionOrder["$dimension$separator$subdimension"] = $subIndex
        $subIndex += 1
    }
    $dimensionIndex += 1
}
$dimensionVariableRows = @(
    $mapping.VariableAssignments.Values |
        ForEach-Object {
            $dimensionRank = $dimensionOrder[$_.Dimension]
            if ($null -eq $dimensionRank) { $dimensionRank = [int]::MaxValue }
            $subdimensionRank = $subdimensionOrder["$($_.Dimension)$separator$($_.Subdimension)"]
            if ($null -eq $subdimensionRank) { $subdimensionRank = [int]::MaxValue }
            [pscustomobject][ordered]@{
                SortDimension = $dimensionRank
                SortSubdimension = $subdimensionRank
                Dimension = $_.Dimension
                Subdimension = $_.Subdimension
                OriginalVariable = $_.OriginalVariable
            }
        } |
        Sort-Object -Property SortDimension, SortSubdimension, OriginalVariable |
        ForEach-Object {
            [pscustomobject][ordered]@{
                Dimension = $_.Dimension
                Subdimension = $_.Subdimension
                "Original Variable" = $_.OriginalVariable
            }
        }
)
$dimensionVariableRows | Export-Csv -LiteralPath $dimensionVariablesPath -NoTypeInformation -Encoding UTF8
Save-BarChart $chartPath $built.Summary $TopicLabel
Save-TableImage $tablePath $built.Summary
$cleaned = Cleanup-WorkFolder $CleanupWorkFolder

$outputs = [ordered]@{
    final_csv = (Resolve-Path -LiteralPath $finalPath).Path
    bar_chart = (Resolve-Path -LiteralPath $chartPath).Path
    table_image = (Resolve-Path -LiteralPath $tablePath).Path
    dimension_variables_csv = (Resolve-Path -LiteralPath $dimensionVariablesPath).Path
    article_count = $articles.Count
    dimension_count = $mapping.Dimensions.Count
}
if ($cleaned) { $outputs["cleaned_work_folder"] = $cleaned }

$outputs | ConvertTo-Json -Depth 8
