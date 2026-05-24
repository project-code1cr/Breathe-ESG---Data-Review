# Data Source Research & Justification

## 1. SAP Fuel & Procurement Data

### Real-World Format Researched

**Format chosen**: Flat CSV export via SE16N (SAP Query Table View)

**Real export columns** (from SAP MM–Materials Management module):
```
MATNR (Material Number)
MAKTX (Material Description)
MEINS (Unit of Measure)
EBELN (Purchase Order Number)
WERKS (Plant/Facility Code)
MENGE (Quantity Ordered)
WEMNG (Goods Receipt Quantity)
BPRME (Purchase Unit)
PREIS (Price per Unit)
EKKOS (Cost Center)
LGORT (Storage Location)
BUDAT (Document Date - when recorded)
LIFNR (Vendor Number)
```

### Real-World Data Quality Issues

#### Issue 1: Unit Inconsistency
**Problem**: Same material across plants in different units
```
Row 1: Diesel, 500 L (Plant A)
Row 2: Diesel, 0.5 TONNE (Plant B)
Row 3: Diesel, 1.89 BBL (Plant C)
```
**Reality**: Company has legacy SAP configs—never standardized units across plants
**Our handling**: Store raw UOM. Flag UNIT_MISMATCH if not in standard list (L, KG, M3). Analyst confirms conversion.

#### Issue 2: Deleted Purchase Order Headers
**Problem**: SAP purges old PO headers after fiscal year close (finance policy). Line items remain but EBELN linkage is lost.
```
QTY_RECEIVED: 950
EBELN: NULL (deleted)
```
**Our handling**: Proceed without PO linkage. Cost center allocation is incomplete but not fatal.

#### Issue 3: Price Includes Hidden Fees
**Problem**: PREIS column includes freight + tax + discount—not item cost
```
Diesel, 1000 L, PREIS = 2.89 per unit (actually: $1.20/unit + $0.89 freight)
```
**Our handling**: We DON'T use price for emission factors. We use quantity only. Price is for cost allocation (out of scope).

### Sample Data (Real-ish)

```csv
MATNR,MAKTX,MEINS,EBELN,WERKS,MENGE,WEMNG,BUDAT,LIFNR,EKKOS
MAT-001,Diesel Fuel (Grade 2D),L,4500123,1000,1000,950,2026-05-15,VEN-999,CC-0001
MAT-002,Natural Gas (STP),M3,4500124,2000,500,490,2026-05-16,VEN-888,CC-0002
MAT-003,Electrical Connectors,KG,4500125,3000,100,100,2026-05-17,VEN-777,CC-0003
```

### What Would Break in Real Deployment

1. **Plant-specific Emission Factors**: Different geographies have different grids. US diesel ≠ German diesel. We use US EPA. Would need geo field.
2. **Vendor Master Emissions**: Some companies track "certified low-carbon fuel from Vendor X." We don't have vendor emission attributes.
3. **Cost Center Allocation Rules**: "This fuel should be 60% Manufacturing, 40% Fleet." Not in SAP export—lives in cost accounting rules. We can't split.
4. **Temporal Aggregation**: Do you want daily data or monthly? We ingest line-item data; aggregation is analyst's job.
5. **Regulatory Reporting**: Some jurisdictions require specific material classifications (e.g., EU ETS commodity codes). We'd need materialization.

---

## 2. Utility Electricity Data

### Real-World Format Researched

**Format chosen**: CSV portal export (e.g., from Duke Energy, Con Edison, PG&E, Enel web portals)

**Real CSV structure** (typical U.S. utility):
```
Account_Number, Meter_ID, Service_Address, 
Billing_Period_Start, Billing_Period_End, 
Usage_kWh, Peak_Demand_kW,
On_Peak_kWh, Off_Peak_kWh,
On_Peak_Rate_$/kWh, Off_Peak_Rate_$/kWh,
Total_Charge_USD
```

### Real Complication: Non-Calendar Billing

**Problem**: Meter reads on the 15th of every month
```
Row 1: Period 2026-04-15 to 2026-05-14 (30 days)
Row 2: Period 2026-05-15 to 2026-06-13 (30 days)
```
These periods DON'T align with calendar months.

**Our handling**:
```python
billing_period_start = 2026-04-15
billing_period_end = 2026-05-14
activity_date = 2026-05-14  # Use period end as reporting date
```

### Real Complication: Time-of-Use (TOU) Tariffs

**Problem**: Different rates for on-peak vs. off-peak hours
```
On_Peak_kWh: 8,523
Off_Peak_kWh: 2,105
On_Peak_Rate: $0.087 per kWh
Off_Peak_Rate: $0.065 per kWh
```

**Carbon impact**: Peak electricity is dirtier (coal plants spin up). Off-peak is cleaner (night wind generation).

**Our simplification**: Use average grid factor (0.385 kg CO₂e/kWh, US average). Real system would adjust by time-of-use.

### Real Complication: Estimated vs. Actual Reads

**Problem**: Meter malfunction → utility estimates that month
```
Status: ESTIMATED
Usage_kWh: 4,500 (±20% confidence interval)
```

**Our handling**: We flag but don't reject. Analyst sees "ESTIMATED" in notes and can decide.

### Sample Data (Real-ish)

```csv
Account_Number,Meter_ID,Service_Address,Billing_Period_Start,Billing_Period_End,Usage_kWh,Peak_Demand_kW,Total_Charge_USD,Status
123456789,M-001,1000 Main St,2026-04-15,2026-05-14,45230,185.5,4521.30,ACTUAL
123456789,M-002,1000 Main St,2026-04-15,2026-05-14,2105,42.1,287.50,ACTUAL
456789123,M-003,500 Industrial Ave,2026-04-15,2026-05-14,125000,450.0,11250.00,ESTIMATED
```

### What Would Break in Real Deployment

1. **Grid Emission Factors Change by Region**: New York uses 0.18 kg CO₂e/kWh (hydro). Texas uses 0.65 (coal). We use US average. Real system needs utility + region → factor lookup.
2. **Distributed Energy Resources (DER)**: Solar on roof → negative kWh on sunny days. We don't handle net metering credits.
3. **Demand Response Programs**: Utility pays customer for load shedding. Avoided emissions but not tracked in bill.
4. **Time-of-Use Carbon Tracking**: Peak-hour electricity is dirtier. Our simple factor ignores this.
5. **Building Occupancy**: Same kWh consumption is different emissions per square foot if occupancy varies. We have no occupancy data.

---

## 3. Corporate Travel (Flights, Hotels, Ground Transport)

### Real-World Format Researched

**Format chosen**: Concur expense export (industry standard since 2010)

**Real Concur data structure**:
```
Expense_ID, Employee_ID, Date,
Category (Airfare / Lodging / Ground Transport),
Vendor_Name, Merchant_City,
Origin_Airport_Code, Destination_Airport_Code,
Distance_km, Duration_Hours,
Class_of_Service (Economy/Business/First),
Duration_Nights (for hotels),
Amount_USD, Currency
```

### Real Complication: Missing Distance Data

**Problem**: Concur often has airport codes but NO calculated distance
```
Origin: ORD (Chicago)
Destination: SEA (Seattle)
Distance_km: NULL
```

**What's real-world distance**: ~2,100 km

**Our handling**:
- Store airport codes (origin, destination)
- Flag MISSING_FACTOR if distance absent
- Analyst can look up distance or use known routes
- Re-ingest with distance populated

### Real Complication: Seat Class Ambiguity

**Problem**: Booking shows 'Y' (economy) but expense shows 'J' (business)
```
Booked as: Economy ($485)
Actual travel: Business Upgrade ($1,200)
```

**Reality**: Employee paid difference out-of-pocket; system only reports purchased fare.

**Our handling**: Use reported class. Analyst notes this discrepancy if material.

### Real Complication: Hotel Chain Emissions Vary Wildly

**Problem**: "Marriott" spans from Motel 6 (basic, low emissions per room) to Ritz-Carlton (luxury, high occupancy emissions)

**Our hardcoding**: 50 kg CO₂e per night (industry average)

**Reality**: Ritz might be 120, Motel 6 might be 20.

**Our handling**: Use average. Analyst can flag as OUTLIER if concerned.

### Sample Data (Real-ish)

```csv
Expense_ID,Category,Date,Origin,Destination,Distance_km,Class_of_Service,Duration_Nights,Vendor_Name,Amount_USD
EXP-001,Airfare,2026-05-10,ORD,SEA,2100,Economy,,,485.00
EXP-001,Lodging,2026-05-10,SEA,,0,Standard,2,Marriott Seattle,280.00
EXP-001,Ground Transport,2026-05-11,SEA,,12,UberX,,Uber,42.50
EXP-002,Airfare,2026-05-15,JFK,MIA,1281,Business,,,1485.00
EXP-002,Lodging,2026-05-15,MIA,,0,Deluxe,3,Biltmore Miami,950.00
```

### What Would Break in Real Deployment

1. **Aircraft Type Not Recorded**: ORD→SEA could be B787 (0.085 kg CO₂e/km) or A319 (0.142). We assume average. Impacts calculation by ±20%.
2. **Radiative Forcing Index (RFI)**: High-altitude contrails add 2–3x multiplier to actual emissions. Most expense systems don't track RFI.
3. **Per-Passenger Confusion**: Some systems record total flight emissions (all passengers). Others per-passenger. We don't detect this.
4. **Ground Transport Vehicle Type**: Uber shows UberX but not vehicle make/model (could be Prius vs. Hummer). We assume car average.
5. **Interline Bookings**: United→Alaska→Southwest are separate records. Distances don't sum naturally. Need logic to link them.
6. **Hotel Occupancy Variation**: Small B&B (10 rooms, 1 guest) has very different per-guest emissions than 500-room Marriott. We average.

---

## Emission Factors Applied

### SAP Fuel
| Fuel Type | Factor | Source | Notes |
|-----------|--------|--------|-------|
| Diesel (2D) | 2.68 kg CO₂e/L | EPA 2023 | Standard industrial diesel |
| Gasoline (87 octane) | 2.31 kg CO₂e/L | EPA 2023 | Regular unleaded |
| Natural Gas (STP) | 2.04 kg CO₂e/m³ | EPA 2023 | At standard temperature/pressure |
| Coal (bituminous) | 2.41 kg CO₂e/kg | IPCC 2006 | Varies by coal type; average |

### Utility Electricity
| Grid Region | Factor | Notes |
|------------|--------|-------|
| US Average | 0.385 kg CO₂e/kWh | Used in demo (no regional data) |
| Production mix | Varies 0.15–0.85 | Regional coal vs. hydro |

### Travel
| Transport | Factor | Notes |
|-----------|--------|-------|
| Flight (Economy, per km) | 0.092 kg CO₂e/km | Includes RFI multiplier ~2.7x |
| Flight (Business, per km) | 0.215 kg CO₂e/km | Higher seat weight + fuel burn |
| Hotel (per night) | 50 kg CO₂e/night | Industry average across occupancy |
| Ground Transport (per km) | 0.112 kg CO₂e/km | Car average (gasoline); electricity not differentiated |

---

## Why These Factors?

1. **EPA 2023**: U.S. regulatory standard. Auditor-familiar.
2. **Conservative**: Middle of plausible range. Protects client (avoids underreporting).
3. **Consistent**: Same source across all fuel types (EPA) means no factor conflicts.
4. **Versioned**: Easy to document "EPA 2023" so auditor knows baseline.

---

## What We Learned (for PM debrief)

1. **Data is Messy**: No source is clean. SAP has NULL fields, utilities have estimated reads, travel has missing distances.
2. **Standardization Tension**: Client wants one emission factor per fuel. Reality: factors vary by source, region, time period.
3. **Scope Boundaries Unclear**: Is contractor fuel Scope 1 or 3? Is purchased electricity Scope 2 (yes, by GHG Protocol) or Scope 1 (if company owns solar)?
4. **Audit Expectations**: Auditors want to see the original data ("Prove where that 50 L comes from"). We do, via RawIngestion table.
5. **Analyst Judgment Essential**: Flags (OUTLIER, MISSING_FACTOR) reduce false positives but require human review.

---

## Deployment Checklist

- [ ] SAP: Coordinate with procurement team on export schedule (monthly?)
- [ ] Utility: Get list of all accounts + meter IDs for target facilities
- [ ] Travel: Obtain Concur export credentials or CSV template from travel admin
- [ ] Factors: Align with client's preferred EPA/IPCC version
- [ ] Baselines: Establish "normal" ranges per facility for outlier detection
- [ ] Training: Show analyst how to use dashboard (approve/flag/review)
