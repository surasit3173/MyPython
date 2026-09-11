param(
    [Parameter(Mandatory = $true)]
    [string]$DocxPath,
    [Parameter(Mandatory = $true)]
    [string]$PdfPath
)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($DocxPath, $false, $true)
    $doc.ExportAsFixedFormat($PdfPath, 17)
    $doc.Close($false)
}
finally {
    $word.Quit()
}
Write-Output $PdfPath
