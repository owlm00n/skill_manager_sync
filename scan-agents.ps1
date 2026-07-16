<#
.SYNOPSIS
    Skills Sync Manager - Agent scanner & importer
.DESCRIPTION
    Scans for installed agents (global level) and project-level skill instances.
    Can import discovered skills into the central repository.
.PARAMETER ScanPath
    Root directory to scan for project-level skill instances.
.PARAMETER MaxDepth
    Maximum directory depth for project scanning. Default: 3
.PARAMETER GlobalOnly
    Only scan for globally installed agents, skip project scanning.
.PARAMETER Import
    Automatically import discovered skills into the central repository.
.PARAMETER Json
    Output results as JSON for machine consumption.
.EXAMPLE
    .\scan-agents.ps1
    .\scan-agents.ps1 -ScanPath "D:\06_Project" -MaxDepth 3
    .\scan-agents.ps1 -ScanPath "D:\06_Project" -Import
    .\scan-agents.ps1 -GlobalOnly
#>

param(
    [string]$ScanPath,
    [int]$MaxDepth = 3,
    [switch]$GlobalOnly,
    [switch]$Import,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsDir = Join-Path $ScriptDir "skills"
$ConfigPath = Join-Path $ScriptDir "config.yaml"

# ── Agent Registry ───────────────────────────────────────────────

$AGENT_REGISTRY = @(
    @{ key="claude_code";  display="Claude Code";     detect=".claude";              skills=".claude/skills" },
    @{ key="cursor";       display="Cursor";          detect=".cursor";              skills=".cursor/skills" },
    @{ key="codex";        display="Codex";           detect=".codex";               skills=".codex/skills" },
    @{ key="copilot";      display="GitHub Copilot";  detect=".copilot";             skills=".copilot/skills" },
    @{ key="gemini_cli";   display="Gemini CLI";      detect=".gemini";              skills=".gemini/skills" },
    @{ key="windsurf";     display="Windsurf";        detect=".codeium\windsurf";    skills=".codeium\windsurf\skills" },
    @{ key="trae";         display="TRAE IDE";        detect=".trae";                skills=".trae/skills" },
    @{ key="grok";         display="Grok";            detect=".grok";                skills=".grok/skills" },
    @{ key="opencode";     display="OpenCode";        detect=".config\opencode";     skills=".config\opencode\skills" },
    @{ key="amp";          display="Amp";             detect=".config\agents";       skills=".config\agents\skills" },
    @{ key="kilo_code";    display="Kilo Code";       detect=".kilocode";            skills=".kilocode/skills" },
    @{ key="roo_code";     display="Roo Code";        detect=".roo";                 skills=".roo/skills" },
    @{ key="goose";        display="Goose";           detect=".config\goose";        skills=".config\goose\skills" },
    @{ key="cline";        display="Cline";           detect=".cline";               skills=".agents/skills" },
    @{ key="droid";        display="Droid";           detect=".factory";             skills=".factory/skills" }
)

# ── Global Agent Detection ───────────────────────────────────────

function Scan-GlobalAgents {
    $homeDir = $env:USERPROFILE
    $results = @()

    foreach ($agent in $AGENT_REGISTRY) {
        $detectPath = Join-Path $homeDir $agent.detect
        $skillsPath = Join-Path $homeDir $agent.skills
        $installed = Test-Path $detectPath

        $skillCount = 0
        $skillNames = @()
        if ($installed -and (Test-Path $skillsPath)) {
            $skillDirs = Get-ChildItem -Path $skillsPath -Directory -ErrorAction SilentlyContinue |
                Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") }
            $skillCount = $skillDirs.Count
            $skillNames = @($skillDirs | Select-Object -ExpandProperty Name)
        }

        $results += @{
            key = $agent.key
            display = $agent.display
            installed = $installed
            skills_dir = $skillsPath
            skill_count = $skillCount
            skills = $skillNames
        }
    }

    return $results
}

# ── Project-Level Scanning ───────────────────────────────────────

function Scan-ProjectSkills {
    param([string]$RootPath, [int]$Depth)

    $results = @()
    Scan-ProjectRecursive $RootPath 0 $Depth $results
    return $results
}

function Scan-ProjectRecursive {
    param([string]$Dir, [int]$CurrentDepth, [int]$MaxDepth, [ref]$Results)

    if ($CurrentDepth -gt $MaxDepth) { return }

    # Check if this directory has any agent skills
    $found = $false
    foreach ($agent in $AGENT_REGISTRY) {
        $projSkillsDir = Join-Path $Dir $agent.skills
        if (Test-Path $projSkillsDir) {
            $skillDirs = Get-ChildItem -Path $projSkillsDir -Directory -ErrorAction SilentlyContinue |
                Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") }

            foreach ($sd in $skillDirs) {
                $Results.Value += @{
                    project = $Dir
                    agent = $agent.key
                    agent_display = $agent.display
                    skill = $sd.Name
                    path = $sd.FullName
                }
            }
            $found = $true
        }
    }

    # If found agent skills here, don't recurse deeper
    if ($found) { return }

    # Recurse into subdirectories
    if ($CurrentDepth -lt $MaxDepth) {
        Get-ChildItem -Path $Dir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            $name = $_.Name
            # Skip hidden dirs, node_modules, etc.
            if ($name.StartsWith('.') -or $name -eq 'node_modules' -or $name -eq 'target' -or $name -eq '__pycache__') {
                return
            }
            Scan-ProjectRecursive $_.FullName ($CurrentDepth + 1) $MaxDepth $Results
        }
    }
}

# ── Import Skills ────────────────────────────────────────────────

function Import-SkillsToCentral {
    param([hashtable[]]$DiscoveredSkills)

    $imported = @()
    $skipped = @()

    # Group by skill name for dedup
    $grouped = @{}
    foreach ($s in $DiscoveredSkills) {
        $name = $s.skill
        if (-not $grouped.ContainsKey($name)) {
            $grouped[$name] = @()
        }
        $grouped[$name] += $s
    }

    foreach ($name in $grouped.Keys) {
        $targetDir = Join-Path $SkillsDir $name

        if (Test-Path $targetDir) {
            # Already exists in central repo
            $skipped += $name
            continue
        }

        # Copy the first found instance
        $source = $grouped[$name][0].path
        Copy-Item -Path $source -Destination $targetDir -Recurse -Force
        $imported += $name
        Write-Host "    + Imported: $name (from $($grouped[$name][0].project))" -ForegroundColor Green
    }

    return @{ imported = $imported; skipped = $skipped }
}

# ── Main ─────────────────────────────────────────────────────────

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Skills Sync - Agent Scanner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Global scan
Write-Host "  [Global Agents]" -ForegroundColor Green
$globalAgents = Scan-GlobalAgents
$installedAgents = @($globalAgents | Where-Object { $_.installed })

if ($Json) {
    # JSON mode - collect all data then output
    $jsonResult = @{
        global_agents = $globalAgents
        project_skills = @()
        import_result = $null
    }

    if (-not $GlobalOnly -and $ScanPath) {
        $projectResults = Scan-ProjectSkills $ScanPath $MaxDepth
        $jsonResult.project_skills = $projectResults

        if ($Import -and $projectResults.Count -gt 0) {
            $importResult = Import-SkillsToCentral $projectResults
            $jsonResult.import_result = $importResult
        }
    }

    Write-Host ($jsonResult | ConvertTo-Json -Depth 5)
    exit 0
}

foreach ($ag in $globalAgents) {
    if ($ag.installed) {
        $status = "INSTALLED"
        $color = "Green"
        $skillInfo = "$($ag.skill_count) skills"
    } else {
        $status = "not found"
        $color = "DarkGray"
        $skillInfo = ""
    }
    Write-Host "    $($ag.display.PadRight(18)) [$status]" -ForegroundColor $color -NoNewline
    if ($ag.installed) {
        Write-Host "  $skillInfo" -ForegroundColor DarkGray
    } else {
        Write-Host ""
    }
}

Write-Host ""
Write-Host "  Found $($installedAgents.Count) installed agent(s)" -ForegroundColor Cyan

# Project scan
if (-not $GlobalOnly) {
    if ($ScanPath) {
        if (-not (Test-Path $ScanPath)) {
            Write-Host "  ERROR: Scan path not found: $ScanPath" -ForegroundColor Red
            exit 1
        }

        Write-Host ""
        Write-Host "  [Project Skills in $ScanPath]" -ForegroundColor Green

        $projectResults = Scan-ProjectSkills $ScanPath $MaxDepth

        if ($projectResults.Count -eq 0) {
            Write-Host "    No project-level skills found (depth: $MaxDepth)" -ForegroundColor DarkGray
        } else {
            # Group by project
            $byProject = @{}
            foreach ($pr in $projectResults) {
                if (-not $byProject.ContainsKey($pr.project)) {
                    $byProject[$pr.project] = @()
                }
                $byProject[$pr.project] += $pr
            }

            foreach ($proj in $byProject.Keys) {
                Write-Host "    Project: $proj" -ForegroundColor Yellow
                foreach ($s in $byProject[$proj]) {
                    Write-Host "      $($s.agent_display): $($s.skill)" -ForegroundColor DarkGray
                }
            }

            Write-Host ""
            Write-Host "  Found $($projectResults.Count) project-level skill(s) in $($byProject.Count) project(s)" -ForegroundColor Cyan

            # Import
            if ($Import) {
                Write-Host ""
                Write-Host "  [Importing to Central Repo]" -ForegroundColor Green
                $importResult = Import-SkillsToCentral $projectResults
                Write-Host "  Imported: $($importResult.imported.Count) | Skipped (existing): $($importResult.skipped.Count)" -ForegroundColor Cyan
            }
        }
    } else {
        Write-Host ""
        Write-Host "  Tip: Use -ScanPath to scan for project-level skills" -ForegroundColor DarkGray
        Write-Host "  Example: .\scan-agents.ps1 -ScanPath `"D:\06_Project`" -MaxDepth 3" -ForegroundColor DarkGray
    }
}

Write-Host ""
