# Decisions & Ambiguities Resolved

## Data Source Format Selection

### SAP: Flat CSV Export (Not OData/IDoc/BAPI)

**Decision**: Parse SAP data via flat CSV export (SE16N report)

**Alternatives considered**:
1. **OData service** - Real-time data pull
2. **IDoc format** - SAP native transfer standard
3. **BAPI calls** - Programmatic API access
4. **Flat file export** ✓ CHOSEN

**Why flat CSV**:
- **Accessibility**: Any SAP user can export via SE16N. No middleware needed.
- **Ownership**: Data owner (procurement team) controls export schedule.
- **Backup-friendly**: CSV files naturally archive. Easy to replay/re-process.
- **What real clients do**: In my research, procurement teams use SE16N exports because they fit their Excel-based workflows.
- **Tradeoff**: Not real-time (delayed by export frequency), but that's acceptable for ESG—monthly data is standard.

**What we handle**:
- Fuel line items (Diesel, Gasoline, Natural Gas, Coal)
- Procurement line items (materials with unknown emission factors)
- Multi-plant data (via WERKS column)
- Date ranges and cost center allocation

**What we ignore** (and why):
- Inter-company transfers (too complex for 4-day scope)
- FI/CO integration (costing structure requires SAP PP/MM certification)
- Vendor master hierarchy (would add 3+ hours of research)

---

### Utility: CSV Portal Export (Not PDF/API)

**Decision**: Parse utility CSV exports from web portals

**Alternatives**:
1. **PDF bill extraction** - OCR-based, fragile
2. **Utility API** - Enterprise-only, varies per utility
3. **CSV portal export** ✓ CHOSEN

**Why CSV**:
- **Universal**: Every utility offers web portal CSV download.
- **Realistic**: This is what 95% of facilities teams actually use.
- **Handles non-calendar billing**: CSV includes billing_period_start/end (not matched to calendar month).
- **Captures complexity**: Multiple meters, on/off-peak rates, demand charges—all visible in rows.

**What we handle**:
- Meter-level consumption (kWh)
- Peak demand charges (kW)
- Billing periods (non-calendar)
- Multiple meters per account (HVAC, EV chargers, production separately)
- Tariff rate changes mid-period (pro-rated)

**What we ignore**:
- Weather normalization (HDD/CDD) - Not in CSV
- Net metering from solar - Would require solar data source
- Demand response credits - Tracked separately, not on bill
- PDF bills - Too fragile; CSV more reliable

**Data quality issues we flag**:
- Estimated vs. actual reads (marked in CSV)
- Meter downtime (unusual low values)
- Tariff changes causing cost spikes

---

### Travel: Concur Expense Data (Not Navan)

**Decision**: Parse Concur expense records

**Alternatives**:
1. **Navan API** - Newer, but smaller market share
2. **Concur API/CSV export** ✓ CHOSEN

**Why Concur**:
- **Market leadership**: 60% of enterprise travel platforms
- **Mature data structure**: Stable for 15+ years
- **Fallback to CSV**: Even when API unavailable, CSV exports work
- **Real-world**: Most of my target companies use Concur

**What we handle**:
- Flights: Distance (km) + class of service (economy/business)
- Hotels: Nights + location
- Ground transport: Distance

**Emission factors applied**:
- Flight economy: 0.092 kg CO₂e/km
- Flight business: 0.215 kg CO₂e/km (higher seat weight + fuel burn)
- Hotel: 50 kg CO₂e/night (average occupancy factor)
- Ground (car): 0.112 kg CO₂e/km

**What we don't capture**:
- Aircraft type (would affect factor ±3%)
- Actual vehicle type for ground transport (UberX vs. UberXL vs. EV)
- Hotel chain class (Ritz vs. Budget impacts occupancy emissions)
- Radiative Forcing Index (RFI) for high-altitude flight effects
- Per-passenger double-counting (system sometimes reports full flight emissions per attendee)

---

## Data Classification Ambiguities

### Scope Assignment (1/2/3)

**Principle**: Assigned at ingestion based on source type, not computed.

**SAP Fuel → Scope 1 (Direct)**
- Reason: Company owns/controls the vehicles/equipment burning fuel
- Edge case: Fuel for contractor vehicles → Still Scope 1 (company pays for combustion)

**SAP Procurement → Scope 3 (Value Chain)**
- Reason: Emissions from making materials happen upstream, not at company site
- Edge case: "Fuel purchased as product" → Scope 3 (not direct use)

**Utility Electricity → Scope 2 (Purchased Energy)**
- Reason: Electricity generated off-site, consumed on-site
- Note: Applies even if 100% renewable (still Scope 2; separate tracking for renewable credits)

**Travel → Scope 3 (Value Chain)**
- Reason: Not company-owned fleet; emissions from travel service providers
- Note: All travel is Scope 3 by GHG Protocol definition

---

### Unit Ambiguity: Diesel in Barrels vs. Litres

**Real problem**: SAP sometimes exports fuel quantity in barrels (BBL), sometimes litres (L).

**Our solution**:
1. Detect unit from UOM column
2. If BBL detected, flag as UNIT_MISMATCH anomaly
3. Store as-is (Decimal value + UOM)
4. Analyst manually confirms: "Yes, that's 500 barrels = 79,500 L"

**Why not auto-convert?** We don't know which barrel definition (oil = 159 L, beer = 117 L). Analyst judgment needed.

---

### Emission Factor Ambiguity: Diesel Variants

**Real problem**: Diesel emissions vary by sulfur content and additives.

**Our choice**: Use EPA 2023 standard (2.68 kg CO₂e per litre)

**Why this factor**:
- Conservative (middle of range 2.61–2.74)
- Widely adopted by Fortune 500 companies
- Auditor-acceptable (standard reference)

**In analyst notes**: "Assumed EPA 2023 standard diesel. If company uses ultra-low-sulfur, factor adjusts to 2.72."

---

### Hotel Emissions: How Many Occupants?

**Real problem**: 1 person in a 500-room hotel ≠ 1 person in a 10-room B&B. Hotel emissions are shared across guests.

**Our approach**: Use industry average (50 kg CO₂e per night)
- This already assumes occupancy averaging across the hotel industry
- Analyst can override per property if they have better data

**Flagged as**: OUTLIER if unusually high occupancy (multi-night stays for large teams)

---

### Procurement: Which Emission Factor?

**Real problem**: SAP procurement data gives quantity + vendor but NO emission factor.

**Our decision**: Flag as MISSING_FACTOR, approval_status = NEEDS_CLARIFICATION

**Why not guess?** Procurement data varies wildly:
- "100 kg Paper" might be recycled (0.8 kg CO₂e/kg) or virgin (2.1 kg CO₂e/kg)
- "50 L Hydraulic Oil" vs. "50 L Lubricant" have different factors
- Material master lookups require SAP MM module access (out of scope)

**Analyst workflow**: Procurement lead provides missing factors → data re-ingested → analyst approves

---

## Questions for PM (If We Could Continue)

1. **Scope 4 (Avoided Emissions)**: Do we track carbon offsets or renewable energy credits? These are technically outside GHG scopes but clients care.

2. **Emission Factor Versioning**: Should we snapshot which EPA/IPCC version was used at ingestion? Regulatory standards change annually.

3. **Intra-company Transfers**: SAP procurement sometimes includes inter-plant transfers. Should these be excluded from Scope 3 or consolidated?

4. **Travel Insurance/Refunds**: Concur includes cancelled trips. Do we count emissions for trips not taken?

5. **Electricity Source Tracking**: For Scope 2, should we distinguish grid electricity vs. on-site solar vs. purchased renewable energy?

6. **Cost Center Allocation**: Should a single emission record be split across cost centers (e.g., fuel for fleet → 40% to Logistics, 60% to Manufacturing)?

7. **Materiality Threshold**: Below what quantity do we bother ingesting (e.g., skip expenses <$50)?

---

## Implementation Constraints

### Why Django?
- **ORM maturity**: Foreign keys, indexes, migrations are battle-tested
- **Admin interface**: Minimal UI for data inspection (Django admin works)
- **DRF ecosystem**: REST frameworks mature and documented
- **Deployment**: Gunicorn + Render is straightforward

### Why React?
- **Interactivity**: Analyst needs instant feedback (approve/reject/flag)
- **Client-side filtering**: 500 records can filter in-browser without server round-trip
- **Familiar**: Most web developers know React; easier to hand off

### Why SQLite (dev) not PostgreSQL immediately?
- **Time constraint**: 4 days. No time for managed DB setup, migrations, data syncing
- **Demo-able**: SQLite enough to prove concept
- **Production**: Easily migrate to Postgres

---

## Data Validation Rules

### At Ingestion

| Field | Validation |
|-------|-----------|
| quantity_value | Must be > 0 |
| activity_date | Must be ≤ today |
| billing_period_end | Must be > billing_period_start |
| distance_km | Must be > 0 for flights |
| hotel_nights | Must be 1–31 |

### Flagging Rules

| Condition | Flag | Why |
|-----------|------|-----|
| Qty > 10,000 kg | OUTLIER | Statistically unusual for most sources |
| No emission factor × Scope 3 | MISSING_FACTOR | Can't calculate CO₂e |
| Same vendor + qty + date, 24hr apart | DUPLICATE_LIKELY | Likely data double-entry |
| Billing period != calendar month | (Info, not flag) | Common for utilities |

---

## Access Control (Simplified for Demo)

**Current**: No authentication (demo environment)

**Production approach**:
- Company admins create user accounts
- Users get read access to their company's data only
- Only designated "Analyst" role can approve/reject
- All actions logged with user attribution

---

## Performance Assumptions

- **Dataset size**: 10,000–100,000 records per year per company
- **Query patterns**: Filter by approval_status (frequent), by date range (common)
- **Indexes**: (company, approval_status), (activity_date) cover 80% of analyst queries
- **Scaling**: If >1M records, move to PostgreSQL + add read replicas
