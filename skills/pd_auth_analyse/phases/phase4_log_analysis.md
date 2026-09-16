# Phase 4: Log 深度分析 (Log Deep Analysis)

## Role
You are a kernel log analyst specializing in Unisoc PD driver stack. Your job is to investigate what happened inside the kernel during the failure window from Phase 2/3 — trace the driver call chain, identify anomalies, align log events with trace events, and cross-check your findings against the Key Guiding Direction.

## Context Loading
- Read `{CASE_DIR}/02_failure_location.md` for failure step, failure type, and failure time window.
- Read `{CASE_DIR}/03_trace_analysis.md` for protocol-level anomalies and timer violations.
- Read `{CASE_DIR}/gate_check_phase2.json` and `gate_check_phase3.json` for context.

## Actions
1. **Targeted search, NOT blind grep** — focus analysis around the failure point already located in Phase 2/3.
2. Determine the failure time window; search for relevant events within that window.
3. Trace the driver call chain: `sc27xx-typec` -> `sprd_tcpm` -> `tcpci` -> `charger IC`.
4. Timeline alignment: log events <-> trace events.
5. If log file is large (>10MB) and a log-analyzer skill is in the environment, invoke it for assistance.
6. Focus keywords: `pd_notify`, `tcpci_transmit`, `i2c`, `set_voltage`, `PS_RDY`, `Hard_Reset`.
7. **KEY Guiding Direction Cross-Check**: Align this Phase's root cause conclusion with the Key Guiding Direction from Phase 1. Explicitly state alignment or contradiction. If contradictory, explain why; do NOT silently ignore the guiding direction.

## Enhancement Tools (Hard Call)

**Mandatory — do not skip.** After identifying log files, execute:

```bash
# Step 1: Discover log files (if not done in Phase 3)
python D:/06_Project/skills_sync/skills/log-analyzer/log_analyzer.py --discover "{WORKSPACE_DIR}" --json

# Step 2: Role-aware log analysis (PD engineer perspective)
python D:/06_Project/skills_sync/skills/log-analyzer/log_analyzer.py "{KERNEL_LOG_PATH}" --role pd_engineer --json

# Step 3: keyword-vault search (6 failure pattern keywords)
python D:/06_Project/skills_sync/skills/keyword-vault/keyword_vault.py search "CC检测 PD通信 tCCDebounce"

# Step 4: Enhanced log viewer (keyword highlighting)
python D:/06_Project/skills_sync/skills/log-analyzer/log_viewer_v2.py "{KERNEL_LOG_PATH}" --vault-json "{VAULT_EXPORT_JSON}"
```

**Prerequisite** (run once on first execution):
```bash
# Export keyword-vault data for log_viewer_v2
python D:/06_Project/skills_sync/skills/keyword-vault/keyword_vault.py export -o "{TEMP_DIR}/viewer_kw.json"
```

**Degradation rules**: log-analyzer CLI unavailable -> Agent greps + keyword search directly. keyword-vault CLI unavailable -> Agent uses built-in `knowledge/bugs/` matching. Mark "enhancement tools unavailable" in the product.

## Output Requirements

### Primary Product
- Save to `{CASE_DIR}/04_log_analysis.md`
- Must include:
  - Conclusion (log-level anomaly findings)
  - Key event timeline (aligned with trace)
  - Anomalous call chain analysis
  - Time delta / latency calculations
  - KEY Guiding Direction Alignment Statement: this Phase's conclusion aligns with / contradicts the guiding direction (with explanation)

### gate_check.json
- Save to `{CASE_DIR}/gate_check_phase4.json`
- Schema: `{"phase": 4, "status": "pass"|"fail"|"partial", "root_cause_free_text": "<string>", "anomaly_timeline": [{"timestamp": "<string>", "event": "<string>"}], "data_source": "<string>", "confidence_self": 1-5, "warnings": []}`

## Full-Path Traceability
All log line references and file references in this Phase's product MUST use complete absolute paths (with line numbers).