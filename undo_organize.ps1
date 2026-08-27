# ============================================================
# 元に戻すスクリプト
#
# auto_organize.ps1 が移動したファイルを、
# 「移動記録.csv」を見ながら全部元の場所へ戻します。
# ファイルは一切削除しません。
# ============================================================

if (-not $env:OneDrive) {
    Write-Host "OneDrive が設定されていないパソコンです。"
    Write-Host "その場合、整理スクリプトは何も移動できていないので、戻す必要はありません。ご安心ください。"
    return
}

$base = Join-Path $env:OneDrive "お米屋の仕事"
$log  = Join-Path $base "移動記録.csv"

if (-not (Test-Path -LiteralPath $log)) {
    Write-Host "移動の記録が見つかりませんでした。"
    Write-Host "まだ整理を実行していないか、すでに元に戻し済みです。ファイルは移動されていません。"
    return
}

$rows = @(Import-Csv -LiteralPath $log -Encoding UTF8)
Write-Host ("記録を読み込みました: {0} 件" -f $rows.Count)
Write-Host ""

$restored = 0
$notFound = 0

foreach ($row in $rows) {
    $from = $row.移動先
    $to   = $row.元の場所

    if (-not (Test-Path -LiteralPath $from)) {
        $notFound++
        continue
    }

    # 戻し先のフォルダがなければ作る
    $toDir = Split-Path $to -Parent
    if (-not (Test-Path -LiteralPath $toDir)) {
        New-Item -ItemType Directory -Force -Path $toDir | Out-Null
    }

    # 戻し先に同名ファイルがあれば (戻し2) を付けて別名で戻す
    $dest = $to
    $i = 2
    while (Test-Path -LiteralPath $dest) {
        $name = [IO.Path]::GetFileNameWithoutExtension($to)
        $ext  = [IO.Path]::GetExtension($to)
        $dest = Join-Path $toDir ("{0} (戻し{1}){2}" -f $name, $i, $ext)
        $i++
    }

    try {
        Move-Item -LiteralPath $from -Destination $dest
        Write-Host ("  戻しました: {0}" -f (Split-Path $dest -Leaf))
        $restored++
    }
    catch {
        Write-Host ("  戻せませんでした（使用中の可能性）: {0}" -f (Split-Path $from -Leaf))
    }
}

# 記録ファイルの名前を変えて「戻し済み」と分かるようにする
$doneLog = Join-Path $base ("戻し済み記録_{0}.csv" -f (Get-Date -Format "yyyyMMdd_HHmm"))
Move-Item -LiteralPath $log -Destination $doneLog -Force

# 空になったフォルダを片付ける（中身のあるフォルダは絶対に消しません）
$dirs = Get-ChildItem -LiteralPath $base -Recurse -Directory |
    Sort-Object { $_.FullName.Length } -Descending
foreach ($d in $dirs) {
    if (-not (Get-ChildItem -LiteralPath $d.FullName -Force)) {
        Remove-Item -LiteralPath $d.FullName
    }
}

Write-Host ""
Write-Host "============================================"
Write-Host ("完了！ {0} 個のファイルを元の場所に戻しました。" -f $restored)
if ($notFound -gt 0) {
    Write-Host ("※ {0} 件はすでに移動済み・戻し済みのためスキップしました" -f $notFound)
}
Write-Host "デスクトップとダウンロードフォルダを確認してみてください。"
Write-Host "============================================"
