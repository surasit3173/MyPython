param(
    [Parameter(Mandatory = $true)]
    [string]$InputDocx,
    [Parameter(Mandatory = $true)]
    [string]$OutputPdf
)

$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$word.AutomationSecurity = 3

try {
    $doc = $word.Documents.Open($InputDocx, $false, $true)
    try {
        $doc.ExportAsFixedFormat($OutputPdf, 17)
    }
    finally {
        $doc.Close(0)
        [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($doc) | Out-Null
    }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
}

Get-Item -LiteralPath $OutputPdf | Select-Object FullName, Length, LastWriteTime
