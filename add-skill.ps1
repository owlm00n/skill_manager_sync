<#
.SYNOPSIS
    Skills Sync Manager - Add a new skill
.DESCRIPTION
    Creates a new skill directory in the central repo with a SKILL.md template.
.PARAMETER Name
    Skill directory name (required)
.PARAMETER Description
    Skill description for frontmatter
.PARAMETER FromPath
    Copy an existing skill directory into the central repo
.EXAMPLE
    .\add-skill.ps1 -Name "my-skill"
    .\add-skill.ps1 -Name "my-skill" -Description "Does something useful"
    .\add-skill.ps1 -FromPath "C:\path\to\existing-skill"
#>

param(
    [string]$Name,
    [string]$Description,
    [string]$FromPath
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsDir = Join-Path $ScriptDir "skills"

if ($FromPath) {
    # Import an existing skill directory
    if (-not (Test-Path $FromPath)) {
        Write-Host "ERROR: Path not found: $FromPath" -ForegroundColor Red
        exit 1
    }

    $skillName = Split-Path $FromPath -Leaf
    $targetDir = Join-Path $SkillsDir $skillName

    if (Test-Path $targetDir) {
        Write-Host "WARNING: Skill '$skillName' already exists in central repo." -ForegroundColor Yellow
        Write-Host "  Overwrite? [y/N] " -NoNewline
        $confirm = Read-Host
        if ($confirm -ne 'y') { exit 0 }
        Remove-Item $targetDir -Recurse -Force
    }

    Copy-Item -Path $FromPath -Destination $targetDir -Recurse -Force
    Write-Host "  Imported skill: $skillName" -ForegroundColor Green
    Write-Host "  Run '.\sync.ps1' to deploy to agents." -ForegroundColor DarkGray
    exit 0
}

if (-not $Name) {
    Write-Host "ERROR: -Name required (or use -FromPath to import)" -ForegroundColor Red
    exit 1
}

$targetDir = Join-Path $SkillsDir $Name

if (Test-Path $targetDir) {
    Write-Host "ERROR: Skill '$Name' already exists at $targetDir" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

$desc = if ($Description) { $Description } else { "TODO: Add description" }

$skillMd = @"
---
name: $Name
description: $desc
---

# $Name

TODO: Add skill instructions here.

## Usage

``````
# Add usage instructions
``````
"@

$skillMd | Set-Content (Join-Path $targetDir "SKILL.md") -Encoding UTF8

Write-Host ""
Write-Host "  Created skill: $Name" -ForegroundColor Green
Write-Host "  Path: $targetDir" -ForegroundColor DarkGray
Write-Host "  Edit: $targetDir\SKILL.md" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "    1. Edit the SKILL.md file" -ForegroundColor DarkGray
Write-Host "    2. Run '.\sync.ps1' to deploy to agents" -ForegroundColor DarkGray
Write-Host ""
