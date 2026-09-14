---
name: engd-code-review
description: Perform end-to-end code review for Unisoc internal Gerrit (gerrit.unisoc.com) topics or specific commits. Use whenever the user wants to review code changes from Unisoc Gerrit, cherry-pick commits across multiple Unisoc kernel/framework repos, and produce a professional HTML code review report. Also trigger for "review this topic", "code review these changes", "review the cherry-picks", "do a code review", "review branch X". This skill handles repo sync from Unisoc local mirrors, cherry-pick setup, deep code analysis with adversarial multi-model validation, HTML report generation, and suggested fix patches.
---

# ENGD Code Review Skill

Comprehensive code review on Gerrit changes with adversarial multi-model validation and HTML report.

## Quick Reference

```
1. resolved_cwd=$(python scripts/init_review.py "<input>")
2. python scripts/setup_review.py "<input>" "$resolved_cwd"   ← STOP entire pipeline if exit code ≠ 0
3. python scripts/prepare_review_dispatch.py <run_dir>  → dispatch ALL subagents IN PARALLEL (one batch)
4. If PROJECT_COUNT > 1: dispatch ONE cross-project review subagent (Step 3.1)
   python scripts/prepare_cross_project_dispatch.py <run_dir>
   python scripts/record_dispatch.py <run_dir> --type cross-review --action start
   python scripts/wait_for_dispatch.py <run_dir> --type cross-review
   python scripts/verify_dispatch.py <run_dir> --type cross-review
5. python scripts/validate_findings.py <run_dir> [--fix]
   python scripts/consolidate_findings.py <run_dir>   ← BLOCKS if Step 3.1 skipped on multi-project
6. python scripts/prepare_validation_dispatch.py <run_dir> → dispatch ALL subagents IN PARALLEL (one batch)
7. If CROSS_PROJECT_FINDINGS > 0: dispatch ONE cross-project validation subagent (Step 4.1)
8. python scripts/validate_verified.py <run_dir>
9. python scripts/merge_validation_results.py <run_dir>
   python scripts/build_issues.py <run_dir>
   python scripts/generate_html_report.py --workspace <ws> --branch <b> --issues <ij> --change-summary <csj>
```

All scripts are in `scripts/` relative to this skill's directory. Run `python scripts/<name>.py --help` for full options.

## Fatal Setup Errors — Abort Entire Pipeline

If Step 2 (`setup_review.py`) exits with code **1**, **stop immediately**. Do not run Steps 3–5, do not dispatch subagents, do not generate a report. Tell the user which change failed and why.

This applies to:
- Gerrit HTTPS access check failure (before clone/cherry-pick)
- **Any cherry-pick conflict** — fetch failure or merge conflict on any change

On cherry-pick conflict, setup runs `git cherry-pick --abort` on the failed repo, cancels in-flight parallel cherry-picks, and exits. No `change_summary.json`, no diffs, no partial review.

## Parallel Subagent Dispatch Protocol (Steps 3 and 4)

Review and validation use **subagents** — separate agent sessions spawned by the parent orchestrator. The parent runs Python scripts; subagents only execute their prompt and write output files. This protocol is **platform-agnostic** (Claude, Cursor, Codex, Gemini, Qoder, Trae, etc.) — adapt your platform's "spawn subagent / task / parallel agent" mechanism to these rules.

### Universal rules

1. **One subagent per unit of work**
   - Per-change review: one subagent per entry in `_review_manifest.json` `agents` array
   - Per-change validation: one subagent per group in `_validation_manifest.json`
   - Cross-project review (Step 3.1): **exactly one** subagent for **all** changes — never split by change groups
   - Cross-project validation (Step 4.1): one subagent

2. **Dispatch in parallel (one launch, one change each)**
   - **Parallel batch** = spawn all N subagents in one message before waiting for any result.
   - **NOT** “batch multiple changes into one subagent.” That breaks `verify_dispatch.py` and the HTML report.
   - Do not review change A, wait, then start change B sequentially.

3. **Subagent inputs**
   - Per-change review: pass each agent's `dispatch_prompt` from the manifest (short bootstrap). The subagent reads the full instructions from `prompt_file` — do not inline or summarize that file in the parent.
   - Per-change validation: pass each group's `dispatch_prompt` from the manifest. The subagent reads `prompt_file` and `findings_file` on disk — do not inline findings in the parent.
   - Cross-project review/validation: pass bootstrap pointing at `prompt_file`, or read `prompt_file` and pass full content if your platform requires it.
   - Subagents need read + write access to `<run_dir>` and `<workspace_dir>`.
   - **No worktree isolation** — see below.

### Worktree isolation (disabled)

This skill **must not** use git worktree isolation for any subagent.

- **Omit the `isolation` parameter** when spawning subagents. Do not pass `isolation: none` — many Agent APIs reject it (`expected "worktree"`). Omitting the parameter runs in the shared cwd (correct for this skill).
- **Never** pass `isolation: worktree`, `--worktree`, or `EnterWorktree`.
- Git repos already live under `<resolved_cwd>/workspace/`. Subagents read/write `<run_dir>/reviews/` and workspace paths directly.
- The skill directory itself is not a git repo — worktree spawn fails with `Cannot create agent worktree`.

Manifests set `worktree_isolation: false` and `spawn_options.omit_isolation: true`.

4. **Subagent outputs (required)**
   - Review: `output_path` / `findings_output` from manifest → `<run_dir>/reviews/...`
   - Cross-project review: `_cross_project_findings.json` (write `[]` if no issues)
   - Validation: `_verified_<CHANGE_ID>.json` or `_verified_cross_project.json`

5. **Verify only after the batch completes** — use the wait/redispatch protocol below. Missing output files during an in-flight batch is normal; it is **not** a signal to re-dispatch.

6. **On failure — re-dispatch, do not improvise**
   - Re-run only subagents whose output files are missing **after** `wait_for_dispatch.py` exits.
   - **Never re-dispatch a subagent while its previous run is still in progress** — duplicate agents race on the same output file and corrupt results.
   - If output is missing but the original subagent may still be running, **wait**; do not spawn a second copy.
   - **Never** use “Continue agent …” / resume on in-flight subagents — spawn a fresh redispatch only via `prepare_redispatch.py`.
   - **Never** treat Task polling errors (`No task found with ID`) as a failed dispatch — those mean **wait**, not re-dispatch.
   - The parent orchestrator must **NOT** read diffs and produce findings or verdicts itself.
   - Inline parent review breaks the pipeline (JSON format, validation, HTML report).

### Wait and re-dispatch protocol (mandatory)

After spawning a parallel batch:

```bash
# 1. Record batch as in-flight (do this once per batch launch)
python scripts/record_dispatch.py "<run_dir>" --type review --action start

# 2. WAIT — do not spawn anything else until this exits
python scripts/wait_for_dispatch.py "<run_dir>" --type review

# 3. Verify outputs
python scripts/verify_dispatch.py "<run_dir>" --type review
```

If step 2 exits **0** (all outputs present): proceed to step 3, then next pipeline step.

If step 2 exits **2** (timeout or stale subagents, still missing): redispatch **only** missing units:

```bash
python scripts/prepare_redispatch.py "<run_dir>" --type review
# Manifest only — does NOT mark in_flight. Dispatch subagents, then record:
# Read reviews/_redispatch_review_manifest.json — dispatch ONLY those agents
python scripts/record_dispatch.py "<run_dir>" --type review --action start --batch-kind redispatch
python scripts/wait_for_dispatch.py "<run_dir>" --type review
python scripts/verify_dispatch.py "<run_dir>" --type review
```

Use `--type validation`, `--type cross-review`, or `--type cross-validation` for other steps.

**While ledger status is `in_flight`, the ONLY allowed action is `wait_for_dispatch.py`.** No verify, no redispatch, no Continue/resume, no second parallel launch for the same step.

Check status anytime:
```bash
python scripts/record_dispatch.py "<run_dir>" --type review --action status
```

### Subagent suitability

Choose a subagent that can read files, write JSON to the exact path in the prompt, and perform multi-step code analysis — not a docs-only or help-only agent.

**Red flags = dispatch failed or duplicated:**
- Subagent completed but output file was not written
- Subagent used no file/read tools (when your UI shows tool-use count)
- Parent says "I'll do the review myself" instead of re-dispatching
- Parent ran `verify_dispatch.py` before `wait_for_dispatch.py` returned
- Parent re-dispatched a subagent while the original run for that unit was still in progress
- Parent spawned "Continue agent …" while waiting for the initial batch
- Parent re-launched agents because of `No task found with ID` or similar polling error
- Parent says it "combined changes into batches" or dispatched fewer subagents than `agent_count`
- One subagent asked to review more than one `change_id` (Step 3 per-change review only)
- Step 3.1: multiple agents like `review change 1541988+1562265+1549280` (must be ONE agent for ALL changes)
- Error: `Cannot create agent worktree` (subagent used worktree isolation from a non-git cwd)
- Error: `Invalid input: expected "worktree"` for isolation (you passed `none` — omit the parameter)

### Parallel batch procedure

1. Run `prepare_*_dispatch.py` — produces manifest JSON with `dispatch_prompt` bootstraps and `prompt_file` paths
2. Read the manifest (one `Read` call — should be a few KB, not tens of KB; full prompts live in `prompt_file`)
3. Spawn ALL subagents in one parallel batch using your platform's mechanism — pass each agent's `dispatch_prompt`, not the contents of `prompt_file`
4. Run `python scripts/record_dispatch.py "<run_dir>" --type review --action start`
5. Run `python scripts/wait_for_dispatch.py "<run_dir>" --type review` — **do nothing else until it exits**
6. Run `python scripts/verify_dispatch.py "<run_dir>" --type review`

```
WRONG:  Subagent(1) → wait → Subagent(2) → wait → Subagent(3)
WRONG:  3 subagents each reviewing 3-4 changes (10 changes → 3 agents)
RIGHT:  [Subagent(1), Subagent(2), ..., Subagent(N)]  ← N = agent_count, one change each
```

Each `(project, change_id)` pair gets its OWN subagent — never combine multiple changes in one subagent. If `agent_count` is 10, you must spawn **10** subagents.

**After dispatch:** run `record_dispatch.py` then `wait_for_dispatch.py`. Never re-dispatch a unit while its original subagent is still running.

**If you are about to spawn the second subagent in a new message after the first already returned — STOP. Re-read the manifest and dispatch ALL remaining subagents together.**

**If you see `No task found with ID` or cannot poll agent status — STOP. Run `wait_for_dispatch.py`. Do NOT spawn Continue/resume agents.**

### Platform notes (orchestrator adapts tool to rules above)

| Platform | Typical mechanism | Pitfall to avoid |
|----------|-------------------|------------------|
| **Cursor** | Task / Agent tool with a general-purpose subagent | Continue/resume in-flight agents; polling Task IDs; verify before wait |
| **Claude Code** | Subagent spawn **without** `isolation` param | Continue/resume while batch in_flight; `No task found with ID` → wrongly redispatch |

**Claude Code stale-subagent detection:** `wait_for_dispatch.py` monitors `subagents/*.jsonl` mtimes in the parent session directory (auto-detected via `CLAUDE_CODE_SESSION_ID` or stored in `_dispatch_ledger.json` when `record_dispatch.py` runs). If no batch subagent jsonl has been updated for 5 minutes (`--subagent-idle-timeout 300`, default), the wait exits with code **2** and `STALE_SUBAGENTS` so you can run `prepare_redispatch.py` instead of blocking for the full 2h timeout. Override with `--claude-session-dir` if auto-detection fails.
| **Codex / Gemini** | Parallel task APIs | Parent doing all reviews sequentially |
| **Qoder** | Quest Agent mode, Experts mode, or custom subagents (`/create-subagent`) with Skills | Team Lead / parent doing review inline instead of dispatching subagents with each entry's `dispatch_prompt` |
| **Trae** | `Task` tool — multiple calls in one message; pick `subagent_type` from your runtime enum | Inlining `prompt_file` into Task calls; truncating bootstrap prompts; wrong or docs-only subagent type; parent fallback after Task errors |

## Output File Structure

```
<resolved_cwd>/                       ← shared base (persists git repos)
    workspace/<workspace_path>/       ← git repos, reused across runs
    review-<timestamp>/               ← per-run directory
        change_summary.json           ← change metadata (from setup)
        reviews/
            <ws_path>-<id>.diff       ← per-change diffs (from setup)
            <ws_path>-<id>_findings.json  ← per-agent findings (from Step 3)
            _cross_project_index.json     ← compact interaction index (from Step 3.1)
            _cross_project_index.md       ← human-readable interaction index (from Step 3.1)
            _validation_findings_<id>.json ← per-change findings slice (from Step 4b)
            _validation_prompt_<id>.txt     ← validation instructions (from Step 4b)
        all_findings.json             ← consolidated (from Step 3.5)
        verified_findings.json        ← validation results (from Step 4)
        issues.json                   ← filtered issues (from Step 5)
        report-20260629232928-review-topic-engd-code-review-test.html  ← final report (from Step 5)
        progress.json                 ← pipeline progress (auto-updated)
```

---

## Step 0: Create Base Directory

**Run this script — do NOT construct the path yourself:**
```bash
resolved_cwd=$(python scripts/init_review.py "<input>")
```

This creates `$HOME/code-review/<correct-prefix>/` and prints the absolute path. Use the printed value as `resolved_cwd` for all subsequent steps.

**Never use `$(pwd)` for `resolved_cwd`.**

## Step 1: Parse Input

- Topic: `topic:<name>` (e.g., `topic:3300608`)
- Change IDs: `<id1>,<id2>,...` (e.g., `1536703,1536704`)

## Step 2: Setup

```bash
python scripts/setup_review.py "<input>" "$resolved_cwd"
```

This queries Gerrit over SSH for metadata, then runs a **fast HTTPS access check** on each change page (`https://<host>/gerrit/c/<project>/+/<id>`). It prints a **Gerrit access check table** and **stops immediately** on the first failure — no clone, cherry-pick, or diff extraction until every change page is reachable. On success it clones repos in parallel from mirror, cherry-picks (parallel across projects, serial within each project), writes `change_summary.json`, and extracts diffs.

**Cherry-pick conflict policy (hard abort):** The first fetch failure or merge conflict on **any** change aborts setup immediately — `git cherry-pick --abort` on the failed repo, cancel other in-flight cherry-picks, exit code 1. No `change_summary.json`, no diffs, no Steps 3–5. Git repos persist in `<resolved_cwd>/workspace/` (may need manual reset if a conflict left state behind).

**Gerrit access gate:** Status `OK` means the change web URL returned HTTP 200 (not a login redirect). Any `FAILED` row stops setup. Use VPN or set `GERRIT_HTTP_COOKIE` from your browser session if needed. Optional: `GERRIT_HTTP_TIMEOUT` (default 3s).

Env vars: `GERRIT_HOST`, `GERRIT_PORT`, `GERRIT_USER`, `GERRIT_HTTP_TIMEOUT`, `GERRIT_HTTP_COOKIE`, `MIRROR_REF`, `MIRROR_URL`, `MIRROR_ROOT`. See `python scripts/setup_review.py --help`.

## Step 3: Parallel Multi-Model Review

**3a — Generate dispatch manifest (one command):**
```bash
python scripts/prepare_review_dispatch.py "<run_dir>"
```
This reads `change_summary.json`, generates all review prompts, and writes `_review_manifest.json` containing every agent's full prompt.

**3b — Dispatch ALL review subagents in parallel (see Parallel Subagent Dispatch Protocol):**

1. Read `<run_dir>/reviews/_review_manifest.json`
2. Let N = `agent_count` from the manifest (must equal number of changes)
3. Spawn **exactly N** subagents — one per `agents[]` entry, each with that entry's `dispatch_prompt` and `description`
4. **Dispatch all N subagents in one parallel launch** — non-negotiable; never merge entries
5. **Do not pass `isolation`** on spawn — omit the parameter entirely

Each subagent reads full instructions from `prompt_file` and writes to `output_path` / `<run_dir>/reviews/<findings_output>` from the manifest.

**3c — Wait, then verify review subagents completed:**

```bash
python scripts/record_dispatch.py "<run_dir>" --type review --action start
python scripts/wait_for_dispatch.py "<run_dir>" --type review
python scripts/verify_dispatch.py "<run_dir>" --type review
```

If `wait_for_dispatch.py` exits 2 (timeout): `prepare_redispatch.py` → dispatch **only** `_redispatch_review_manifest.json` → record → wait → verify.

Do NOT run verify before wait returns. Do NOT re-dispatch while ledger status is `in_flight`. Do NOT review inline in the parent.

**STOP after 3c if `PROJECT_COUNT > 1`:** The script prints a warning when `_cross_project_findings.json` is missing. You MUST complete Step 3.1 before Step 3.5 or Step 4. `consolidate_findings.py` will exit with an error if you skip it.

## Step 3.1: Cross-Project Review (multi-project only)

**Check `PROJECT_COUNT` from the `prepare_review_dispatch.py` stdout output (Step 3a). You MUST read the actual script output. Do NOT count projects yourself or infer the value. If `PROJECT_COUNT=1`, skip to Step 3.5. If `PROJECT_COUNT > 1`, continue.**

**IMPORTANT: Always run this step for multi-project topics, even if per-project agents returned 0 findings. Cross-project bugs (API mismatches, dependency scope mismatches, shared state races) are invisible to per-project agents and can only be found by reviewing interactions BETWEEN projects.**

**Do NOT run Step 3.5 (validate/consolidate) or Step 4 (validation) until Step 3.1 completes.** An empty cross-project result is `[]` written to `_cross_project_findings.json` — that is different from the file being missing.

**3.1a — Generate cross-project index, prompt, and manifest:**
```bash
python scripts/prepare_cross_project_dispatch.py "<run_dir>"
```
This writes `_cross_project_index.json`, `_cross_project_index.md`, `_cross_project_prompt.txt`, and `_cross_project_manifest.json`. The index gives the cross-project agent a compact map of changed projects, Android-system signals, and likely provider/consumer edges so large topics do not require loading every raw diff upfront. The manifest sets `agent_count: 1` and lists **all** change IDs — do not split them.

**3.1b — Dispatch exactly ONE cross-project review subagent:**

Read `<run_dir>/reviews/_cross_project_manifest.json`. Spawn **one** subagent with the full `prompt_file` (`subagent_role: cross_project_review`; omit `isolation`). It reviews **all** changes across **all** projects, reads `_cross_project_index.md` first to build an interaction matrix, then opens targeted diffs/workspace files for high-risk edges. It must **not** perform an upfront sequential read of every raw diff; raw diffs are evidence files opened only for selected cross-project edges. It writes **only** `<run_dir>/reviews/_cross_project_findings.json` (write `[]` if no issues).

**WRONG:** `review change 1541988+1562265+1549280`, one agent per project, or multiple cross-project agents.  
**RIGHT:** One agent, one prompt, one output file covering every change in the topic.

**3.1c — Verify cross-project review completed:**
```bash
python scripts/record_dispatch.py "<run_dir>" --type cross-review --action start
python scripts/wait_for_dispatch.py "<run_dir>" --type cross-review
python scripts/verify_dispatch.py "<run_dir>" --type cross-review
```
Run `record_dispatch.py` immediately after spawning the single cross-project subagent, then wait. This MUST pass before Step 3.5. If `wait_for_dispatch.py` exits 2, run `prepare_redispatch.py "<run_dir>" --type cross-review`, dispatch the one redispatch agent, record, wait, then verify. Do NOT spawn a second copy while the first is still running.

## Step 3.5: Validate & Consolidate

**3.5a — Validate format:**
```bash
python scripts/validate_findings.py "<run_dir>"
```
If validation fails:
- **Fixable** (line range strings): re-run with `--fix`
- **Content errors** (identical codes, missing fields, bad types): **re-dispatch** the review agent for that (project, change_id) after its prior run has finished, passing the validation errors so it can self-correct
- Verify number of `*_findings.json` files matches change count. Missing after batch complete = re-dispatch.

**3.5b — Consolidate ALL findings (per-project + cross-project):**
```bash
python scripts/consolidate_findings.py "<run_dir>"
```
This picks up ALL `*_findings.json` files (per-project AND `_cross_project_findings.json`) and merges them into `all_findings.json`. **Fails with an error if `PROJECT_COUNT > 1` and `_cross_project_findings.json` is missing.** Read the `CROSS_PROJECT_FINDINGS` value from the output for Step 4.1 — only trust `CROSS_PROJECT_FINDINGS=0` when the message says `Step 3.1 completed`.

## Step 4: Parallel Per-Change Validation

**4a — Re-validate:**
```bash
python scripts/validate_findings.py "<run_dir>" --report
```

**4b — Generate validation dispatch manifest (one command):**
```bash
python scripts/prepare_validation_dispatch.py "<run_dir>"
```
This groups **non-cross-project** findings by change_id, writes `_validation_findings_<CHANGE_ID>.json` and slim `_validation_prompt_<CHANGE_ID>.txt` files, and `_validation_manifest.json`. Findings with `cross_project: true` are excluded and validated only in Step 4.1.

**4c — Dispatch ALL validation subagents in parallel (same protocol as Step 3):**

Skip this step if the manifest has 0 groups (all findings are cross-project).

1. Read `<run_dir>/reviews/_validation_manifest.json`
2. Let M = number of groups
3. For each group, spawn one subagent with that group's `dispatch_prompt` and `description`
4. **Dispatch ALL M subagents in one parallel batch** — non-negotiable

Each subagent reads `prompt_file` and `findings_file`, then writes to `output_path` / `<run_dir>/reviews/_verified_<CHANGE_ID>.json`.

**4c-verify — Wait, then verify validation subagents completed:**

```bash
python scripts/record_dispatch.py "<run_dir>" --type validation --action start
python scripts/wait_for_dispatch.py "<run_dir>" --type validation
python scripts/verify_dispatch.py "<run_dir>" --type validation
```

If wait times out: `prepare_redispatch.py --type validation` → dispatch only `_redispatch_validation_manifest.json` → record → wait → verify.

Skip if manifest has 0 groups. Do NOT validate inline in the parent.

## Step 4.1: Cross-Project Validation (multi-project only)

**Check `CROSS_PROJECT_FINDINGS` from the `consolidate_findings.py` output (Step 3.5b). You MUST run the script and read its actual stdout output. Do NOT infer or guess this value from per-project findings count — cross-project findings are independent of per-project findings. If the actual output says `CROSS_PROJECT_FINDINGS=0`, skip to Step 4d. If it says `CROSS_PROJECT_FINDINGS > 0`, continue.**

**4.1a — Generate cross-project validation prompt:**
```bash
python scripts/generate_cross_project_validation_prompt.py "<run_dir>" \
    --output "<run_dir>/reviews/_cross_project_validation_prompt.txt"
```

**4.1b — Dispatch ONE cross-project validation subagent:**

Read `<run_dir>/reviews/_cross_project_validation_prompt.txt` (findings are read from `_cross_project_findings.json` by the subagent, not inlined). Dispatch a single subagent with a bootstrap pointing at the prompt file (omit `isolation`). It verifies cross-project interaction chains across ALL workspaces and writes results to `<run_dir>/reviews/_verified_cross_project.json`.

**4d — Validate verified schema, then merge:**

Run after Step 4c-verify **and** Step 4.1 (when applicable). Do NOT merge until validation passes.

```bash
python scripts/validate_verified.py "<run_dir>"
python scripts/merge_validation_results.py "<run_dir>"
```

`validate_verified.py` checks all `reviews/_verified_*.json` files for the 8-field per-change schema (or 10-field schema for `_verified_cross_project.json`). On failure, re-dispatch the affected validation subagent **after** its prior run has finished, with the error output — do NOT fix inline in the parent.

**Sanity checks:**
- Cross-check `verified_findings.json` entry count against `all_findings.json`
- Verify rationales reference the correct functions/lines
- Check for misplaced output files in `<resolved_cwd>/` (agents sometimes write to wrong directory — move them to `<run_dir>/`)

## Step 5: Build Issues & Generate Report

**5a — Build issues.json:**
```bash
python scripts/build_issues.py "<run_dir>"
```
Keeps only VALID+PARTIAL findings, applies severity adjustments, attaches project metadata. Preserves all 13 fields. Every finding must have non-null `change_id`.

**5b — Generate HTML report (run ONCE for all findings):**
```bash
python scripts/generate_html_report.py \
    --workspace <resolved_cwd>/workspace \
    --branch <branch_name> \
    --issues <run_dir>/issues.json \
    --change-summary <run_dir>/change_summary.json
```
Omit `--output` to write `<run_dir>/report-<timestamp>-<topic_prefix>.html` (e.g. `report-20260628003845-review-1569504.html`). Omit `--commit-ref` if empty. Report auto-discovers git repos in workspace.

**5c — Final validation:**
```bash
python scripts/validate_findings.py "<run_dir>"
```

## Resume Capability

Each script writes to `<run_dir>/progress.json` on success. Check it to skip completed steps:
```bash
cat <run_dir>/progress.json
```
If `"completed"` includes `"setup"` and `"consolidate"`, skip to Step 4. If `"merge_validation"` is done, skip to Step 5. For multi-project topics, `"cross_project_review"` must be in `"completed"` before consolidate.

---

## Reference

- **13-field finding format**: `python scripts/findings_format.py`
- **8/10-field verdict format**: `python scripts/validate_verified.py --help` (see `data_formats.py` verified_findings section)
- **All data formats**: `python scripts/data_formats.py`
- **HTML report CSS**: `assets/report.css` (HTML is generated inline by `generate_html_report.py`)
- **Shared utilities** (JSON loading, SSH, progress): `scripts/shared.py`
