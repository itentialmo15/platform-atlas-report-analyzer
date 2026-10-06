# Platform Atlas Severity Guide — Customer Language Reference

Use this guide when writing or reviewing the customer-facing draft. Every Atlas
rule has a `severity` field. Here's how to translate it for a non-technical
stakeholder.

---

## ⛔ Mandatory — Must Fix (`severity: critical`)

**What it means technically:** The validation engine flagged a configuration that
directly violates a security control, high-availability requirement, or platform
correctness invariant. Platform support can not be guaranteed on a deployment with
these issues open.

**How to explain it to a customer:**

> "This item is blocking a production-ready state. Left unresolved, it creates
> direct risk of platform outage, security exposure, or data inconsistency."

**Common critical categories:**
- MongoDB not running with authentication (`MDB-*`)
- Redis persistence not configured (`RDS-*`)
- IAP webserver running HTTP instead of HTTPS (`PLAT-*`)
- Replica set in a degraded state
- Missing or expired TLS certificates on gateways

**Tone:** Direct but not alarmist. State the risk clearly; offer a path forward.

---

## ⚠️ Recommended — Should Fix (`severity: warning`)

**What it means technically:** The configuration departs from Itential's
production best practices. The platform will run, but long-term reliability,
maintainability, or supportability is reduced.

**How to explain it to a customer:**

> "This item is not blocking production today, but it increases operational risk
> over time. We recommend addressing it at the next scheduled maintenance window."

**Common warning categories:**
- Log levels set too verbose for production (DEBUG instead of INFO)
- Timeout or retry values outside recommended ranges
- Gateway API token expiry set too long
- Redundant services or adapters not disabled

**Tone:** Matter-of-fact. Quantify the risk where possible ("a DEBUG log level
increases storage consumption 3–5× and slows query performance").

---

## ℹ️ Optional — Best Practice (`severity: info`)

**What it means technically:** The platform is configured acceptably, but an
improvement is available that would enhance observability, performance, or
long-term manageability.

**How to explain it to a customer:**

> "These are non-blocking improvements. They're worth scheduling at your
> convenience rather than treating as urgent."

**Common info categories:**
- Metrics endpoints not exposed for monitoring
- Default description fields left blank
- Minor version behind the latest patch release

**Tone:** Light and constructive. Frame as "nice to have" rather than "you need
to fix this." These items should not dominate the customer conversation.

---

## Health Ratings

| Pass Rate | Rating | Customer Framing |
|-----------|--------|-----------------|
| ≥ 90% | Excellent | "Your environment is in excellent shape." |
| 75–89% | Good | "Your environment is in good shape with a few areas to tighten up." |
| 60–74% | Fair | "Your environment is functional but has several gaps to address." |
| 40–59% | Poor | "Your environment has significant configuration gaps that need attention." |
| < 40% | Critical | "Your environment requires immediate attention before production use." |

---

## Writing Tips

1. **Lead with outcomes, not rule numbers.** Customers don't know what `PLAT-020`
   means. Say "HTTPS is not enabled on the webserver (PLAT-020)."

2. **Be specific about risk.** "MongoDB authentication is disabled" is better
   than "MongoDB configuration issue detected."

3. **Avoid jargon stacking.** Terms like "replica set quorum degradation" need a
   one-sentence plain-English follow-up.

4. **Don't soften Mandatory items.** If it's critical, say it's critical.
   Customers rely on our honest assessment to prioritize remediation.

5. **Suggest the next concrete action.** Each mandatory item should end with
   what the customer should do: "Enable authentication in `mongod.conf` under
   `security.authorization: enabled` and restart MongoDB."
