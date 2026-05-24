# ESG Data Ingestion System - Data Model

## Overview

This document describes the data model for the Breathe ESG emissions ingestion platform. The model is designed to ingest heterogeneous data from three sources (SAP, utility, travel), normalize it, and surface it for analyst review before audit lock-in.

**Core principle**: Every normalized emission traces back to raw source data. No state is created without an audit trail.

## Domain Model

### 1. Company (Multi-Tenancy Root)

```
Company
├── id (UUID, PK)
├── name (unique)
├── industry
├── headquarters (for utility emission baselines)
└── created_at
```

**Why**: Breathe ESG is a multi-tenant platform. Each client's data must be strictly isolated. Company is the root of all data ownership and access control.

### 2. RawIngestion (Immutable Source Record)

```
RawIngestion
├── id (UUID, PK)
├── company_id (FK, PROTECT on delete)
├── source_type (SAP | UTILITY | TRAVEL)
├── raw_data (JSONField - original row as-is)
├── uploaded_at
├── uploaded_by (User FK, nullable)
├── status (PENDING | PARSED | FAILED | APPROVED | REJECTED)
├── parse_error (TextField if FAILED)
└── indexes: (company, source_type, status), (uploaded_at)
```

**Design decisions**:

- **raw_data as JSON**: We store the exact input as received, before any parsing. This is critical for debugging. If a data quality issue emerges 6 months later, we can re-parse the original.
- **Immutable**: Once created, never modified. This prevents loss of audit trail.
- **Parse error field**: If parsing fails (e.g., malformed date), we capture the error message so analysts know what went wrong.
- **Status tracking**: `PENDING` means raw data received but not yet parsed. `PARSED` = successfully converted to NormalizedEmission. `FAILED` = parse error. `APPROVED` = analyst approved the derived emissions and they're locked for audit.

**Why this structure**:
- ESG data auditors require proof of source. This table IS that proof.
- Regulatory compliance: We show exactly what came in.
- Traceability: Every NormalizedEmission has a foreign key back to RawIngestion.

### 3. NormalizedEmission (Analyst Review Surface)

```
NormalizedEmission
├── id (UUID, PK)
├── company_id (FK, PROTECT)
│
├── # Source lineage
├── data_source_ingestion_id (FK to RawIngestion, PROTECT)
├── source_type (SAP | UTILITY | TRAVEL)
│
├── # Classification (GHG Protocol)
├── scope (SCOPE_1 | SCOPE_2 | SCOPE_3)
├── category (FUEL_DIESEL | FUEL_GASOLINE | ELECTRICITY | TRAVEL_FLIGHTS | ...)
│
├── # Normalized quantities (always SI at rest)
├── quantity_value (Decimal)
├── quantity_unit (KG | LITRE | M3 | KWH | KM | MILES | NIGHT)
├── quantity_kg_co2e (Decimal - computed field)
├── unit_conversion_factor (Decimal - what was applied)
│
├── # Temporal
├── activity_date (when the activity occurred)
├── billing_period_start (for utilities)
├── billing_period_end (for utilities)
│
├── # Metadata
├── facility (e.g., "Plant A")
├── vendor_supplier
├── cost_center
├── origin (e.g., "ORD" airport code)
├── destination (e.g., "SEA")
├── distance_km (for travel)
│
├── # Analyst review
├── flagged_anomaly (NONE | UNIT_MISMATCH | MISSING_FACTOR | OUTLIER | ...)
├── analyst_notes (TextField)
│
├── # Approval workflow
├── approval_status (PENDING_REVIEW | APPROVED | REJECTED | NEEDS_CLARIFICATION)
├── approved_by (User FK, nullable)
├── approved_at (DateTimeField, nullable)
│
├── created_at
├── updated_at
└── indexes: (company, approval_status), (activity_date), (scope)
```

**Key design points**:

#### Unit Normalization (Not Lossy)

We store THREE fields to preserve full information:
- `quantity_value`: Original number
- `quantity_unit`: Original unit (L, KG, M3, etc.)
- `unit_conversion_factor`: Applied conversion factor
- `quantity_kg_co2e`: Result (quantity_value × factor)

**Example**: 50 L diesel
- quantity_value = 50
- quantity_unit = "LITRE"
- unit_conversion_factor = 2.68 (kg CO2e per litre)
- quantity_kg_co2e = 134

This design allows:
- Auditors to verify the math (50 × 2.68 = 134)
- Re-calculation with new factors if needed
- Clear labeling of units (no ambiguity)

#### Scope 1/2/3 at Data Level

Scope is determined at ingestion time, not computed downstream. Example:
- SAP fuel → Scope 1 (direct)
- Utility electricity → Scope 2 (purchased)
- Travel flights → Scope 3 (value chain)

**Why not compute scope in BI layer?** Because source type often IS scope. Baking it in at ingestion forces clarity: "Which source produced this?" = "What scope is it?"

#### Analyst Flags (Not Auto-Rejection)

The `flagged_anomaly` field surfaces data quality issues WITHOUT rejecting the row:
- UNIT_MISMATCH: "SAP says 50 barrels but barrel ≠ standard unit"
- MISSING_FACTOR: "Procurement data—no emission factor available"
- OUTLIER: "50 tonnes fuel in one day? Unusual."
- DUPLICATE_LIKELY: "Same vendor, same qty, same date as yesterday"

**Analyst workflow**: See the flag, understand the context (via analyst_notes), manually approve or reject.

**Why not auto-reject?** Emission data is messy. A "likely duplicate" might be legitimate (peak production day). An outlier might be real (factory repair required fuel surges). We don't want to silently drop records.

#### approval_status Workflow

```
PENDING_REVIEW
    ├─→ APPROVED (analyst approves, locks for audit)
    ├─→ REJECTED (analyst rejects, not included in audit)
    └─→ NEEDS_CLARIFICATION (needs more info from data source owner)
```

### 4. AuditLog (Immutable Change History)

```
AuditLog
├── id (UUID, PK)
├── company_id (FK, PROTECT)
├── action (INGESTED | PARSED | APPROVED | REJECTED | FLAGGED | UNFLAGGED | NOTES_ADDED)
├── related_emission_id (FK to NormalizedEmission, nullable)
├── related_ingestion_id (FK to RawIngestion, nullable)
├── user_id (FK to User, nullable - null for system actions)
├── timestamp (auto_now_add)
├── reason (why this action occurred)
├── details_json (full state before/after for debugging)
└── indexes: (company, timestamp), (action)
```

**Not just compliance**—it's the debugging log. When an analyst says "I approved this," AuditLog proves it. When a CO₂ number changes, AuditLog shows why.

## Entity Relationships

```
Company (1)
    ├── (1..N) RawIngestion
    │   └── (1..N) NormalizedEmission
    │       └── (1) AuditLog (via related_emission)
    └── (1..N) AuditLog
```

## Unit Normalization Strategy

### Source Units → Standardized Internal Units

**SAP Fuel**:
- L (diesel, petrol) → Litre
- KG (coal) → Kilogram
- M3 (natural gas at STP) → Cubic Meter
- BBL (barrels, sometimes for fuel) → Convert to Litres (1 BBL ≈ 159 L)

**Utility**:
- kWh → kWh (standard)
- MWh → kWh (× 1000)
- kW peak demand → kW (for demand charges)

**Travel**:
- km → km
- miles → convert to km (÷ 1.60934)
- hotel nights → Night unit

### Emission Factor Storage

Rather than compute CO₂ and discard the original, we store:

```python
# Example: 50 L diesel
emission.quantity_value = 50
emission.quantity_unit = "LITRE"
emission.unit_conversion_factor = 2.68  # kg CO2e per litre (EPA 2023)
emission.quantity_kg_co2e = 134.0  # Calculated

# Auditor review:
# ✓ 50 × 2.68 = 134
# ✓ Factor traceable to EPA 2023 standard
# ✓ Original unit preserved
```

## Scope 1/2/3 Assignment

| Source | Type | Scope | Why |
|--------|------|-------|-----|
| SAP | Diesel, natural gas, coal | Scope 1 | Direct emissions from company vehicles/facilities |
| SAP | Procurement | Scope 3 | Upstream supply chain |
| Utility | Electricity | Scope 2 | Purchased energy |
| Travel | Flights, hotels, ground | Scope 3 | Employee business travel (value chain) |

## Key Design Tradeoffs

### 1. SQLite (Development) vs. PostgreSQL (Production)

**Current**: SQLite for simplicity
**Production**: PostgreSQL with UUID fields for scale
**Why**: ESG data can scale quickly (1M+ records per year for large clients). UUID avoids ID collisions across distributed systems. JSON fields need PostgreSQL native support.

### 2. Unit Conversion Factor Storage

**Decision**: Store conversion factor per record
**Alternative considered**: Centralized lookup table with version history
**Why we chose per-record**: Auditability. Each row shows exactly what factor was used. No ambiguity.

### 3. No Pre-Computed Totals

**Decision**: Compute CO₂e at query time using SUM(quantity_kg_co2e)
**Alternative**: Materialized totals by scope/category
**Why chosen approach**: Avoids stale data. If an emission is re-evaluated, totals auto-update.

## Future Enhancements

1. **Emission Factor Versioning**: Track which EPA/IPCC factor version applied (for regulatory updates)
2. **GEO Specificity**: Store latitude/longitude for location-based utilities (grid carbon intensity varies by region)
3. **Radiative Forcing Index (RFI)**: For flights, track RFI multiplier for high-altitude contrails
4. **Batch Operations**: Bulk approve/reject with audit trail
5. **Data Reconciliation**: Flag when same record ingested twice from different sources
