---
name: er-triage
description: >
  Platform Atlas ER ticket triage. Triggers automatically when the user drops any
  Jira URL (itential.atlassian.net/browse/...), mentions a ticket key like ER-508
  or PLAT-123, asks to "review the Atlas report", "triage the customer report",
  "draft customer recommendations", or references the Platform Health Program.
  Fetches the Atlas session export ZIP from Jira, analyzes the compliance data,
  classifies every failed rule into three customer-ready severity tiers
  (⛔ Mandatory / ⚠️ Recommended / ℹ️ Optional), and drafts a professional summary.
  Optionally posts the draft back as an internal or external Jira comment.
  Use this skill proactively — if a Jira URL is present, always run the triage
  rather than asking the user what they want done with it.
---

You are triaging a Platform Atlas ER ticket so the SE team can quickly send
customer-facing recommendations without reading the entire 80-page HTML report.

## When this skill fires

The user pasted a Jira URL or ticket key. Extract:
- **Ticket key**: the `ER-XXX` / `PLAT-XXX` fragment of the URL or raw text
- **Comment ID**: the `focusedCommentId=NNNNNN` query param if present — use it
  to identify which session the customer uploaded (pick the attachment closest in
  time to that comment's timestamp)

If no Jira URL was given but the user asked to "review" or "triage" a report and
provided a file path instead, skip Steps 1-2 and go straight to Step 3.

---

## Step 1 — Fetch the Jira ticket

Use `getJiraIssue` (Jira MCP):
- `cloudId`: `2ece816a-62e4-4222-8518-b5507d198470`
- `issueIdOrKey`: the ticket key (e.g. `ER-508`)

Show the user a one-line ticket summary: title, customer name, status, and how
many attachments were found.

---

## Step 2 — Download the Atlas session export ZIP

From the ticket's attachment list:
1. Prefer files matching `ATLAS-*.zip` (the `platform-atlas session export` output)
2. Fall back to any `.zip` or `.tar.gz`
3. If multiple Atlas ZIPs exist, prefer the most recently uploaded; if
   `focusedCommentId` was given, prefer the one whose `created` timestamp is
   closest to that comment's `created` timestamp

Download the attachment. Jira attachment URLs require Bearer-token auth:

```bash
curl -sL -H "Authorization: Bearer $JIRA_API_TOKEN" \
  "<attachment-content-url>" \
  -o /tmp/atlas-<ticket-key>.zip
```

If `$JIRA_API_TOKEN` is not set, check `$ATLASSIAN_TOKEN` or `$JIRA_TOKEN`.
If none are set, tell the user and ask them to export the ZIP manually and
provide the path — then jump to Step 3 with that path.

---

## Step 3 — Analyze the report

Find the `analyze_report.py` script. It lives alongside this SKILL.md in the
`platform-atlas-report-analyzer` repo. The canonical path is:
`~/Documents/IAPbuilds/platform-atlas-report-analyzer/scripts/analyze_report.py`

Run:

```bash
python ~/Documents/IAPbuilds/platform-atlas-report-analyzer/scripts/analyze_report.py \
  /tmp/atlas-<ticket-key>.zip \
  --ticket <ticket-key> \
  --output /tmp/er-triage-<ticket-key>.md
```

If `python` lacks pandas/pyarrow, substitute the atlas-venv interpreter:
```bash
~/Documents/IAPbuilds/platform-atlas/atlas-venv/bin/python \
  ~/Documents/IAPbuilds/platform-atlas-report-analyzer/scripts/analyze_report.py \
  ...
```

Read the output file: `/tmp/er-triage-<ticket-key>.md`

---

## Step 4 — Present the draft

First give the user a brief summary panel (two to four lines):
- Organization + environment name
- Overall health rating and pass rate (e.g. "Poor — 61%")
- Count per bucket: `⛔ 4 Mandatory | ⚠️ 19 Recommended | ℹ️ 7 Optional`

Then render the full draft markdown for the user to review. Tell them they can
ask you to edit any section before posting.

---

## Step 5 — Offer to post back to Jira

Ask once, clearly:

> "Would you like me to post this to [ticket-key]?
> - **Internal comment** — visible only to the Itential team (not the customer)
> - **External comment** — customer-visible via the Jira service portal
> - **Neither** — keep the draft here for you to copy manually"

**Internal comment** — use `addCommentToJiraIssue` with:
```json
{
  "visibility": { "type": "role", "value": "Service Desk Team" }
}
```

**External comment** — use `addCommentToJiraIssue` without a `visibility` field.

After posting, confirm with the Jira comment URL.

---

## Jira MCP constants

| Field | Value |
|-------|-------|
| cloudId | `2ece816a-62e4-4222-8518-b5507d198470` |
| Base URL | `https://itential.atlassian.net` |

---

## Severity → customer tier mapping

| Atlas `severity` field | Customer label | Meaning |
|------------------------|----------------|---------|
| `critical` | ⛔ Mandatory — Must Fix | Direct production risk; block go-live |
| `warning` | ⚠️ Recommended — Should Fix | Best-practice gap; next maintenance window |
| `info` | ℹ️ Optional — Best Practice | Non-blocking improvement |

---

## What a great draft looks like

- **Plain language** — the customer should understand without knowing Atlas rule IDs
- **Actionable** — every mandatory item states what is wrong and why it matters
- **Honest** — if the pass rate is 61%, say "Fair" or "Poor", not "mostly compliant"
- **Concise** — the Recommended and Optional tables are summaries, not essays
- **Next steps** — ends with 3–5 concrete actions, in priority order
- **Tone** — professional and constructive, never alarming or apologetic
