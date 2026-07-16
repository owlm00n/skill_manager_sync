<#
.SYNOPSIS
    Skills Sync Manager - Core sync script
.DESCRIPTION
    Syncs skills from central repo to configured agent directories.
    Supports symlink and copy modes.
.PARAMETER Mode
    Sync mode: symlink | copy. Overrides config.yaml default_mode.
.PARAMETER Agent
    Sync only to a specific agent (by name in config.yaml).
.PARAMETER Skill
    Sync only a specific skill (by directory name).
.PARAMETER DryRun
    Preview what would be synced without making changes.
.EXAMPLE
    .\sync.ps1
    .\sync.ps1 -Mode copy
    .\sync.ps1 -Agent claude_code_global -DryRun
    .\sync.ps1 -Skill bug-core
#>

param(
    [ValidateSet("symlink", "copy")]
    [string]$Mode,
    [string]$Agent,
    [string]$Skill,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $ScriptDir "config.yaml"
$SkillsDir = Join-Path $ScriptDir "skills"

# ── YAML Parser (lightweight, for our config format) ─────────────

function Parse-SimpleYaml {
    param([string]$Path)
    $content = Get-Content $Path -Raw -Encoding UTF8
    $result = @{}
    $currentSection = $null
    $currentSubSection = $null
    $currentSubSubSection = $null
    $currentKey = $null

    foreach ($line in (Get-Content $Path -Encoding UTF8)) {
        # Skip comments and empty lines
        if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }

        $indent = ($line -replace '^(\s*).*', '$1').Length

        # Top-level key (no indent)
        if ($indent -eq 0 -and $line -match '^(\w[\w_-]*)\s*:\s*(.*)$') {
            $key = $Matches[1]
            $val = $Matches[2].Trim()
            if ($val -eq '') {
                $currentSection = $key
                if (-not $result.ContainsKey($key)) { $result[$key] = @{} }
                $currentSubSection = $null
                $currentSubSubSection = $null
            } else {
                $result[$key] = Convert-YamlValue $val
                $currentSection = $null
            }
            continue
        }

        # Second level (2-space indent)
        if ($indent -eq 2 -and $currentSection -and $line -match '^\s{2}(\w[\w_-]*)\s*:\s*(.*)$') {
            $key = $Matches[1]
            $val = $Matches[2].Trim()
            if ($val -eq '') {
                $currentSubSection = $key
                if (-not $result[$currentSection].ContainsKey($key)) {
                    $result[$currentSection][$key] = @{}
                }
                $currentSubSubSection = $null
            } else {
                $result[$currentSection][$key] = Convert-YamlValue $val
                $currentSubSection = $null
            }
            continue
        }

        # Third level (4-space indent)
        if ($indent -eq 4 -and $currentSubSection -and $line -match '^\s{4}(\w[\w_-]*)\s*:\s*(.*)$') {
            $key = $Matches[1]
            $val = $Matches[2].Trim()
            if ($val -eq '') {
                $currentSubSubSection = $key
                $result[$currentSection][$currentSubSection][$key] = @{}
            } else {
                $result[$currentSection][$currentSubSection][$key] = Convert-YamlValue $val
                $currentSubSubSection = $null
            }
            continue
        }
    }
    return $result
}

function Convert-YamlValue {
    param([string]$val)
    # Remove quotes
    $val = $val.Trim()
    if ($val -match '^"(.*)"$' -or $val -match "^'(.*)'$") { $val = $Matches[1] }
    # Array: ["a", "b", "c"]
    if ($val -match '^\[(.+)\]$') {
        $items = $Matches[1] -split ',' | ForEach-Object {
            $_.Trim().Trim('"').Trim("'")
        }
        return @($items)
    }
    # Boolean
    if ($val -eq 'true') { return $true }
    if ($val -eq 'false') { return $false }
    return $val
}

# ── Main Logic ───────────────────────────────────────────────────

if (-not (Test-Path $ConfigPath)) {
    Write-Host "ERROR: config.yaml not found at $ConfigPath" -ForegroundColor Red
    exit 1
}

$config = Parse-SimpleYaml $ConfigPath

# Determine sync mode
if (-not $Mode) {
    $Mode = $config['default_mode']
    if (-not $Mode) { $Mode = "symlink" }
}

# Get all available skills
$allSkills = Get-ChildItem -Path $SkillsDir -Directory | Where-Object {
    Test-Path (Join-Path $_.FullName "SKILL.md")
} | Select-Object -ExpandProperty Name

if ($allSkills.Count -eq 0) {
    Write-Host "WARNING: No skills found in $SkillsDir" -ForegroundColor Yellow
}

# Get agents config
$agentsConfig = $config['agents']
if (-not $agentsConfig) {
    Write-Host "ERROR: No agents configured in config.yaml" -ForegroundColor Red
    exit 1
}

# Filter agents if -Agent specified
$agentNames = @($agentsConfig.Keys)
if ($Agent) {
    if ($agentNames -notcontains $Agent) {
        Write-Host "ERROR: Agent '$Agent' not found in config.yaml. Available: $($agentNames -join ', ')" -ForegroundColor Red
        exit 1
    }
    $agentNames = @($Agent)
}

# Resolve which skills to sync for an agent
function Resolve-SkillsForAgent {
    param($agentConf, [string[]]$allAvailable)

    $skillList = $agentConf['skills']
    if (-not $skillList) { $skillList = @("*") }

    # If specific skill filter from CLI
    if ($Skill) {
        if ($allAvailable -contains $Skill) {
            return @($Skill)
        } else {
            Write-Host "WARNING: Skill '$Skill' not found in central repo" -ForegroundColor Yellow
            return @()
        }
    }

    if ($skillList -contains "*") {
        return $allAvailable
    }
    return @($skillList)
}

# Sync a single skill to a target directory
function Sync-SkillToTarget {
    param(
        [string]$SkillName,
        [string]$TargetDir,
        [string]$SyncMode
    )

    $sourceDir = Join-Path $SkillsDir $SkillName
    $destDir = Join-Path $TargetDir $SkillName

    if (-not (Test-Path $sourceDir)) {
        return @{ Status = "MISSING_SOURCE"; Skill = $SkillName }
    }

    if ($SyncMode -eq "symlink") {
        # Check if already a correct symlink
        if (Test-Path $destDir) {
            $item = Get-Item $destDir -Force
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                $target = (Get-Item $destDir).Target
                if ($target -and (Resolve-Path $target -ErrorAction SilentlyContinue) -eq (Resolve-Path $sourceDir)) {
                    return @{ Status = "OK"; Skill = $SkillName }
                }
                # Wrong symlink target - remove and recreate
                if (-not $DryRun) { Remove-Item $destDir -Force }
            } else {
                # It's a real directory (from copy mode) - remove and create symlink
                if (-not $DryRun) { Remove-Item $destDir -Recurse -Force }
            }
        }

        # Ensure parent directory exists
        $parentDir = Split-Path $destDir -Parent
        if (-not (Test-Path $parentDir)) {
            if (-not $DryRun) { New-Item -ItemType Directory -Path $parentDir -Force | Out-Null }
        }

        if (-not $DryRun) {
            try {
                New-Item -ItemType SymbolicLink -Path $destDir -Target $sourceDir | Out-Null
                return @{ Status = "LINKED"; Skill = $SkillName }
            } catch {
                return @{ Status = "ERROR"; Skill = $SkillName; Error = $_.Exception.Message }
            }
        } else {
            return @{ Status = "WOULD_LINK"; Skill = $SkillName }
        }
    } else {
        # Copy mode
        if (Test-Path $destDir) {
            $item = Get-Item $destDir -Force
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                # It's a symlink - remove and copy
                if (-not $DryRun) { Remove-Item $destDir -Force }
            } else {
                # Already a real directory - check if content differs
                # For simplicity, always overwrite
                if (-not $DryRun) { Remove-Item $destDir -Recurse -Force }
            }
        }

        $parentDir = Split-Path $destDir -Parent
        if (-not (Test-Path $parentDir)) {
            if (-not $DryRun) { New-Item -ItemType Directory -Path $parentDir -Force | Out-Null }
        }

        if (-not $DryRun) {
            Copy-Item -Path $sourceDir -Destination $destDir -Recurse -Force
            return @{ Status = "COPIED"; Skill = $SkillName }
        } else {
            return @{ Status = "WOULD_COPY"; Skill = $SkillName }
        }
    }
}

# Clean up stale skills in target directory
function Clean-StaleSkills {
    param(
        [string]$TargetDir,
        [string[]]$ExpectedSkills,
        [string]$SyncMode
    )

    if (-not (Test-Path $TargetDir)) { return @() }
    $cleaned = @()

    Get-ChildItem -Path $TargetDir -Directory | ForEach-Object {
        $dirName = $_.Name
        if ($ExpectedSkills -notcontains $dirName) {
            # Check if it's our managed skill (symlink to our repo or contains SKILL.md)
            $isManaged = $false
            if ($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                $target = $_.Target
                if ($target -and $target.StartsWith($SkillsDir)) {
                    $isManaged = $true
                }
            } elseif (Test-Path (Join-Path $_.FullName "SKILL.md")) {
                # Check if content matches a skill we manage
                $isManaged = $true
            }

            if ($isManaged) {
                if (-not $DryRun) {
                    Remove-Item $_.FullName -Recurse -Force
                }
                $cleaned += $dirName
            }
        }
    }
    return $cleaned
}

# ── Execute Sync ─────────────────────────────────────────────────

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "  Skills Sync Manager [DRY RUN]" -ForegroundColor Cyan
} else {
    Write-Host "  Skills Sync Manager" -ForegroundColor Cyan
}
Write-Host "  Mode: $Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$totalLinked = 0
$totalCopied = 0
$totalErrors = 0
$totalStale = 0

foreach ($agentName in $agentNames) {
    $agentConf = $agentsConfig[$agentName]
    $targetPath = $agentConf['path']

    if (-not $targetPath) {
        Write-Host "  WARNING: No path for agent '$agentName', skipping" -ForegroundColor Yellow
        continue
    }

    # Expand ~ to home directory
    $targetPath = $targetPath -replace '^~', $env:USERPROFILE
    $targetPath = $targetPath -replace '/', '\'

    $skillsToSync = Resolve-SkillsForAgent $agentConf $allSkills

    Write-Host "  Agent: $agentName ($($agentConf['tool']))" -ForegroundColor Green
    Write-Host "  Target: $targetPath" -ForegroundColor DarkGray
    Write-Host "  Skills: $($skillsToSync.Count) to sync" -ForegroundColor DarkGray

    # Ensure target directory exists
    if (-not (Test-Path $targetPath) -and -not $DryRun) {
        New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
    }

    # Sync each skill
    foreach ($skillName in $skillsToSync) {
        $result = Sync-SkillToTarget $skillName $targetPath $Mode
        switch ($result.Status) {
            "LINKED" {
                Write-Host "    + $skillName -> symlinked" -ForegroundColor DarkGreen
                $totalLinked++
            }
            "COPIED" {
                Write-Host "    + $skillName -> copied" -ForegroundColor DarkGreen
                $totalCopied++
            }
            "OK" {
                Write-Host "    = $skillName (already synced)" -ForegroundColor DarkGray
            }
            "WOULD_LINK" {
                Write-Host "    ~ $skillName -> would symlink" -ForegroundColor Yellow
            }
            "WOULD_COPY" {
                Write-Host "    ~ $skillName -> would copy" -ForegroundColor Yellow
            }
            "MISSING_SOURCE" {
                Write-Host "    ! $skillName (source missing)" -ForegroundColor Red
                $totalErrors++
            }
            "ERROR" {
                Write-Host "    ! $skillName ERROR: $($result.Error)" -ForegroundColor Red
                $totalErrors++
            }
        }
    }

    # Clean stale skills
    $cleaned = Clean-StaleSkills $targetPath $skillsToSync $Mode
    foreach ($c in $cleaned) {
        Write-Host "    - $c (removed stale)" -ForegroundColor DarkYellow
        $totalStale++
    }

    Write-Host ""
}

# Summary
Write-Host "----------------------------------------" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "  [DRY RUN] No changes made." -ForegroundColor Yellow
}
Write-Host "  Linked: $totalLinked | Copied: $totalCopied | Stale removed: $totalStale | Errors: $totalErrors" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""
