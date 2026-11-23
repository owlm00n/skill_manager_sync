export const meta = {
  name: 'bugzilla-commit',
  description: 'Hard Gate for Bugzilla writes — validates custom_fields before allowing status transitions',
  phases: [
    { title: 'Validate', detail: 'Check required custom_fields for target status' },
    { title: 'Preview', detail: 'Generate reply preview with cf_* fields + Token' },
    { title: 'Send', detail: 'Read preview, parse cf_* fields, call bug_commit live' },
  ],
  whenToUse: 'Anytime the AI needs to change a Bugzilla bug status (commit, reply, rootcause, fixed). This workflow enforces the Hard Gate that Root-Caused status requires cf_root_cause/cf_resolution/cf_testing_suggestion/cf_impact_customer. AI cannot bypass this — if custom_fields are missing, the workflow rejects before any API call.',
}

// ============================================================
// Bugzilla Commit Workflow — Hard Gate Enforcement
// ============================================================
// This is the MECHANISM layer. Not prose rules, not SKILL.md text.
// The Workflow runtime enforces that custom_fields validation happens
// BEFORE any Bugzilla API call.
//
// Three layers of defense:
//   A. Code-level: update_bug_status() validates status_required_fields
//   B. Knowledge:   SKILL.md documents which statuses require which fields
//   C. Gate:        THIS WORKFLOW — AI must invoke it, and it rejects
//                   invalid requests at the agent level before API calls.
// ============================================================

// ── Status → Required Fields Mapping (mirrors bugzilla_instances.json) ──
const STATUS_REQUIRED_FIELDS = {
  "Root-Caused": {
    "cf_root_cause": "[1.Root Cause]",
    "cf_resolution": "[2.Resolution]",
    "cf_testing_suggestion": "[3.Testing Suggestion]",
    "cf_impact_customer": "[4.Impact for customer]",
  },
  "Fixed": {},
  "Code-Committed": {},
  "Need_Info": {},
  "Assigned": {},
  "Resolved": {},
  "Closed": {},
  "Reopened": {},
  "TobeVerified": {},
  "WONTFIX": {},
  "Duplicated": {},
  "Invalided": {},
}

// ── Phase 1: Validate ────────────────────────────────────────
phase('Validate')

// `args` must contain: { bug_id, target_status, custom_fields?, comment_text? }
const { bug_id, target_status, custom_fields, comment_text } = args || {}

if (!bug_id) {
  log('❌ FATAL: Missing bug_id in args')
  return { success: false, error: 'bug_id is required' }
}
if (!target_status) {
  log('❌ FATAL: Missing target_status in args')
  return { success: false, error: 'target_status is required' }
}

// Resolve short name to actual Bugzilla status
const STATUS_MAP = {
  "rootcause": "Root-Caused",
  "rootcaused": "Root-Caused",
  "codecommitted": "Code-Committed",
  "fixed": "Fixed",
  "tobeverified": "TobeVerified",
  "needinfo": "Need_Info",
  "assigned": "Assigned",
  "resolved": "Resolved",
  "closed": "Closed",
  "reopened": "Reopened",
  "reopen": "ReOpen",
  "wontfix": "WONTFIX",
  "duplicated": "Duplicated",
  "invalided": "Invalided",
}
const resolvedStatus = STATUS_MAP[target_status.toLowerCase()] || target_status
const required = STATUS_REQUIRED_FIELDS[resolvedStatus] || {}

log(`Bug: ${bug_id}`)
log(`Target status: ${target_status} → ${resolvedStatus}`)
log(`Required fields: ${Object.keys(required).length > 0 ? Object.values(required).join(', ') : '(none)'}`)

// === HARD GATE ===
if (Object.keys(required).length > 0) {
  if (!custom_fields || typeof custom_fields !== 'object') {
    const missing = Object.values(required)
    log(`⛔ HARD GATE REJECTED: Status "${resolvedStatus}" requires custom_fields: ${missing.join(', ')}`)
    log('')
    log('The AI MUST provide these fields. This workflow will not proceed.')
    log('Example:')
    log('  custom_fields: {')
    for (const [k, label] of Object.entries(required)) {
      log(`    "${k}": "<${label}>",`)
    }
    log('  }')
    return {
      success: false,
      error: `HARD GATE: Status "${resolvedStatus}" requires custom_fields. Missing: ${missing.join(', ')}`,
      required_fields: required,
      gate: 'VALIDATE_CUSTOM_FIELDS',
    }
  }

  // Check each required field is present and non-empty
  for (const [cf_key, cf_label] of Object.entries(required)) {
    const val = custom_fields[cf_key]
    if (!val || (typeof val === 'string' && !val.trim())) {
      log(`⛔ HARD GATE REJECTED: "${cf_label}" (${cf_key}) is missing or empty`)
      return {
        success: false,
        error: `HARD GATE: "${cf_label}" (${cf_key}) is required but missing or empty`,
        required_fields: required,
        provided_fields: custom_fields,
        gate: 'VALIDATE_CUSTOM_FIELDS',
      }
    }
  }

  log('✅ All required custom_fields present:')
  for (const [k, v] of Object.entries(custom_fields)) {
    if (required[k]) {
      log(`  ${k}: ${v}`)
    }
  }
} else {
  log('✅ No required fields for this status')
}

// ── Phase 2: Preview ─────────────────────────────────────────
phase('Preview')

// Generate preview via agent — it calls prepare_customer_reply() with custom_fields
const previewResult = await agent(
  `Call prepare_customer_reply() in bug_core.py with the following parameters:

Bug ID: ${bug_id}
Target Status: ${target_status}
Custom Fields: ${JSON.stringify(custom_fields || {})}
Comment Text: ${comment_text || 'Please provide the analysis content for this bug.'}

IMPORTANT:
1. Import prepare_customer_reply from bug_core module
2. Call: prepare_customer_reply(bug_id="${bug_id}", content=<analysis content>, new_status="${target_status}", custom_fields=${JSON.stringify(custom_fields || null)})
3. The function writes a preview .txt file to the Bug workspace with Token + cf_* fields in header
4. os.startfile() auto-opens the file for user review
5. Return the filepath from the result dict

Write a temporary Python script to execute this, then run it.`,
  {
    label: `preview:${bug_id}`,
    phase: 'Preview',
  }
)

log(`Preview result: ${previewResult}`)

// ── Phase 3: Send ────────────────────────────────────────────
phase('Send')

// The send step reads the preview file (which the user may have edited),
// parses the cf_* fields from header, and calls bug_commit(send_mode='live')
const sendResult = await agent(
  `Call send_customer_reply() in bug_core.py to send the reviewed reply:

Bug ID: ${bug_id}
Target Status: ${target_status}

IMPORTANT:
1. Import send_customer_reply from bug_core module
2. Call: send_customer_reply(bug_id="${bug_id}", new_status="${target_status}", instance="unisoc", use_combined=True)
3. This reads the preview file, parses cf_* fields from header, validates Token, and calls bug_commit(send_mode='live')
4. Report the result — success or failure with details

Write and execute a temporary Python script.`,
  {
    label: `send:${bug_id}`,
    phase: 'Send',
  }
)

log(`Send result: ${sendResult}`)

return {
  success: true,
  bug_id,
  target_status: resolvedStatus,
  custom_fields_provided: Object.keys(custom_fields || {}).length > 0,
  preview: previewResult,
  send: sendResult,
}