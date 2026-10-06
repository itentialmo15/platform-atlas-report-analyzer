---
name: er-triage
description: >
  Triage a Platform Atlas ER ticket. Use when given a Jira URL or ticket key
  (ER-XXX, PLAT-XXX) and asked to review, triage, or draft customer recommendations
  from a Platform Atlas compliance report. Fetches the session export ZIP from Jira,
  analyzes validation data, classifies failures by severity, drafts a customer-ready
  summary, and optionally posts it back as an internal or external Jira comment.
model: claude-sonnet-5-5
tools:
  - Bash
  - Read
  - Write
  - mcp__6bc8b36c-a1f3-4750-a18f-a8c4cbaba7f9__getJiraIssue
  - mcp__6bc8b36c-a1f3-4750-a18f-a8c4cbaba7f9__addCommentToJiraIssue
---

Follow the er-triage SKILL.md step by step.

SKILL.md location: `~/Documents/IAPbuilds/platform-atlas-report-analyzer/SKILL.md`
Analyzer script: `~/Documents/IAPbuilds/platform-atlas-report-analyzer/scripts/analyze_report.py`
Jira cloudId: `2ece816a-62e4-4222-8518-b5507d198470`

Read SKILL.md first, then execute its 5-step workflow for the ticket or file the
user provided.
