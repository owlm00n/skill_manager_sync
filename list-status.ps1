<#
.SYNOPSIS
    Skills Sync Manager - List sync status
.DESCRIPTION
    Shows all skills in the central repo and their sync status across agents.
.EXAMPLE
    .\list-status.ps1
#>

param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $ScriptDir "config.yaml"
$SkillsDir = Join-Path $ScriptDir "skills"

# ── Parse config ─────────────────────────────────────────────────

function Parse-SimpleYaml {
    param([string]$Path)
    $result = @{}
    $currentSection = $null
    $currentSubSection = $null

    foreach ($line in (Get-Content $Path -Encoding UTF8)) {
        if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }
        $indent = ($line -replace '^(\s*).*', '$1').Length

        if ($indent -eq 0 -and $line -match '^(\w[\w_-]*)\s*:\s*(.*)$') {
            $key = $Matches[1]; $val = $Matches[2].Trim()
            if ($val -eq '') {
                $currentSection = $key
                if (-not $result.ContainsKey($key)) { $result[$key] = @{} }
                $currentSubSection = $null
            } else {
                $result[$key] = Convert-YamlValue $val
                $currentSection = $null
            }
            continue
        }
        if ($indent -eq 2 -and $currentSection -and $line -match '^\s{2}(\w[\w_-]*)\s*:\s*(.*)$') {
            $key = $Matches[1]; $val = $Matches[2].Trim()
            if ($val -eq '') {
                $currentSubSection = $key
                if (-not $result[$currentSection].ContainsKey($key)) { $result[$currentSection][$key] = @{} }
            } else {
                $result[$currentSection][$key] = Convert-YamlValue $val
                $currentSubSection = $null
            }
            continue
        }
        if ($indent -eq 4 -and $currentSubSection -and $line -match '^\s{4}(\w[\w_-]*)\s*:\s*(.*)$') {
            $key = $Matches[1]; $val = $Matches[2].Trim()
            $result[$currentSection][$currentSubSection][$key] = Convert-YamlValue $val
            continue
        }
    }
    return $result
}

function Convert-YamlValue {
    param([string]$val)
    $val = $val.Trim()
    if ($val -match '^"(.*)"$' -or $val -match "^'(.*)'$") { $val = $Matches[1] }
    if ($val -match '^\[(.+)\]$') {
        $items = $Matches[1] -split ',' | ForEach-Object { $_.Trim().Trim('"').Trim("'") }
        return @($items)
    }
    if ($val -eq 'true') { return $true }
    if ($val -eq 'false') { return $false }
    return $val
}

# ── Main ─────────────────────────────────────────────────────────

$config = Parse-SimpleYaml $ConfigPath
$agentsConfig = $config['agents']
$allSkills = Get-ChildItem -Path $SkillsDir -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
    Select-Object -ExpandProperty Name | Sort-Object

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Skills Sync Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Central repo skills
Write-Host "  Central Repo: $($allSkills.Count) skills" -ForegroundColor Green
Write-Host ""

# Build agent status table
$agentNames = @($agentsConfig.Keys)
if ($agentNames.Count -eq 0) {
    Write-Host "  No agents configured." -ForegroundColor Yellow
    exit 0
}

# Header
$header = "  Skill".PadRight(25)
foreach ($an in $agentNames) {
    $short = if ($an.Length -gt 12) { $an.Substring(0, 12) } else { $an }
    $header += $short.PadRight(14)
}
Write-Host $header -ForegroundColor Cyan
Write-Host ("  " + ("-" * (25 + $agentNames.Count * 14))) -ForegroundColor DarkGray

# Each skill
foreach ($skill in $allSkills) {
    $line = "  $skill".PadRight(25)

    foreach ($an in $agentNames) {
        $agentConf = $agentsConfig[$an]
        $targetPath = $agentConf['path'] -replace '^~', $env:USERPROFILE -replace '/', '\'
        $skillPath = Join-Path $targetPath $skill

        $status = "  -  "
        $color = "DarkGray"

        if (Test-Path $skillPath) {
            $item = Get-Item $skillPath -Force
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                $status = " link "
                $color = "Green"
            } else {
                $status = " copy "
                $color = "DarkGreen"
            }
        }

        $line += $status.PadRight(14)
    }

    Write-Host $line -ForegroundColor $color
}

Write-Host ""
Write-Host "  Legend: [link] = symlinked  [copy] = copied  [-] = not synced" -ForegroundColor DarkGray
Write-Host ""
