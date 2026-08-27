# ============================================================
# パソコン自動整理スクリプト（お米屋の仕事用）
#
# やること:
#   1. OneDrive に「お米屋の仕事」フォルダ一式を作る
#   2. デスクトップとダウンロードのファイルを種類・年ごとに仕分ける
#
# 安全のためのルール:
#   ・ファイルは一切削除しない（移動するだけ）
#   ・デスクトップのフォルダとショートカットは動かさない
#   ・同じ名前があっても上書きしない（(2) を付けて別名保存）
#   ・何をどこへ移したか「移動記録.csv」に全部残す
# ============================================================

$base = Join-Path $env:OneDrive "お米屋の仕事"
$log  = Join-Path $base "移動記録.csv"

# --- 1. フォルダ一式を作る ---
$folders = @(
    "01_顧客管理\顧客画像\2025年",
    "01_顧客管理\顧客画像\2026年",
    "01_顧客管理\住所録データ",
    "02_注文・発送\2025年",
    "02_注文・発送\2026年",
    "03_請求・経理\2025年",
    "03_請求・経理\2026年",
    "04_チラシ・販促",
    "05_写真",
    "06_道具・スクリプト",
    "07_書類（あとで仕分け）",
    "99_過去の資料\ダウンロードした物",
    "99_過去の資料\その他"
)
foreach ($f in $folders) {
    New-Item -ItemType Directory -Force -Path (Join-Path $base $f) | Out-Null
}
Write-Host "フォルダ一式を用意しました → $base"
Write-Host ""

# --- 2. ファイルの行き先を決めるルール ---
function Get-Dest($file) {
    $ext  = $file.Extension.ToLower()
    $year = $file.LastWriteTime.Year

    if ($ext -in ".jpg",".jpeg",".png",".gif",".bmp",".heic",".tif",".tiff",".webp",".mp4",".mov",".avi") {
        return (Join-Path $base "05_写真\${year}年")
    }
    if ($ext -in ".pdf",".doc",".docx",".xls",".xlsx",".ppt",".pptx",".csv",".txt") {
        return (Join-Path $base "07_書類（あとで仕分け）\${year}年")
    }
    if ($ext -in ".py",".ps1",".bat") {
        return (Join-Path $base "06_道具・スクリプト")
    }
    if ($ext -in ".exe",".msi",".zip",".7z",".rar") {
        return (Join-Path $base "99_過去の資料\ダウンロードした物")
    }
    return (Join-Path $base "99_過去の資料\その他")
}

# --- 3. デスクトップとダウンロードを仕分ける ---
$targets = @(
    [Environment]::GetFolderPath('Desktop'),
    (Join-Path $env:USERPROFILE "Downloads"),
    (Join-Path $env:OneDrive "Downloads")
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

$moved   = @()
$skipped = 0

foreach ($dir in $targets) {
    Write-Host "仕分け中: $dir"
    $files = Get-ChildItem -LiteralPath $dir -File |
        Where-Object { $_.Extension -ne ".lnk" -and $_.Name -ne "desktop.ini" }

    foreach ($file in $files) {
        $dest = Get-Dest $file
        New-Item -ItemType Directory -Force -Path $dest | Out-Null

        $newPath = Join-Path $dest $file.Name
        $i = 2
        while (Test-Path -LiteralPath $newPath) {
            $newPath = Join-Path $dest ("{0} ({1}){2}" -f $file.BaseName, $i, $file.Extension)
            $i++
        }

        try {
            Move-Item -LiteralPath $file.FullName -Destination $newPath
            $shortDest = $dest.Replace("$base\", "")
            Write-Host ("  移動: {0} → {1}" -f $file.Name, $shortDest)
            $moved += [pscustomobject]@{
                日時     = (Get-Date -Format "yyyy-MM-dd HH:mm")
                ファイル = $file.Name
                元の場所 = $file.FullName
                移動先   = $newPath
            }
        }
        catch {
            Write-Host ("  スキップ（使用中の可能性）: {0}" -f $file.Name)
            $skipped++
        }
    }
}

# --- 4. 記録を残して結果を表示 ---
if ($moved.Count -gt 0) {
    $moved | Export-Csv -LiteralPath $log -Append -NoTypeInformation -Encoding UTF8
}

Write-Host ""
Write-Host "============================================"
Write-Host ("完了！ {0} 個のファイルを仕分けました。" -f $moved.Count)
if ($skipped -gt 0) {
    Write-Host ("※ {0} 個は使用中のためスキップしました（開いているソフトを閉じてもう一度実行すればOK）" -f $skipped)
}
Write-Host ("仕分け先: {0}" -f $base)
Write-Host ("移動の記録: {0}" -f $log)
Write-Host "============================================"
