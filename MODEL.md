Short model summary.

Core entities:
- `Company` (tenant root).
- `RawIngestion` (immutable JSON of each uploaded row; keeps the audit trail and parsing status).
- `NormalizedEmission` (one row per parsed emission with original unit, applied factor, computed kg CO₂e, scope, and analyst/approval fields).
- `AuditLog` (immutable history of actions: ingest, parse, approve, flag).

Key points:
- We keep original units and the conversion factor per record so auditors can verify calculations.
- Scope (1/2/3) is assigned at ingestion by source type (SAP fuel → Scope 1, utilities → Scope 2, travel/procurement → Scope 3).
- Flags (e.g., UNIT_MISMATCH, MISSING_FACTOR, OUTLIER) mark rows for analyst review instead of auto-rejecting them.

Why this design:
- Traceability and auditability are primary — everything links back to the raw JSON.
- Storing the factor on each record avoids ambiguity when factors are updated later.
- Approval workflow locks records for audit when approved.

Future improvements: factor versioning, geo-specific grid factors, bulk analyst tools, and reconciliation features.
