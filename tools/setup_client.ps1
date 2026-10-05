<#
.SYNOPSIS
    Fetch portable Godot for the desktop client and create the "Manager" desktop shortcut
    (spec 007, research R5).

.DESCRIPTION
    Downloads the official Godot release into tools\godot\ (gitignored; no system install, no
    admin rights), checks it against the release's published SHA-512 sum, and creates a desktop
    shortcut that opens the game window. Running it again is safe: an existing, verified copy
    is kept.

.PARAMETER NoShortcut
    Skip the desktop shortcut (CI).
#>
param(
    [switch]$NoShortcut
)

$ErrorActionPreference = 'Stop'
$Version = '4.7.2-stable'
$Zip = "Godot_v${Version}_win64.exe.zip"
# Pinned: a tampered release would also publish matching sums, so the expected hash lives here.
# The release's SHA512-SUMS.txt is only a cross-check (both must agree). Trust on first
# download: pinned on 2026-10-04 from the official 4.7.2-stable release (its SHA512-SUMS.txt
# and the zip downloaded here and on a GitHub runner all agreed). Re-verify when changing $Version.
$PinnedSha512 = '83decd58fdf67b9d657958a1ae6bf1929c20785315a81effe245874cdc57acb709bf868e00778a96984338c1b29dafdb453c6847747694621c6ecf5da2259993'
$Base = "https://github.com/godotengine/godot/releases/download/$Version"

$Repo = Split-Path -Parent $PSScriptRoot
$GodotDir = Join-Path $PSScriptRoot 'godot'
$Exe = Join-Path $GodotDir 'godot.exe'
$ConsoleExe = Join-Path $GodotDir 'godot_console.exe'
$Stamp = Join-Path $GodotDir 'VERSION'

New-Item -ItemType Directory -Force -Path $GodotDir | Out-Null

$current = if (Test-Path $Stamp) { (Get-Content $Stamp -Raw).Trim() } else { '' }
if ((Test-Path $Exe) -and ($current -eq $Version)) {
    Write-Host "Godot $Version already in $GodotDir"
} else {
    $zipPath = Join-Path $GodotDir $Zip
    Write-Host "Downloading Godot $Version ..."
    Invoke-WebRequest -Uri "$Base/$Zip" -OutFile $zipPath -UseBasicParsing
    # GitHub serves the sums as binary: save the file and read it as text
    $sumsPath = Join-Path $GodotDir 'SHA512-SUMS.txt'
    Invoke-WebRequest -Uri "$Base/SHA512-SUMS.txt" -OutFile $sumsPath -UseBasicParsing
    $line = Get-Content $sumsPath | Where-Object { $_ -match [regex]::Escape($Zip) } | Select-Object -First 1
    Remove-Item $sumsPath -Force
    if (-not $line) { throw "No SHA-512 sum published for $Zip" }
    $published = ($line -split '\s+')[0].ToLowerInvariant()
    if ($published -ne $PinnedSha512) {
        Remove-Item $zipPath -Force
        throw "The release's published SHA-512 for $Zip differs from the pinned one: refusing it"
    }
    $actual = (Get-FileHash -Algorithm SHA512 -Path $zipPath).Hash.ToLowerInvariant()
    if ($actual -ne $PinnedSha512) {
        Remove-Item $zipPath -Force
        throw "SHA-512 mismatch for $Zip (expected $PinnedSha512, got $actual)"
    }
    $unpack = Join-Path $GodotDir 'unpack'
    if (Test-Path $unpack) { Remove-Item $unpack -Recurse -Force }
    Expand-Archive -Path $zipPath -DestinationPath $unpack
    Copy-Item (Join-Path $unpack "Godot_v${Version}_win64.exe") $Exe -Force
    Copy-Item (Join-Path $unpack "Godot_v${Version}_win64_console.exe") $ConsoleExe -Force
    Remove-Item $unpack -Recurse -Force
    Remove-Item $zipPath -Force
    Set-Content -Path $Stamp -Value $Version -Encoding ascii
    Write-Host "Godot $Version installed in $GodotDir (SHA-512 matches the pinned hash)"
}

if (-not $NoShortcut) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $link = Join-Path $desktop 'Manager.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($link)
    $shortcut.TargetPath = $Exe
    $shortcut.Arguments = "--path `"$(Join-Path $Repo 'client')`""
    $shortcut.WorkingDirectory = $Repo
    $shortcut.Description = 'Manager - jogo de futebol'
    $shortcut.Save()
    Write-Host "Shortcut created: $link"
}
