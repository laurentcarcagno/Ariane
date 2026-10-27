# Renders the sheets of exemple-export.xlsx to PDF with Excel (one PDF per sheet, first rows only); render-xlsx.py turns them into the PNG of the manual.
param([string]$Xlsx = "$PSScriptRoot\exemple-export.xlsx", [string]$Out = "$PSScriptRoot\img\pdf")
New-Item -ItemType Directory -Force $Out | Out-Null
$rows = @{ "Page de garde" = 53; "From-To" = 22; "Connecteurs" = 22; "Segments" = 22; "Nomenclature" = 22; "Rapport" = 22 }
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
try {
  $wb = $xl.Workbooks.Open($Xlsx)
  foreach ($ws in $wb.Worksheets) {
    $last = $ws.UsedRange.Columns.Count
    $col = $ws.UsedRange.Column + $last - 1
    $ws.PageSetup.PrintArea = $ws.Range($ws.Cells(1, 1), $ws.Cells($rows[$ws.Name], $col)).Address()
    $ws.PageSetup.Orientation = if ($ws.Name -eq "Page de garde") { 1 } else { 2 }
    $ws.PageSetup.Zoom = $false; $ws.PageSetup.FitToPagesWide = 1; $ws.PageSetup.FitToPagesTall = 1
    $ws.ExportAsFixedFormat(0, (Join-Path $Out (($ws.Name -replace " ", "_") + ".pdf")))
  }
  $wb.Close($false)
} finally { $xl.Quit() }
