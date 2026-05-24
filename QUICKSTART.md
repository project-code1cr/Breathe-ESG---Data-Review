npm install
Quick start — local setup in minutes.

Prereqs: Python 3.11+, Node 18+, Git.

Backend (quick):
1. cd backend
2. python -m venv venv && activate it
3. pip install -r requirements.txt
4. python manage.py migrate
5. python manage.py createsuperuser (optional)
6. python manage.py runserver (app on http://localhost:8000)

Frontend (quick):
1. cd frontend
2. npm install
3. npm start (app on http://localhost:3000)

To test:
- Add a company in the admin or via API.
- Upload one of the sample CSVs (SAP, utility, travel) from the repo using the Upload Data screen.
- Visit Review Data to approve or flag records; check Dashboard for totals.

If something breaks: check backend logs, browser console, and that `REACT_APP_API_URL` points to your backend.

Want a step-by-step printed for your team? I can generate a short checklist file.
