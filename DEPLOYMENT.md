Deployment notes — short and practical.

What you need: a Render account and your GitHub repo. Create two services:
- a Web Service for the Django backend (root: `backend`) — build with `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`, start with `gunicorn config.wsgi`.
- a Static Site for the React frontend (root: `frontend`) — build with `npm install && npm run build`, publish the `build` folder.

Key env vars:
- Backend: `DJANGO_SETTINGS_MODULE=config.settings`, `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS`.
- Frontend: `REACT_APP_API_URL` set to your backend `/api` URL.

Quick checks after deploy:
- API: `GET /api/` returns the endpoints.
- Frontend: site loads and can call the API (no CORS errors).
- Admin: create a superuser (`python manage.py createsuperuser`) if you need to inspect data.

Common fixes:
- Build fails because pip step wasn't run — make sure build command installs requirements first.
- `pkg_resources` errors on Python 3.14 — add `setuptools` to `requirements.txt`.
- `DisallowedHost` or CORS errors — add the exact Render/Vercel domains to `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`.

For production, use Postgres (set `DATABASE_URL`). Free tier is fine for demos; paid plans improve cold starts and uptime.
