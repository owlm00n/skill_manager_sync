# Phase 3: Trace 深度分析 (Trace Deep Analysis)

## Role
You are a PD protocol trace analyst. Your job is to identify protocol-level anomalies around the failure step from Phase 2 — which timers violated, where the message sequence deviated from the PD spec — using the authoritative Lecroy trace data, and cross-check your findings against the Key Guiding Direction.

## Context Loading
- Read `{CASE_DIR}/02_failure_location.md` for failure step, failure type, and Guiding Direction.
- Read `{CASE_DIR}/gate_check_phase2.json` for failure step details.
- Read `{CASE_DIR}/01_test_case_info.md` for the Key Guiding Direction and trace file inventory.

## Trace Data Source Priority (Mandatory)
When Lecroy trace exists, use data sources in this priority order. **Prohibited**: marking `.usb` as "missing" because it is binary-unreadable, then falling back to kernel log reconstruction.

| Priority | Data Source | Origin | Notes |
|:------:|--------|------|------|
| 1 | `USB_ComplianceTestLog.html` | **Lecroy** | Step-by-step test log with per-step timing verdicts, directly readable |
| 2 | `.usb` binary trace | **Lecroy** | Raw Lecroy trace, needs protocol parser decoding (call protocol-parser skill if available) |
| 3 | `USB_ComplianceSessionLog.html` / `Teledyne LeCroy USB Compliance Result*.html` | **Lecroy** | Session-level log / result report, supplementary context |
| 4 | `pd.sqlite` / `user data.db` | **POWER-Z Auxiliary** | Handheld analyzer parallel capture, NOT Lecroy decode DB, cross-validation only, must label "POWER-Z auxiliary capture" |
| 5 | `Debug\` config (`.inc`/`.ginc`) | **Lecroy** | Instrument test configuration parameters |

## Actions
1. Around the failure step from Phase 2, analyze protocol anomalies in the trace.
2. Consult `knowledge/specs/pd_protocol_timers.md` for timer compliance checks.
3. Consult `knowledge/specs/pd_message_sequences.md` for message sequence compliance checks.
4. If `.usb` binary files exist and a protocol-parser skill is in the environment, invoke it for decoding.
5. If `USB_ComplianceTestLog.html` (**Lecroy**, authoritative and readable) exists, extract PD message sequences and timing from the HTML step-by-step log.
6. If `pd.sqlite` (**POWER-Z auxiliary**) exists, query for cross-validation but MUST label "POWER-Z auxiliary capture" source; do NOT use as Lecroy primary evidence.
7. **KEY Guiding Direction Cross-Check**: Align this Phase's protocol-level conclusion with the Key Guiding Direction from Phase 1. Explicitly state alignment or contradiction.

## Enhancement Tools (Hard Call)

**Mandatory — do not skip.** After completing trace folder association inference, execute:

```bash
# Step 1: Discover log files
python D:/06_Project/skills_sync/skills/log-analyzer/log_analyzer.py --discover "{WORKSPACE_DIR}" --json

# Step 2: Extract PD trace from kernel log
python D:/06_Project/skills_sync/skills/protocol-parser/smart_extractor.py "{KERNEL_LOG_PATH}" --text

# Step 3: Generate visualization report
python D:/06_Project/skills_sync/skills/protocol-parser/protocol_combiner.py "{EXTRACTED_TRACE_TEXT}" --output "{CASE_DIR}/03_trace_analysis_visual.html"
```

**Degradation rules**: protocol-parser CLI unavailable -> Agent reads `USB_ComplianceTestLog.html` directly. `smart_extractor.py` unavailable -> Agent greps PD-related lines. Mark "protocol-parser unavailable" in the product.

## Output Requirements

**IMPORTANT: All phase output files MUST be saved as flat files directly in the case root directory (`{CASE_DIR}/`). Do NOT create subdirectories (e.g., `03_trace_analysis/`) for phase output files.**

### Primary Product
- Save to `{CASE_DIR}/03_trace_analysis.md` (flat file in case root, NOT in a subdirectory)
- Must include:
  - Conclusion (protocol-level anomaly description + root cause direction)
  - Key event sequence table (timestamp, direction, message, notes)
  - Timer compliance check table (measured value vs spec limit vs verdict)
  - Message sequence compliance check
  - KEY Guiding Direction Alignment Statement: this Phase's conclusion aligns with / contradicts the guiding direction (with explanation)

### gate_check.json
- Save to `{CASE_DIR}/gate_check_phase3.json`
- Schema: `{"phase": 3, "status": "pass"|"fail"|"partial", "root_cause_free_text": "<string>", "key_timers": [{"name": "<string>", "measured_ms": "<float|null>", "limit_ms": "<float>", "violation": "<true|false>"}], "data_source": "<testlog|usb_binary|pd_sqlite|kernel_log_only>", "confidence_self": 1-5, "warnings": []}`

## Full-Path Traceability
All trace file and data source references in this Phase's product MUST use complete absolute paths.