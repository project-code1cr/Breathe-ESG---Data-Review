Decisions and notes for the ingestion and review system.

SAP data: we use flat CSV exports (SE16N) rather than APIs or IDocs. CSVs are accessible to procurement teams, quick to archive, and easy to replay. The trade-off is that the data isn’t real-time, but monthly exports are acceptable for ESG reporting.

Utilities: we parse CSV portal exports from utility accounts instead of OCRing PDFs or relying on vendor APIs. CSVs capture meter-level reads, billing periods, and tariff rows reliably.

Travel: Concur CSV/API is the primary source. We extract flights (distance + class), hotels (nights), and ground travel (distance). Some details like aircraft type or exact vehicle model aren’t captured and are treated as approximations.

Scope rules: assign scope at ingestion by source type—SAP fuel → Scope 1, SAP procurement → Scope 3, utility electricity → Scope 2, travel → Scope 3. We document edge cases for analyst review.

Ambiguities and flags: units and missing factors are common issues. We detect unit mismatches (e.g., barrels vs litres) and flag missing emission factors for procurement items. Analysts review and resolve these with manual overrides.

Emission factors: we use conservative, widely accepted defaults (example: EPA diesel factor) and record assumptions so analysts or auditors can change them later.

Implementation: backend in Django + DRF for rapid development and admin access; frontend in React for an interactive analyst experience. Dev uses SQLite for speed; production should run on Postgres.

Open questions for product decisions: do we track offsets/RECs, snapshot factor versions, handle intra-company transfers specially, count cancelled travel, split emissions across cost centers, or set a materiality threshold for ingestion?

If you want, I can shorten any section further or expand a specific area for the report.
