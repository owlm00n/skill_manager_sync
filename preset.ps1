<#
.SYNOPSIS
    Skills Sync Manager - Preset management
.DESCRIPTION
    Manage skill presets: create, activate, deactivate, view status.
    Presets group skills for one-click deployment to agents.
.PARAMETER Command
    Action to perform: list, show, activate, deactivate, status, create, add-skill, remove-skill
.PARAMETER Name
    Preset name (for show, activate, deactivate, create, add-skill, remove-skill)
.PARAMETER Agent
    Target agent name (for activate, deactivate, status)
.PARAMETER Skills
    Comma-separated skill names (for create)
.PARAMETER Description
    Preset description (for create)
.PARAMETER DryRun
    Preview without making changes
.EXAMPLE
    .\preset.ps1 list
    .\preset.ps1 show debug-toolkit
    .\preset.ps1 activate debug-toolkit -Agent claude_code_global
    .\preset.ps1 deactivate debug-toolkit -Agent claude_code_global
    .\preset.ps1 status -Agent claude_code_global
    .\preset.ps1 create my-preset -Skills "skill-a,skill-b" -Description "My preset"
    .\preset.ps1 add-skill debug-toolkit new-skill
    .\preset.ps1 remove-skill debug-toolkit old-skill
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("list", "show", "activate", "deactivate", "status", "create", "add-skill", "remove-skill")]
    [string]$Command = "list",

    [Parameter(Position=1)]
    [string]$Name,

    [string]$Agent,
    [string]$Skills,
    [string]$Description,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $ScriptDir "config.yaml"
$SkillsDir = Join-Path $ScriptDir "skills"
$SyncScript = Join-Path $ScriptDir "sync.ps1"

# ── YAML helpers ─────────────────────────────────────────────────

function Read-Config {
    $lines = Get-Content $ConfigPath -Encoding UTF8
    return $lines
}

function Write-Config {
    param([string[]]$Lines)
    $Lines | Set-Content $ConfigPath -Encoding UTF8
}

function Get-Presets {
    $lines = Read-Config
    $presets = @{}
    $inPresets = $false
    $currentPreset = $null
    $inSkills = $false

    foreach ($line in $lines) {
        if ($line -match '^presets:\s*$') { $inPresets = $true; continue }
        if ($inPresets -and $line -match '^\w' -and $line -notmatch '^\s') { $inPresets = $false; continue }

        if ($inPresets) {
            if ($line -match '^\s{2}([\w-]+):\s*$') {
                $currentPreset = $Matches[1]
                $presets[$currentPreset] = @{ description = ""; skills = @() }
                $inSkills = $false
                continue
            }
            if ($currentPreset -and $line -match '^\s{4}description:\s*"?(.+?)"?\s*$') {
                $presets[$currentPreset].description = $Matches[1]
                continue
            }
            if ($currentPreset -and $line -match '^\s{4}skills:\s*\[(.+)\]') {
                $items = $Matches[1] -split ',' | ForEach-Object { $_.Trim().Trim('"').Trim("'") }
                $presets[$currentPreset].skills = @($items)
                $inSkills = $true
                continue
            }
        }
    }
    return $presets
}

function Get-AgentActivePresets {
    param([string]$AgentName)
    $lines = Read-Config
    $inAgent = $false
    $activePresets = @()

    foreach ($line in $lines) {
        if ($line -match "^  ${AgentName}:\s*$") { $inAgent = $true; continue }
        if ($inAgent -and $line -match '^\w' -and $line -notmatch '^\s') { $inAgent = $false; continue }
        if ($inAgent -and $line -match '^\s{4}active_presets:\s*\[(.+)\]') {
            $items = $Matches[1] -split ',' | ForEach-Object { $_.Trim().Trim('"').Trim("'") }
            $activePresets = @($items)
        }
    }
    return $activePresets
}

function Set-AgentActivePresets {
    param([string]$AgentName, [string[]]$Presets)
    $lines = Read-Config
    $newLines = @()
    $inAgent = $false
    $replaced = $false

    $presetStr = ($Presets | ForEach-Object { "`"$_`"" }) -join ", "

    foreach ($line in $lines) {
        if ($line -match "^  ${AgentName}:\s*$") { $inAgent = $true; $newLines += $line; continue }
        if ($inAgent -and $line -match '^\w' -and $line -notmatch '^\s') { $inAgent = $false }
        if ($inAgent -and $line -match '^\s{4}active_presets:') {
            $newLines += "    active_presets: [$presetStr]"
            $replaced = $true
            continue
        }
        $newLines += $line
    }

    if (-not $replaced -and $Presets.Count -gt 0) {
        # Add active_presets to agent section
        $finalLines = @()
        $inAgent = $false
        $added = $false
        foreach ($line in $newLines) {
            $finalLines += $line
            if ($line -match "^  ${AgentName}:\s*$") { $inAgent = $true; continue }
            if ($inAgent -and -not $added -and ($line -match '^\s{4}path:' -or $line -match '^\s{4}tool:')) {
                $finalLines += "    active_presets: [$presetStr]"
                $added = $true
            }
            if ($inAgent -and $line -match '^\w' -and $line -notmatch '^\s') { $inAgent = $false }
        }
        $newLines = $finalLines
    }

    Write-Config $newLines
}

function Resolve-PresetSkills {
    param([string[]]$SkillList)
    $allSkills = Get-ChildItem -Path $SkillsDir -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
        Select-Object -ExpandProperty Name

    if ($SkillList -contains "*") {
        return $allSkills
    }
    return @($SkillList)
}

# ── Commands ─────────────────────────────────────────────────────

switch ($Command) {
    "list" {
        $presets = Get-Presets
        $allAvailable = Get-ChildItem -Path $SkillsDir -Directory |
            Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
            Select-Object -ExpandProperty Name

        Write-Host ""
        Write-Host "  Available Presets:" -ForegroundColor Cyan
        Write-Host "  ---------------------------------" -ForegroundColor DarkGray
        foreach ($name in ($presets.Keys | Sort-Object)) {
            $p = $presets[$name]
            if ($p.skills -contains "*") {
                $skillCount = $allAvailable.Count
            } else {
                $skillCount = $p.skills.Count
            }
            $desc = if ($p.description) { $p.description } else { "" }
            Write-Host "    $name" -ForegroundColor Green -NoNewline
            Write-Host (" " * [Math]::Max(1, 22 - $name.Length)) -NoNewline
            Write-Host "$skillCount skills" -ForegroundColor DarkGray -NoNewline
            if ($desc) { Write-Host "  $desc" -ForegroundColor DarkGray } else { Write-Host "" }
        }
        Write-Host ""
    }

    "show" {
        if (-not $Name) { Write-Host "ERROR: Preset name required" -ForegroundColor Red; exit 1 }
        $presets = Get-Presets
        if (-not $presets.ContainsKey($Name)) {
            Write-Host "ERROR: Preset '$Name' not found. Available: $($presets.Keys -join ', ')" -ForegroundColor Red
            exit 1
        }
        $p = $presets[$Name]
        $resolved = Resolve-PresetSkills $p.skills

        Write-Host ""
        Write-Host "  Preset: $Name" -ForegroundColor Cyan
        if ($p.description) { Write-Host "  Description: $($p.description)" -ForegroundColor DarkGray }
        Write-Host "  Skills ($($resolved.Count)):" -ForegroundColor Green
        foreach ($s in ($resolved | Sort-Object)) {
            $exists = Test-Path (Join-Path $SkillsDir "$s\SKILL.md")
            if ($exists) {
                Write-Host "    + $s" -ForegroundColor DarkGreen
            } else {
                Write-Host "    ! $s (not in central repo)" -ForegroundColor Yellow
            }
        }
        Write-Host ""
    }

    "activate" {
        if (-not $Name) { Write-Host "ERROR: Preset name(s) required" -ForegroundColor Red; exit 1 }
        if (-not $Agent) { Write-Host "ERROR: -Agent required" -ForegroundColor Red; exit 1 }

        $presets = Get-Presets
        $presetNames = $Name -split ',' | ForEach-Object { $_.Trim() }
        $currentActive = @(Get-AgentActivePresets $Agent)

        # Validate preset names
        foreach ($pn in $presetNames) {
            if (-not $presets.ContainsKey($pn)) {
                Write-Host "ERROR: Preset '$pn' not found" -ForegroundColor Red
                exit 1
            }
        }

        # Merge: add new presets to active list
        $newActive = @($currentActive)
        foreach ($pn in $presetNames) {
            if ($currentActive -notcontains $pn) {
                $newActive += $pn
            }
        }

        # Collect all skills from active presets
        $allPresetSkills = @()
        foreach ($pn in $newActive) {
            if ($presets.ContainsKey($pn)) {
                $allPresetSkills += @(Resolve-PresetSkills $presets[$pn].skills)
            }
        }
        $allPresetSkills = $allPresetSkills | Select-Object -Unique

        Write-Host ""
        Write-Host "  Activating preset(s): $($presetNames -join ', ')" -ForegroundColor Green
        Write-Host "  Agent: $Agent" -ForegroundColor Cyan
        Write-Host "  Active presets after: $($newActive -join ', ')" -ForegroundColor DarkGray
        Write-Host "  Total skills to sync: $($allPresetSkills.Count)" -ForegroundColor DarkGray

        if (-not $DryRun) {
            Set-AgentActivePresets $Agent $newActive
            # Trigger sync for this agent
            & $SyncScript -Agent $Agent
        } else {
            Write-Host "  [DRY RUN] No changes made." -ForegroundColor Yellow
        }
        Write-Host ""
    }

    "deactivate" {
        if (-not $Name) { Write-Host "ERROR: Preset name(s) required" -ForegroundColor Red; exit 1 }
        if (-not $Agent) { Write-Host "ERROR: -Agent required" -ForegroundColor Red; exit 1 }

        $presets = Get-Presets
        $presetNames = $Name -split ',' | ForEach-Object { $_.Trim() }
        $currentActive = @(Get-AgentActivePresets $Agent)

        # Remove from active list
        $newActive = @($currentActive | Where-Object { $presetNames -notcontains $_ })

        # Collect remaining skills
        $remainingSkills = @()
        foreach ($pn in $newActive) {
            if ($presets.ContainsKey($pn)) {
                $remainingSkills += @(Resolve-PresetSkills $presets[$pn].skills)
            }
        }
        $remainingSkills = $remainingSkills | Select-Object -Unique

        # Skills that were only in deactivated presets
        $deactivatedSkills = @()
        foreach ($pn in $presetNames) {
            if ($presets.ContainsKey($pn)) {
                $deactivatedSkills += @(Resolve-PresetSkills $presets[$pn].skills)
            }
        }
        $toRemove = @($deactivatedSkills | Where-Object { $remainingSkills -notcontains $_ })

        Write-Host ""
        Write-Host "  Deactivating preset(s): $($presetNames -join ', ')" -ForegroundColor Yellow
        Write-Host "  Agent: $Agent" -ForegroundColor Cyan
        Write-Host "  Active presets after: $(if ($newActive.Count) { $newActive -join ', ' } else { 'none' })" -ForegroundColor DarkGray
        if ($toRemove.Count -gt 0) {
            Write-Host "  Skills to remove: $($toRemove -join ', ')" -ForegroundColor DarkYellow
        }

        if (-not $DryRun) {
            Set-AgentActivePresets $Agent $newActive
            # Remove orphaned skills from target
            $config = Parse-SimpleYaml $ConfigPath
            $agentConf = $config['agents'][$Agent]
            if ($agentConf) {
                $targetPath = $agentConf['path'] -replace '^~', $env:USERPROFILE -replace '/', '\'
                foreach ($s in $toRemove) {
                    $skillPath = Join-Path $targetPath $s
                    if (Test-Path $skillPath) {
                        Remove-Item $skillPath -Recurse -Force
                        Write-Host "    - Removed: $s" -ForegroundColor DarkYellow
                    }
                }
            }
            # Re-sync remaining
            & $SyncScript -Agent $Agent
        } else {
            Write-Host "  [DRY RUN] No changes made." -ForegroundColor Yellow
        }
        Write-Host ""
    }

    "status" {
        if (-not $Agent) { Write-Host "ERROR: -Agent required" -ForegroundColor Red; exit 1 }

        $presets = Get-Presets
        $activePresets = @(Get-AgentActivePresets $Agent)

        # Get target path for checking synced skills
        $config = Parse-SimpleYaml $ConfigPath
        $agentConf = $config['agents'][$Agent]
        $targetPath = ""
        $syncedSkills = @()
        if ($agentConf) {
            $targetPath = $agentConf['path'] -replace '^~', $env:USERPROFILE -replace '/', '\'
            if (Test-Path $targetPath) {
                $syncedSkills = @(Get-ChildItem -Path $targetPath -Directory -ErrorAction SilentlyContinue |
                    Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
                    Select-Object -ExpandProperty Name)
            }
        }

        Write-Host ""
        Write-Host "  Preset Status for: $Agent" -ForegroundColor Cyan
        Write-Host "  ─────────────────────────────────" -ForegroundColor DarkGray

        foreach ($name in ($presets.Keys | Sort-Object)) {
            $p = $presets[$name]
            $resolved = Resolve-PresetSkills $p.skills
            $isActive = $activePresets -contains $name

            if ($isActive) {
                $syncedCount = @($resolved | Where-Object { $syncedSkills -contains $_ }).Count
                $total = $resolved.Count
                if ($syncedCount -eq $total) {
                    Write-Host "    $name".PadRight(22) -ForegroundColor Green -NoNewline
                    Write-Host " [OK] ($syncedCount/$total skills synced)" -ForegroundColor Green
                } else {
                    $missing = @($resolved | Where-Object { $syncedSkills -notcontains $_ })
                    Write-Host "    $name".PadRight(22) -ForegroundColor Yellow -NoNewline
                    Write-Host " [$syncedCount/$total] missing: $($missing -join ', ')" -ForegroundColor Yellow
                }
            } else {
                Write-Host "    $name".PadRight(22) -ForegroundColor DarkGray -NoNewline
                Write-Host " not activated" -ForegroundColor DarkGray
            }
        }
        Write-Host ""
    }

    "create" {
        if (-not $Name) { Write-Host "ERROR: Preset name required" -ForegroundColor Red; exit 1 }
        if (-not $Skills) { Write-Host "ERROR: -Skills required (comma-separated)" -ForegroundColor Red; exit 1 }

        $skillList = $Skills -split ',' | ForEach-Object { $_.Trim() }
        $desc = if ($Description) { $Description } else { $Name }

        # Check if preset already exists
        $presets = Get-Presets
        if ($presets.ContainsKey($Name)) {
            Write-Host "ERROR: Preset '$Name' already exists. Use add-skill/remove-skill to modify." -ForegroundColor Red
            exit 1
        }

        # Add to config.yaml
        $lines = Read-Config
        $newLines = @()
        $inserted = $false

        for ($i = 0; $i -lt $lines.Count; $i++) {
            $newLines += $lines[$i]
            # Insert before the agents section
            if (-not $inserted -and $lines[$i] -match '^# .*Agent' -and $i -gt 0) {
                $skillStr = ($skillList | ForEach-Object { "`"$_`"" }) -join ", "
                $newLines = $newLines[0..($newLines.Count-2)]
                $newLines += "  ${Name}:"
                $newLines += "    description: `"$desc`""
                $newLines += "    skills: [$skillStr]"
                $newLines += ""
                $newLines += $lines[$i]
                $inserted = $true
            }
        }

        if (-not $inserted) {
            # Append to presets section
            $skillStr = ($skillList | ForEach-Object { "`"$_`"" }) -join ", "
            # Find the end of presets section
            for ($i = $newLines.Count - 1; $i -ge 0; $i--) {
                if ($newLines[$i] -match '^agents:') {
                    $insertLines = @(
                        "  ${Name}:",
                        "    description: `"$desc`"",
                        "    skills: [$skillStr]",
                        ""
                    )
                    $before = $newLines[0..($i-1)]
                    $after = $newLines[$i..($newLines.Count-1)]
                    $newLines = @($before) + $insertLines + @($after)
                    $inserted = $true
                    break
                }
            }
        }

        if (-not $DryRun) {
            Write-Config $newLines
            Write-Host "  Created preset '$Name' with skills: $($skillList -join ', ')" -ForegroundColor Green
        } else {
            Write-Host "  [DRY RUN] Would create preset '$Name'" -ForegroundColor Yellow
        }
    }

    "add-skill" {
        if (-not $Name) { Write-Host "ERROR: Preset name required" -ForegroundColor Red; exit 1 }
        if (-not $Skills) {
            # Positional: second arg is the skill name
            if ($args.Count -gt 0) {
                $Skills = $args[0]
            } else {
                Write-Host "ERROR: Skill name required" -ForegroundColor Red; exit 1
            }
        }

        $presets = Get-Presets
        if (-not $presets.ContainsKey($Name)) {
            Write-Host "ERROR: Preset '$Name' not found" -ForegroundColor Red; exit 1
        }

        $currentSkills = @($presets[$Name].skills)
        $newSkills = $Skills -split ',' | ForEach-Object { $_.Trim() }
        $merged = @($currentSkills)
        foreach ($s in $newSkills) {
            if ($merged -notcontains $s) { $merged += $s }
        }

        # Update config
        $lines = Read-Config
        $skillStr = ($merged | ForEach-Object { "`"$_`"" }) -join ", "
        $newLines = $lines | ForEach-Object {
            if ($_ -match "^\s{4}skills:.*# preset:$Name") {
                "    skills: [$skillStr]"
            } elseif ($_ -match "^\s{4}skills:\s*\[" -and $script:inPreset) {
                "    skills: [$skillStr]"
            } else {
                $_
            }
        }

        # Simpler approach: find the preset's skills line and replace
        $inTargetPreset = $false
        $newLines = @()
        foreach ($line in (Read-Config)) {
            if ($line -match "^  ${Name}:\s*$") { $inTargetPreset = $true; $newLines += $line; continue }
            if ($inTargetPreset -and $line -match '^\s{2}[\w-]+:\s*$') { $inTargetPreset = $false }
            if ($inTargetPreset -and $line -match '^\s{4}skills:\s*\[') {
                $newLines += "    skills: [$skillStr]"
                continue
            }
            $newLines += $line
        }

        if (-not $DryRun) {
            Write-Config $newLines
            Write-Host "  Added to '$Name': $($newSkills -join ', ')" -ForegroundColor Green
            Write-Host "  Preset now has: $($merged -join ', ')" -ForegroundColor DarkGray
        } else {
            Write-Host "  [DRY RUN] Would add to '$Name': $($newSkills -join ', ')" -ForegroundColor Yellow
        }
    }

    "remove-skill" {
        if (-not $Name) { Write-Host "ERROR: Preset name required" -ForegroundColor Red; exit 1 }
        if (-not $Skills) {
            if ($args.Count -gt 0) { $Skills = $args[0] }
            else { Write-Host "ERROR: Skill name required" -ForegroundColor Red; exit 1 }
        }

        $presets = Get-Presets
        if (-not $presets.ContainsKey($Name)) {
            Write-Host "ERROR: Preset '$Name' not found" -ForegroundColor Red; exit 1
        }

        $currentSkills = @($presets[$Name].skills)
        $toRemove = $Skills -split ',' | ForEach-Object { $_.Trim() }
        $remaining = @($currentSkills | Where-Object { $toRemove -notcontains $_ })

        $inTargetPreset = $false
        $skillStr = ($remaining | ForEach-Object { "`"$_`"" }) -join ", "
        $newLines = @()
        foreach ($line in (Read-Config)) {
            if ($line -match "^  ${Name}:\s*$") { $inTargetPreset = $true; $newLines += $line; continue }
            if ($inTargetPreset -and $line -match '^\s{2}[\w-]+:\s*$') { $inTargetPreset = $false }
            if ($inTargetPreset -and $line -match '^\s{4}skills:\s*\[') {
                $newLines += "    skills: [$skillStr]"
                continue
            }
            $newLines += $line
        }

        if (-not $DryRun) {
            Write-Config $newLines
            Write-Host "  Removed from '$Name': $($toRemove -join ', ')" -ForegroundColor Yellow
            Write-Host "  Preset now has: $($remaining -join ', ')" -ForegroundColor DarkGray
        } else {
            Write-Host "  [DRY RUN] Would remove from '$Name': $($toRemove -join ', ')" -ForegroundColor Yellow
        }
    }
}

# ── Helper: Parse YAML (simplified, for status command) ──────────

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
