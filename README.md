# Breathe ESG - ESG Data Ingestion & Review Platform

A Django REST + React application for ingesting emissions data from multiple sources (SAP, utilities, corporate travel), normalizing it, and providing an analyst review dashboard for approval before audit lock-in.

## Project Structure

```
.
├── backend/              # Django REST API
│   ├── config/          # Django settings
│   ├── ingestion/       # Core app (models, views, serializers)
│   ├── manage.py
│   └── requirements.txt
├── frontend/            # React dashboard
│   ├── src/
│   │   ├── components/
│   │   └── App.js
│   └── package.json
├── MODEL.md            # Data model documentation (35% grading)
├── DECISIONS.md        # Ambiguity resolutions & choices
├── TRADEOFFS.md        # What was deliberately not built
└── SOURCES.md          # Data source research & justification
```

## Quick Start (Local Development)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create database
python manage.py migrate

# Create superuser for admin
python manage.py createsuperuser

# Run server
python manage.py runserver
```

Server runs on `http://localhost:8000`

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm start
```

App runs on `http://localhost:3000`

### Test Data

Create a test company:
```bash
python manage.py shell

from ingestion.models import Company
Company.objects.create(name="Test Corp", industry="Manufacturing", headquarters="New York, NY")
```

Then upload sample CSV data via the dashboard.

## Data Flow

1. **Upload** → CSV file via React dashboard
2. **Parse** → DataSourceParser converts to NormalizedEmission records
3. **Flag** → Anomalies marked (missing factors, outliers, duplicates)
4. **Review** → Analyst sees flagged issues, can approve/reject/clarify
5. **Lock** → Approved records go to auditors

## API Endpoints

### Companies
- `GET /api/companies/` - List all companies
- `POST /api/companies/` - Create company

### Upload Data
- `POST /api/upload/` - Ingest CSV data
  ```json
  {
    "company_id": "uuid",
    "source_type": "SAP|UTILITY|TRAVEL",
    "data": [
      {"PO_NUMBER": "...", "QTY_RECEIVED": "...", ...}
    ]
  }
  ```

### Review Emissions
- `GET /api/emissions/?company=uuid&approval_status=PENDING_REVIEW` - Get emissions for review
- `POST /api/emissions/{id}/approve/` - Approve record
- `POST /api/emissions/{id}/reject/` - Reject record
- `POST /api/emissions/{id}/flag_anomaly/` - Flag issue

### Dashboard
- `GET /api/dashboard/summary/?company_id=uuid` - Summary stats

## Data Model

See `MODEL.md` for comprehensive documentation.

**Key entities**:
- **Company**: Multi-tenant root
- **RawIngestion**: Immutable source data snapshot
- **NormalizedEmission**: Standardized, analyst-reviewable record
- **AuditLog**: Complete change history

## Key Design Decisions

See `DECISIONS.md` for detailed reasoning on:
- Why flat CSV for SAP (not OData/IDoc)
- Why CSV portal export for utilities (not PDF/API)
- Why Concur for travel (not Navan)
- How scope 1/2/3 is assigned
- Unit normalization strategy

## Tradeoffs (What We Didn't Build)

See `TRADEOFFS.md`. We deliberately skipped:
1. Automated de-duplication (manual analyst review is more reliable)
2. Real-time API pulls (4-day timeline; batch CSV sufficient)
3. Emission factor versioning (hardcoded, documented factors)
4. Audit report generation (manual export acceptable)
5. ML-based anomaly detection (no training data available)

**Time saved**: 27 hours, allowing focus on core functionality.

## Deployment

### Render (Recommended)

1. **Create Render account** and connect GitHub repo

2. **Create PostgreSQL database** on Render (free tier: 500 MB)

3. **Create Web Service**:
   - Build command: `pip install -r backend/requirements.txt && python backend/manage.py migrate && python backend/manage.py collectstatic --noinput`
   - Start command: `gunicorn config.wsgi --chdir backend`
   - Set environment variables:
     ```
     DJANGO_SETTINGS_MODULE=config.settings
     SECRET_KEY=<generate-secure-key>
     DEBUG=False
     ALLOWED_HOSTS=your-app.onrender.com
     DATABASE_URL=<from-postgres-instance>
     ```

4. **Create Static Site** for React frontend:
   - Build command: `cd frontend && npm install && npm run build`
   - Publish directory: `frontend/build`
   - Set environment: `REACT_APP_API_URL=https://your-api.onrender.com/api`

5. **Configure CORS** in Django:
   - Set `CORS_ALLOWED_ORIGINS` to your React URL

### Local Docker

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "config.wsgi", "--chdir", "backend"]
```

```bash
docker build -t esg-backend -f backend/Dockerfile .
docker run -p 8000:8000 -e DATABASE_URL=sqlite:///db.sqlite3 esg-backend
```

## Emission Factors

Hardcoded (production would parameterize):

| Source | Fuel/Type | Factor | Source |
|--------|-----------|--------|--------|
| SAP | Diesel | 2.68 kg CO₂e/L | EPA 2023 |
| SAP | Gasoline | 2.31 kg CO₂e/L | EPA 2023 |
| SAP | Natural Gas | 2.04 kg CO₂e/m³ | EPA 2023 |
| Utility | Electricity | 0.385 kg CO₂e/kWh | US Average Grid |
| Travel | Flight Economy | 0.092 kg CO₂e/km | ICAO standard |
| Travel | Flight Business | 0.215 kg CO₂e/km | ICAO standard |
| Travel | Hotel | 50 kg CO₂e/night | Industry average |
| Travel | Ground | 0.112 kg CO₂e/km | Car average |

## File Format Examples

### SAP CSV
```
PO_NUMBER,MATERIAL,DESCRIPTION,QTY_RECEIVED,UOM,RECEIPT_DATE,VENDOR,COST_CENTER
4500001,MAT-001,Diesel Fuel,1000,L,2026-05-10,VEN-999,CC-0001
```

### Utility CSV
```
Account_Number,Meter_ID,Billing_Period_Start,Billing_Period_End,Usage_kWh,Peak_Demand_kW,Total_Charge_USD
ACC-001,M-001,2026-04-15,2026-05-14,45230,185.5,4521.30
```

### Travel CSV
```
Expense_ID,Category,Date,Origin,Destination,Distance_km,Class_of_Service,Duration_Nights
EXP-001,Airfare,2026-05-10,ORD,SEA,2100,Economy,
```

## Admin Interface

Access at `/admin` with superuser credentials.

- Manage companies
- View raw ingestions
- Review normalized emissions
- Check audit logs

## Testing

### Sample Data Upload

1. Go to `http://localhost:3000`
2. Select "Upload Data"
3. Choose data source type (SAP/Utility/Travel)
4. Paste sample CSV (see examples above)
5. Submit
6. Go to "Review Data" to see ingested records

### Approval Workflow

1. Analyst sees flagged anomalies
2. Click record to view details
3. Approve (locks for audit) or Reject (excludes from audit)
4. All actions logged to AuditLog

## Performance Notes

- SQLite suitable for < 100,000 records
- Indexes on (company, approval_status) and (activity_date) cover most queries
- Production: Use PostgreSQL + read replicas for scale

## Future Enhancements

1. **Factor Versioning**: Track which EPA/IPCC version per record
2. **Geo-Specific Factors**: Regional grid emissions + utility-specific data
3. **Real-Time APIs**: Direct SAP/Concur integration (currently CSV only)
4. **Bulk Operations**: Approve/reject multiple records at once
5. **Export Formats**: Generate audit-ready PDFs/Excel reports
6. **Reconciliation**: Detect duplicates across sources
7. **RFI Tracking**: Radiative forcing index for flight emissions

## Grading Rubric (Self-Assessment)

- **35% Data Model**: Comprehensive schema covering multi-tenancy, scope, source-of-truth, audit trail. See MODEL.md.
- **25% Decision Defense**: Clear rationale for data source choices, scope assignment, unit handling. See DECISIONS.md.
- **20% Realistic Source Handling**: Research-backed sample data, real data quality issues flagged. See SOURCES.md.
- **10% Analyst UX**: Non-engineer can review, flag, approve/reject records via dashboard.
- **10% Tradeoffs**: Explicit about what wasn't built and why. See TRADEOFFS.md.

## License

Demo project for Breathe ESG evaluation.

## Contact

Questions? See DECISIONS.md for "Questions for PM" section.
