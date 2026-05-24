# Render Deployment Configuration

## Prerequisites

- Render account (free tier available at render.com)
- GitHub repository connected
- PostgreSQL database from Render
- Node.js 18+ installed locally

## Step-by-Step Deployment

### 1. Create PostgreSQL Database on Render

- Go to Render dashboard → New → PostgreSQL
- Select free tier
- Note the connection string (looks like: `postgresql://user:pass@host:5432/db`)

### 2. Create Web Service for Django Backend

- Go to Render → New → Web Service
- Connect GitHub repository
- Settings:
  - **Name**: breathe-esg-api
  - **Root Directory**: `backend`
  - **Runtime**: Python 3.11
  - **Build Command**: 
    ```bash
    pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
    ```
  - **Start Command**: 
    ```bash
    gunicorn config.wsgi
    ```

- Environment Variables:
  ```
  DJANGO_SETTINGS_MODULE=config.settings
  SECRET_KEY=<generate-using-Django>
  DEBUG=False
  ALLOWED_HOSTS=breathe-esg-api.onrender.com,breathe-esg-frontend.onrender.com
  DATABASE_URL=<paste-PostgreSQL-connection-string>
  CORS_ALLOWED_ORIGINS=https://breathe-esg-frontend.onrender.com
  ```

- Deploy

### 3. Create Static Site for React Frontend

- Go to Render → New → Static Site
- Connect GitHub repository
- Settings:
  - **Name**: breathe-esg-frontend
  - **Root Directory**: `frontend`
  - **Build Command**: 
    ```bash
    npm install && npm run build
    ```
  - **Publish Directory**: `build`

- Environment Variables:
  ```
  REACT_APP_API_URL=https://breathe-esg-api.onrender.com/api
  ```

- Deploy

### 4. Test Deployment

- Frontend: https://breathe-esg-frontend.onrender.com
- API: https://breathe-esg-api.onrender.com/api/
- Admin: https://breathe-esg-api.onrender.com/admin/

### 5. Create Admin User (for database management)

- SSH into backend service (Render dashboard → Web Service → Shell)
- Run:
  ```bash
  python manage.py createsuperuser
  ```

### 6. Seed Test Company

- Via Django admin or shell:
  ```bash
  python manage.py shell
  from ingestion.models import Company
  Company.objects.create(
      name="Acme Manufacturing",
      industry="Manufacturing",
      headquarters="Chicago, IL"
  )
  ```

## Troubleshooting

### Build Fails: "No module named django"
- Ensure `requirements.txt` is in the correct directory (`backend/requirements.txt`)
- Check Python version is 3.11+

### CORS Errors in Frontend
- Update `CORS_ALLOWED_ORIGINS` in Django settings
- Ensure frontend URL matches exactly (https, no trailing slash)

### Database Connection Error
- Verify `DATABASE_URL` format: `postgresql://user:pass@host:port/dbname`
- Check PostgreSQL instance is running
- Run `python manage.py migrate` to initialize schema

### Static Files Not Serving
- Django admin CSS broken? Run `python manage.py collectstatic` locally to test
- Ensure `STATIC_ROOT` and `STATIC_URL` are configured

### React App Blank
- Check browser console for API errors
- Verify `REACT_APP_API_URL` is correct
- Ensure Django API is responding: `curl https://breathe-esg-api.onrender.com/api/companies/`

## Performance Tips

- Use PostgreSQL even on free tier (SQLite doesn't work with Render multi-instance)
- Cold starts: ~30 seconds normal for free tier
- For production: Upgrade to paid tier for better performance

## Monitoring

- Render dashboard shows logs, builds, deployments
- Django admin `/admin/` for data inspection
- API health check: `GET /api/companies/` should return `[]` or list of companies

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] `SECRET_KEY` is long, random, unique (use `django-insecure-...` placeholder replaced with real key)
- [ ] `ALLOWED_HOSTS` is explicit (not `*`)
- [ ] `CORS_ALLOWED_ORIGINS` is specific (not `*`)
- [ ] Database credentials in environment variables, not in code
- [ ] HTTPS enforced (Render does this by default)

## Rollback

If deployment breaks:
1. Go to Render dashboard → Deployments
2. Select previous working deployment
3. Click "Deploy"

## Cost

- Free tier: $0 (limited resources)
- Production: ~$20/month for small app + database
