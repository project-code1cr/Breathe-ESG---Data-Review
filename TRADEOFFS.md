# Tradeoffs: What We Deliberately Did NOT Build

## 1. Automated Data Reconciliation (Detecting Cross-Source Duplicates)

**What we didn't build**: Detection when the same emission appears in multiple source systems.

**Example**: A company's fleet fuel purchase is recorded in:
- SAP procurement (25,000 L diesel from Vendor X)
- Travel expense system (125 trips with ground transport totaling 25,000 km)
- Utility system (peak load suggesting fleet charging)

**Why skip it**:
- **Complexity**: Would need fuzzy matching (vendor name variations), cost allocation logic, inter-system timestamps
- **Manual validation is reliable**: Analysts can cross-check during review. A small risk of double-counting is better than false negatives (incorrectly removing real data)
- **Time cost**: 6–8 hours of development for uncertain payoff
- **Better solution**: Require data owner to de-dupe before upload. SAP procurement and Concur travel are different systems; collision is rare if data owners follow hygiene.

**Tradeoff accepted**: Manual analyst review adds overhead but eliminates false positives.

---

## 2. Real-Time Updates / Streaming Ingestion

**What we didn't build**: Live data pull from SAP/Concur/Utility APIs.

**Why skip it**:
- **ESG data isn't urgent**: Carbon accounting is monthly or quarterly. Real-time data isn't valuable.
- **API complexity**: Each source has different auth (OAuth, SOAP, REST), rate limits, scoping rules
- **Offline resilience**: Batch import (CSV upload) works if network down. APIs don't.
- **4-day constraint**: Building reliable OAuth integrations = 2+ days

**What we do instead**: CSV uploads (5-minute process to ingest month's data)

**Tradeoff accepted**: No real-time visibility, but reliable and operator-friendly.

---

## 3. Emission Factor Configuration & Versioning

**What we didn't build**: Admin UI to manage emission factors per company, with version history.

**Current state**: Factors hardcoded in code
```python
FUEL['diesel'] = 2.68  # kg CO2e per litre
```

**Why skip it**:
- **Standardization is desired**: Auditors want consistency. Different factors per company = hard to audit.
- **Versioning complexity**: Track which records used which factor version. Old records shouldn't change retroactively. Adds migrations + complexity.
- **Time cost**: 4 hours to build factor admin UI + tests

**What we do instead**: Document factors in SOURCES.md, have analysts note which version applies.

**Tradeoff accepted**: Factors are fixed for this demo. Production would parameterize.

---

## 4. Bulk Export to Audit Format (PDF/Excel Reports)

**What we didn't build**: One-click "export approved emissions to audit report" functionality.

**Why skip it**:
- **Not core to MVP**: Analysts' job is review. Auditor formatting is polish.
- **Varies per auditor**: Some want PDF, others CSV, others direct database access. No single export format fits all.
- **Can be manual**: "Export to CSV" + open in Excel is acceptable for audit handoff.
- **Time cost**: 3 hours to build configurable export

**What we do instead**: API returns JSON. Auditor can script their own export if needed.

**Tradeoff accepted**: Export is manual workaround, but good enough for demo.

---

## 5. Anomaly Detection / ML-Based Outlier Flagging

**What we didn't build**: Machine learning to detect anomalies (e.g., "50 tonnes fuel in one day is unusual").

**Why skip it**:
- **Requires training data**: Need baseline of what's "normal" per company/facility. Not available in 4 days.
- **False positives problem**: ML flags 10% of data as "unusual," analyst spends 3 hours reviewing noise.
- **Simpler solution works**: Statistical outliers (quantity > 3σ from mean) need just a histogram—doable in future.
- **Time cost**: 6+ hours for ML pipeline that would likely underperform

**What we do instead**: Analysts manually inspect flagged_anomaly field (which is pre-populated based on heuristics like missing factors).

**Tradeoff accepted**: No statistical anomaly detection, but explicit flags for known data issues.

---

## Summary Table

| Feature | Reason Skipped | Workaround | Time Saved |
|---------|----------------|-----------|-----------|
| Auto de-duplication | Complex fuzzy matching | Manual analyst review | 6 hrs |
| Real-time APIs | Auth + rate limits | Batch CSV upload | 8 hrs |
| Factor versioning | Audit complexity | Hardcode + document | 4 hrs |
| Audit export format | Auditor-specific | Manual CSV export | 3 hrs |
| ML anomaly detection | Needs training data | Manual flagging heuristics | 6 hrs |
| **Total time saved** | | | **27 hrs** |

---

## What This Means for Deployment

These five features are **not blockers** for the demo but should be considered for production:

1. **Months 2-3**: Build factor management UI (auditors will need it)
2. **Months 2-3**: Add API integrations (so you're not stuck on manual CSV)
3. **Months 3-4**: Implement statistical anomaly detection (reduce analyst manual work)
4. **Months 4+**: Consider automated reconciliation (only after 6 months of data to train on)

For now: **Demo ships with what an analyst genuinely needs to approve data.**
