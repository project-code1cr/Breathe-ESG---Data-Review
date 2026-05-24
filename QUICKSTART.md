# Quick Start Guide

## 5-Minute Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Step 1: Backend Setup (2 minutes)

```bash
# Clone repo (or navigate to your working directory)
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python manage.py migrate

# Create superuser
python manage.py createsuperuser
# When prompted, enter:
#   Username: admin
#   Email: admin@breatheesg.com
#   Password: (choose secure password)

# Create test company
python manage.py shell
```

Inside the shell:
```python
from ingestion.models import Company
Company.objects.create(name="Acme Manufacturing", industry="Manufacturing", headquarters="Chicago, IL")
exit()
```

Start Django server:
```bash
python manage.py runserver
```

✅ Backend runs on http://localhost:8000

### Step 2: Frontend Setup (2 minutes)

In a new terminal:
```bash
cd frontend

npm install
npm start
```

✅ Frontend runs on http://localhost:3000

### Step 3: Test the App (1 minute)

1. Go to **http://localhost:3000**
2. Click "Upload Data"
3. Select "SAP Fuel & Procurement" from dropdown
4. Copy-paste content of `../sample_data_sap.csv`
5. Click "Upload Data"
6. Go to "Review Data" to see results
7. Click on a record to approve/reject

## What You'll See

### Dashboard Tab
- Total records ingested
- Total CO₂e (in tonnes)
- Breakdown by Scope 1/2/3
- Flagged anomalies

### Review Data Tab
- List of all ingested emissions
- Filter by approval status
- Click to view details
- Approve (✓) or Reject (✗) records
- Add analyst notes

### Upload Data Tab
- Select data source type
- Paste CSV data
- System parses and ingests
- Shows success/failure counts

## Sample Data Files

Pre-made CSV files in root directory:
- `sample_data_sap.csv` - Fuel & procurement
- `sample_data_utility.csv` - Electricity data
- `sample_data_travel.csv` - Business travel

Each has realistic data quality issues (missing factors, outliers, etc.) that trigger analyst flags.

## Admin Interface

Access at **http://localhost:8000/admin**

Use superuser credentials (admin/password). Here you can:
- View all records
- Check audit logs
- Manage companies
- Inspect raw ingestions

## Troubleshooting

**"ModuleNotFoundError: No module named 'django'"**
- Run `pip install -r requirements.txt` in backend directory
- Ensure virtual environment is activated

**"psycopg2 error" on Windows**
- Already handled; psycopg2-binary installed in requirements.txt

**React shows "Cannot GET /api"**
- Django server not running on localhost:8000
- Check `REACT_APP_API_URL` in frontend/.env

**Database locked error**
- SQLite locks when two processes write simultaneously
- Restart Django server (`Ctrl+C`, then `python manage.py runserver`)

## Next Steps

1. **Upload Real Data**: Replace sample CSVs with your actual SAP/utility/travel exports
2. **Test Approval Workflow**: Approve a record, check AuditLog in admin
3. **Deploy**: Follow DEPLOYMENT.md for Render setup
4. **Review Documentation**: Read MODEL.md, DECISIONS.md, SOURCES.md for implementation details

## Production Deployment

See DEPLOYMENT.md for Render one-click deployment.

Key steps:
1. Push to GitHub
2. Connect Render to repo
3. Use render.yaml for infrastructure setup
4. Deploy both backend + frontend
5. Share live URL in submission email

## Still Stuck?

- Check logs: `python manage.py runserver` shows Django errors
- React console: Browser DevTools → Console tab
- Admin panel: Visit `/admin` to inspect data directly
- EMAIL: Include error message + what you were trying when it failed
