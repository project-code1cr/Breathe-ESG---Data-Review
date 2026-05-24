Short source notes.

SAP: we ingest flat CSV exports from SAP (SE16N). Key point — keep the original unit and flag anything unusual (barrels vs litres, missing PO link). We use quantity fields only for emissions (not price).

Utilities: we parse CSV downloads from utility portals. CSVs give meter-level kWh and billing periods. We assume a default grid factor in the demo but recommend region-specific factors for production.

Travel: Concur exports are our primary source. We extract flights, hotels, and ground transport. Distances or seat class may be missing; those rows are flagged for analyst review.

Emission factors are documented and conservative (EPA 2023 for fuels; a demo grid factor for electricity; simple per-km rates for travel). Analysts can override or supply better factors if available.

In short: keep raw inputs, flag missing or mismatched fields, and let analysts confirm conversions or factors.
