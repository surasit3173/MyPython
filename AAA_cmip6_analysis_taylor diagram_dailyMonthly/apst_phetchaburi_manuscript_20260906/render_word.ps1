$docxPath = Join-Path (Get-Location) 'APST_Phetchaburi_Precipitation_Extremes_Manuscript.docx'
$pdfPath = Join-Path (Get-Location) 'render_word\APST_Phetchaburi_Precipitation_Extremes_Manuscript.pdf'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $pdfPath) | Out-Null
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open((Resolve-Path $docxPath).Path, $false, $true)
$doc.ExportAsFixedFormat($pdfPath, 17, $false, 0, 0, 1, 1, 0, $true, $false, 0, $true, $true, $false)
$doc.Close($false)
$word.Quit()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($doc) | Out-Null
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
Write-Output $pdfPath
