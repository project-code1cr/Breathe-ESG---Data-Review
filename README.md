# Breathe ESG

A Django + React app for uploading emissions data, normalizing it, and reviewing it before approval.

## What it does

- Takes SAP, utility, and travel data
- Normalizes the records into one format
- Lets an analyst review, approve, reject, or flag them
- Keeps an audit trail of changes

## Project structure

- `backend/` - Django REST API
- `frontend/` - React app
- `MODEL.md` - data model notes
- `DECISIONS.md` - key design choices
- `SOURCES.md` - source research
- `TRADEOFFS.md` - what was skipped

## Run locally

Backend:
```bash
cd backend
python -m venv venv
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Frontend:
```bash
cd frontend
npm install
npm start
```

## Main features

- Upload SAP, utility, and travel data
- Review emissions in the dashboard
- Approve, reject, or flag records
- Track everything with an audit log

## API

- `GET /api/companies/`
- `POST /api/companies/`
- `POST /api/upload/`
- `GET /api/emissions/`
- `POST /api/emissions/{id}/approve/`
- `POST /api/emissions/{id}/reject/`
- `POST /api/emissions/{id}/flag_anomaly/`
- `GET /api/dashboard/summary/`

## Docs

- `MODEL.md` - data model
- `DECISIONS.md` - why the app works this way
- `SOURCES.md` - source notes
- `TRADEOFFS.md` - what was left out
- `DEPLOYMENT.md` - Render setup
- `QUICKSTART.md` - short local setup

## Deploy

Use Render for backend and frontend. Set the backend env vars, point the frontend to the API URL, and make sure CORS allows the frontend domain. If you are deploying from scratch, use the commands in `DEPLOYMENT.md`.
