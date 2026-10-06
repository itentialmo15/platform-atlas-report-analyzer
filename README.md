# platform-atlas-report-analyzer

A Claude skill + standalone analyzer script for triaging Platform Atlas ER tickets.

## What it does

When an SE drops a Jira URL like `https://itential.atlassian.net/browse/ER-508`
into their Claude session, this skill:

1. Fetches the Jira ticket and finds the Atlas session export ZIP attachment
2. Runs `scripts/analyze_report.py` against the ZIP
3. Produces a customer-ready markdown summary with failures grouped into three tiers:
   - ⛔ **Mandatory — Must Fix** (critical severity rules)
   - ⚠️ **Recommended — Should Fix** (warning severity rules)
   - ℹ️ **Optional — Best Practice** (info severity rules)
4. Optionally posts the draft as an internal or external Jira comment

## Repository structure

```
platform-atlas-report-analyzer/
├── SKILL.md                      # Claude skill definition (frontmatter + 5-step workflow)
├── .claude/
│   └── agents/
│       └── er-triage.md          # Claude Code agent definition
├── scripts/
│   └── analyze_report.py         # Core analyzer — ZIP/dir → markdown draft
└── references/
    └── severity_guide.md         # Customer-language guide for each severity tier
```

## Using the skill

### Via Claude session (recommended)

Just paste a Jira ER ticket URL. The skill triggers automatically:

```
https://itential.atlassian.net/browse/ER-508?focusedCommentId=550994
```

Claude fetches the ticket, downloads the ZIP, analyzes the report, and presents
the draft. You can then ask it to post as an internal or external Jira comment.

### Via CLI (standalone)

```bash
# Requires pandas + pyarrow
python scripts/analyze_report.py /path/to/export.zip --ticket ER-508

# Or using the platform-atlas atlas-venv
~/Documents/IAPbuilds/platform-atlas/atlas-venv/bin/python \
  scripts/analyze_report.py /path/to/export.zip --ticket ER-508 \
  --output /tmp/er-triage-ER-508.md
```

## Dependencies

| Dependency | Purpose |
|------------|---------|
| `pandas` + `pyarrow` | Read `02_validation.parquet` from session export |
| Jira MCP (Claude session) | Fetch ticket, post comment |

`pandas`/`pyarrow` are already available in the platform-atlas `atlas-venv`. No
additional installation is needed if you point the script at that interpreter.

## Jira comment types

- **Internal** — posted with `visibility: {type: "role", value: "Service Desk Team"}`.
  Only the Itential team sees it; the customer cannot via the Jira portal.
- **External** — posted without visibility restrictions. Customer-visible via the
  Jira service portal.

## Related

- [platform-atlas](../platform-atlas/) — the CLI tool that generates session exports
- [references/severity_guide.md](references/severity_guide.md) — writing guide for
  customer-facing severity explanations
