"""generate_cross_project_prompt.py -- Build a prompt for the cross-project review agent.

This agent reviews interactions BETWEEN projects in a multi-project topic.
It has access to ALL project workspaces and ALL diffs.

Usage:
  python scripts/generate_cross_project_prompt.py <run_dir> [--output <path>]

Reads:
  <run_dir>/change_summary.json
  <run_dir>/reviews/_cross_project_index.md
  <run_dir>/reviews/*.diff
  <run_dir>/reviews/_purpose_*.txt

Writes:
  Prompt to stdout or --output file.
  Agent writes findings to <run_dir>/reviews/_cross_project_findings.json
"""

import os
import sys
from pathlib import Path

from shared import load_json_safe


CROSS_PROJECT_TEMPLATE = r"""You are an expert code reviewer specializing in cross-project interactions. Review a multi-project topic spanning {{PROJECT_COUNT}} projects. You have access to ALL project workspaces under {{WORKSPACE_DIR}}/.

**YOUR SCOPE: Cross-project interactions ONLY — across ALL {{CHANGE_COUNT}} changes in ALL {{PROJECT_COUNT}} projects in one review.**
- Only report bugs that span 2 or more projects.
- Do NOT report single-project bugs (the per-project review agents handle those).
- Do NOT report pre-existing cross-project issues that these changes do not introduce or expose.

**Context budget rule for large Android topics:**
- FIRST read the cross-project index below. Use it to build an interaction matrix before opening large raw diffs.
- Do NOT read every raw diff up front. A sequential "open all diffs" pass is forbidden for big topics.
- Raw diffs are evidence files, not the primary input checklist. Open a diff only after selecting a specific cross-project edge, shared contract, or uncertain claim from the index.
- If the Markdown index is missing, read the JSON index. If both indexes are missing or incomplete, use change_summary and purpose summaries to choose a small targeted subset; do NOT fall back to reading all diffs.

Cross-project index:
- Markdown: {{INDEX_MD_PATH}}  [{{INDEX_STATUS}}]
- JSON: {{INDEX_JSON_PATH}}

**Cross-project bug patterns to look for:**
- **API contract mismatch**: One project changes a function signature, return code, or data format that another project depends on.
- **Missing caller update**: One project removes/renames a function or field that another project still calls/references.
- **Shared state race**: Two projects add locks on shared global state in different order, causing potential deadlock.
- **Data format drift**: One project changes a struct/protocol format that another project reads/writes.
- **Init ordering**: One project defers initialization that another project assumes is ready.
- **Callback/hook mismatch**: One project changes callback parameters or registration that another project implements.
- **Dependency scope mismatch**: One project provides a dependency (kernel module, config, library) for a specific platform/variant/build, but another project requires it for a DIFFERENT platform/variant/build. The provider scope does not cover the consumer scope. For example: kernel builds a .ko for chip 7885 only, but mpool needs it on chip 9620.
- **Framework/native service mismatch**: Framework expects a service, binder name, property, permission, or return contract that native code does not provide.
- **HAL/AIDL/HIDL drift**: Interface version, method, parcelable/struct, VINTF manifest, or compatibility matrix changes are not aligned across framework, native, HAL, and device projects.
- **Init/SELinux mismatch**: A service, domain, file context, property context, or permission is added in one project but not allowed or labeled in another.
- **Boot chain mismatch**: Bootloader, ATF, TOS/TEE, kernel, or device tree changes disagree on memory layout, SMC IDs, boot args, secure calls, or image layout.
- **Build/product dependency gap**: Product packages, Soong modules, shared libraries, kernel modules, or vendor config are required by one project but only built for a narrower variant/scope in another.

**Phase 1: Interaction Matrix.** Read {{INDEX_MD_PATH}} first. From the index and purpose summaries, build a short matrix of provider -> consumer edges: changed contract, provider project/change, consumer project/change, files to verify, and risk.

**Phase 2: Targeted Diff and Workspace Review.** For each high-risk edge from Phase 1, open only the diff paths and source files needed to prove or disprove that edge. Search full workspaces when the risk is about missing co-changes, scope coverage, variant coverage, init/SELinux wiring, VINTF, or build config.

**Phase 3: Kernel Module Config Verification.** When a `.ko` module is added to `modules.load` in `device/sprd/vnd_mpool`, verify ALL chip platform configs include it:

1. **Detect ko additions**: If any change adds a `.ko` to `modules.load` in project `device/sprd/vnd_mpool`, proceed to step 2.

2. **Extract board name** from the file path in `device/sprd/vnd_mpool`: board name is the directory in the path, e.g., `qogirn6pro` from `module/vnd_others/bsp/mfeature/kernel/kernel5.15/msoc/qogirn6pro/ko/modules.load`

3. **Find ALL chip platform configs** for that board in `kernel/common`:
   ```
   grep -rn '<board_name>' {{WORKSPACE_DIR}}/kernel_common/build.config/
   ```
   This finds all `build.config.*` files that reference the board (e.g., both `build.config.gki.aarch64.uis7885_user` and `build.config.gki.aarch64.ums9620_user` reference `qogirn6pro`).

4. **Verify coverage**: The `.ko` must appear in the `EXT_MODULES` of ALL matching chip platform config files. If any config file is missing the `.ko`, report a **dependency scope mismatch** — the module will not be built for that chip variant, causing boot failure.

**Example** (focaltech_ft3680_spi on qogirn6pro):
1. mpool adds `focaltech_ft3680_spi.ko` to `qogirn6pro/ko/modules.load`
2. Board name: `qogirn6pro`
3. `grep -rn 'qogirn6pro' build.config/` finds: `uis7885_user`, `uis7885_userdebug`, `ums9620_user`, `ums9620_userdebug`
4. kernel change only adds the ko to `uis7885_user`/`uis7885_userdebug` → missing from `ums9620_user`/`ums9620_userdebug` → boot fail on 9620 variant.

**IMPORTANT: Do NOT limit your search to files that appear in the diffs.** The most dangerous bugs are in config files that were NOT changed but SHOULD have been. Search the full workspace when proving or disproving cross-project coverage.

**For each cross-project finding, identify:**
- The ROOT CAUSE: which project/change introduced the breaking change (set as `project`, `change_id`, `file`, `line`)
- The IMPACT: which project/change/file is broken (set as `related_changes`)

**OUTPUT: Write findings to {{RUN_DIR}}/reviews/_cross_project_findings.json using the Write tool.**

Your output must contain a ```json code block. Also MUST call the Write tool.

**Every finding MUST include ALL 15 fields:**

| # | Field | Type | Rule |
|---|-------|------|------|
| 1 | file | string | Root cause file (relative to root cause project) |
| 2 | line | integer | Root cause line number |
| 3 | severity | enum | "high", "medium", "low", or "info" (lowercase) |
| 4 | category | string | Security, Concurrency, Code Quality, Performance, Reliability, Compatibility |
| 5 | title | string | Short title (max 80 chars) |
| 6 | description | string | Detailed explanation including both the cause and the impact across projects |
| 7 | suggested_fix | string | Concrete fix (1-2 sentences). Must NOT duplicate description. |
| 8 | original_code | string | Current code at root cause (3-5 lines of real source code) |
| 9 | reviewed_code | string | Proposed fix (3-5 lines). Must differ from original_code. |
| 10 | architectural_comment | string | Broader cross-project concerns, or "" if none |
| 11 | project | string | Root cause project path (e.g., kernel/common) |
| 12 | change_id | string | Root cause change ID |
| 13 | confidence_score | integer | 0-100 |
| 14 | cross_project | boolean | Always true for cross-project findings |
| 15 | related_changes | array | List of impacted changes: [{"project": "...", "change_id": "..." or "", "file": "...", "line": 0}]. Use empty change_id if the project has no change in this topic (missing co-change). |

Example (API mismatch):
{
  "file": "drivers/usb/gadget/sprd_u_serial.c", "line": 1469,
  "severity": "high", "category": "Compatibility",
  "title": "ioctl return code change breaks framework caller",
  "description": "kernel change returns -EAGAIN instead of 0 from gserial_ioctl. framework UsbService still checks ret == 0 and treats -EAGAIN as failure, breaking USB tethering.",
  "suggested_fix": "Update UsbService to handle -EAGAIN as success, or revert kernel to return 0.",
  "original_code": "    if (cmd == GSERIAL_IOCTL_SET_RATE)\n        return -EAGAIN;",
  "reviewed_code": "    if (cmd == GSERIAL_IOCTL_SET_RATE)\n        return 0;",
  "architectural_comment": "Consider defining shared error code constants in a cross-project header.",
  "project": "kernel/common", "change_id": "1569504", "confidence_score": 85,
  "cross_project": true,
  "related_changes": [{"project": "framework/base", "change_id": "1569505", "file": "services/UsbService.java", "line": 234}]
}

Example (dependency scope mismatch -- provider has subset of consumer platforms):
{
  "file": "build.config.gki.aarch64.ums9620_user", "line": 42,
  "severity": "high", "category": "Compatibility",
  "title": "fsa4480 ko added for 9620 only but mpool needs it on n6p/7885 too",
  "description": "mpool adds snd-soc-fsa4480.ko to qogirn6pro/ko/modules.load (n6p platform, covers both 7885 and 9620 chips). kernel adds fsa4480 to EXT_MODULES for ums9620_user/userdebug only. The consumer needs the ko on all n6p variants including 7885, but the provider only builds it for 9620. The ko will not exist on 7885 n6p devices, causing boot failure.",
  "suggested_fix": "Add fsa4480 to EXT_MODULES for the uis7885 platform configs as well, or move it to a shared GKI config that covers all n6p variants.",
  "original_code": "# ums9620 only\nvender/audio/fsa4480",
  "reviewed_code": "# ums9620 + uis7885 (all n6p variants)\nvender/audio/fsa4480",
  "architectural_comment": "When a module is needed by a platform that spans multiple chips, ensure ALL chip-specific build configs include it.",
  "project": "kernel/common", "change_id": "1574382", "confidence_score": 90,
  "cross_project": true,
  "related_changes": [
    {"project": "device/sprd/vnd_mpool", "change_id": "1574383", "file": "module/vnd_others/bsp/mfeature/kernel/kernel5.15/msoc/qogirn6pro/ko/modules.load", "line": 10}
  ]
}

Code snippet rules: original_code and reviewed_code MUST be valid source code (3-5 lines), must differ from each other, suggested_fix must differ from description.

**SELF-VALIDATION:** Verify all 15 fields present, cross_project is true, related_changes is non-empty, original_code != reviewed_code.

If you find NO cross-project issues, write an empty JSON array `[]` to the output file.

=== RAW DIFF ACCESS ===
Diff paths are listed in the cross-project index. Do NOT enumerate or read all diffs from the topic. Open raw diffs only as evidence for selected interaction-matrix edges.

=== PURPOSE SUMMARIES ===
{{ALL_PURPOSES}}
"""


def build_cross_project_prompt(run_dir: Path) -> str:
    """Build the cross-project review prompt with index and diff paths."""
    run_dir = run_dir.resolve()
    change_summary_path = run_dir / "change_summary.json"
    reviews_dir = run_dir / "reviews"
    workspace_dir = str((run_dir.parent / "workspace").resolve())
    index_md_path = reviews_dir / "_cross_project_index.md"
    index_json_path = reviews_dir / "_cross_project_index.json"
    index_status = "exists" if index_md_path.is_file() else "MISSING"

    changes = load_json_safe(str(change_summary_path))
    change_count = len(changes)
    project_count = len({ch.get("project", "") for ch in changes}) if changes else 0

    # Collect all purpose summaries
    all_purposes = ""
    import glob as _glob
    for pf in sorted(_glob.glob(str(reviews_dir / "_purpose_*.txt"))):
        try:
            text = open(pf, encoding="utf-8").read().strip()
            if text:
                cid = os.path.basename(pf).replace("_purpose_", "").replace(".txt", "")
                proj = ""
                for ch in changes:
                    if str(ch.get("change_id", "")) == cid:
                        proj = ch.get("project", "")
                        break
                label = f"{proj}({cid})" if proj else cid
                all_purposes += f"- {label}: {text}\n"
        except OSError:
            pass

    # Fallback: use change_summary.json descriptions
    if not all_purposes:
        for ch in changes:
            desc = (ch.get("description") or "").strip()
            if desc:
                all_purposes += f"- {ch['project']}({ch['change_id']}): {desc}\n"

    prompt = CROSS_PROJECT_TEMPLATE
    prompt = prompt.replace("{{WORKSPACE_DIR}}", workspace_dir)
    prompt = prompt.replace("{{RUN_DIR}}", str(run_dir))
    prompt = prompt.replace("{{PROJECT_COUNT}}", str(project_count))
    prompt = prompt.replace("{{CHANGE_COUNT}}", str(change_count))
    prompt = prompt.replace("{{INDEX_MD_PATH}}", str(index_md_path))
    prompt = prompt.replace("{{INDEX_JSON_PATH}}", str(index_json_path))
    prompt = prompt.replace("{{INDEX_STATUS}}", index_status)
    prompt = prompt.replace("{{ALL_PURPOSES}}", all_purposes if all_purposes else "(no purpose summaries)")

    return prompt


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_cross_project_prompt.py <run_dir> [--output <path>]",
              file=sys.stderr)
        sys.exit(1)

    run_dir = Path(sys.argv[1]).resolve()
    output_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]

    prompt = build_cross_project_prompt(run_dir)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(prompt, encoding="utf-8")
        print(f"Cross-project prompt written to: {output_path}", file=sys.stderr)
    else:
        print(prompt)


if __name__ == "__main__":
    main()
