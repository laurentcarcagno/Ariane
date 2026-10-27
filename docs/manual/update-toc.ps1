# Fills the table of contents with Word (the docx library only writes an empty field) and saves the file.
param([string]$Docx = "$PSScriptRoot\ARIANE-manuel-utilisateur.docx")
$w = New-Object -ComObject Word.Application
$w.Visible = $false; $w.DisplayAlerts = 0
try {
  $doc = $w.Documents.Open($Docx)
  $doc.TablesOfContents.Item(1).Update()
  $doc.Fields.Update() | Out-Null
  $doc.Save(); $doc.Close()
} finally { $w.Quit() }
