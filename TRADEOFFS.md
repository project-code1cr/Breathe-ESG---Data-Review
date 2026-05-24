Tradeoffs we accepted for the MVP.

1) No automatic cross-source reconciliation. Duplicate detection across SAP, travel and utility is tricky and prone to false positives. Analysts review flagged rows instead.

2) No real-time API ingestion. CSV uploads are simple, resilient, and match the cadence for ESG reporting.

3) Emission factors are not managed in an admin UI yet — factors are documented in `SOURCES.md`. This keeps the demo simple and auditable; production should add a factor-management screen.

4) No one-click audit-export feature. The API returns JSON so auditors or engineers can make custom reports.

5) No ML-based anomaly detection. We use simple heuristics and human review; ML can be added later once there is enough data.

These choices saved development time and kept the product focused on analyst workflows. We can add any of the skipped features later when there’s demand.
