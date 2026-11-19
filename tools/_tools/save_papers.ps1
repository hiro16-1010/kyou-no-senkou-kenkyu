# 論文を保存：ダウンロードフォルダにある「論文保存_*.json」（「今日の先行研究」の「PDFを保存」で作られるファイル）を読み、
# PDFをダウンロードして、ゼミフォルダの「後で読む論文」に「保存日_タイトル.pdf」の名前で保存する。
$ErrorActionPreference = 'Stop'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$dest = Join-Path (Split-Path -Parent $PSScriptRoot) '後で読む論文'   # ゼミフォルダの中の「後で読む論文」
if (-not (Test-Path -LiteralPath $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null }
$downloads = (New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path
$doneDir = Join-Path $downloads '論文保存_処理済み'
$zemi = Split-Path -Parent $PSScriptRoot
# 保存依頼はダウンロードフォルダとゼミフォルダの両方から探す（ブラウザの保存先がどちらでも動くように）
$files = @(foreach ($dir in @($downloads, $zemi)) { if (Test-Path -LiteralPath $dir) { Get-ChildItem -LiteralPath $dir -Filter '論文保存_*.json' -File } }) | Sort-Object LastWriteTime

if ($files.Count -eq 0) {
  Write-Host '保存依頼のファイルがありません。'
  Write-Host 'ページの「PDFを保存」を押して、ダウンロードを許可してから、もう一度実行してください。'
  return
}
if (-not (Test-Path -LiteralPath $doneDir)) { New-Item -ItemType Directory -Path $doneDir | Out-Null }

function Get-SafeName([string]$s) {
  $map = @{ ':' = '：'; '?' = '？'; '*' = '＊'; '"' = '”'; '<' = '＜'; '>' = '＞'; '|' = '｜'; '/' = '／'; '\' = '＼' }
  foreach ($k in $map.Keys) { $s = $s.Replace($k, $map[$k]) }
  $s = ($s -replace '[\x00-\x1f]', '' -replace '\s+', ' ').Trim().TrimEnd('.')
  if ($s.Length -gt 150) { $s = $s.Substring(0, 150).Trim() }
  return $s
}

$ok = 0; $ng = 0
foreach ($f in $files) {
  try {
    $j = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $j.pdfUrl -or -not $j.title) { throw '保存依頼のファイルにタイトルかURLがありません' }
    $date = if ($j.savedDate) { [string]$j.savedDate } else { Get-Date -Format 'yyyyMMdd' }
    $name = "${date}_$(Get-SafeName $j.title).pdf"
    $out = Join-Path $dest $name
    if (Test-Path -LiteralPath $out) {
      Write-Host "すでに保存済みです：$name"
    } else {
      $tmp = "$out.part"
      Invoke-WebRequest -Uri $j.pdfUrl -OutFile $tmp -UseBasicParsing -MaximumRedirection 5 -UserAgent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
      $fs = [IO.File]::OpenRead($tmp); $buf = New-Object byte[] 4; [void]$fs.Read($buf, 0, 4); $fs.Close()
      if ([Text.Encoding]::ASCII.GetString($buf) -ne '%PDF') {
        Remove-Item -LiteralPath $tmp -Force
        throw 'PDFではないページが返りました（ログインが必要か、URLが変わった可能性があります）。ページの「論文ページを開く」から手で保存してください'
      }
      Move-Item -LiteralPath $tmp -Destination $out
      Write-Host "保存しました：$name"
      $ok++
    }
    Move-Item -LiteralPath $f.FullName -Destination (Join-Path $doneDir $f.Name) -Force
  } catch {
    Write-Host "保存できませんでした：$($f.Name)"
    Write-Host "  理由：$($_.Exception.Message)"
    $ng++
  }
}
Write-Host ''
Write-Host "完了：保存 $ok 件、失敗 $ng 件（保存先：$dest）"
