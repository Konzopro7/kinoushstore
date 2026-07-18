# Kinoush Store

E-commerce Django project deployed on **Hostinger**.

## Local setup

1. Create a virtual environment and activate it.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in the required values.
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Collect static assets locally if needed:
   ```bash
   python manage.py collectstatic --noinput
   ```
6. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Production Deployment (Hostinger)

See **[HOSTINGER_DEPLOYMENT.md](./HOSTINGER_DEPLOYMENT.md)** for complete setup instructions.

### Quick Deploy

```bash
bash deploy.sh
```

## Configuration

### Local Development
- Copy `.env.example` to `.env`
- Set `DJANGO_DEBUG=true`
- All variables optional for local development

### Production (Hostinger)
- Create `.env` file on server with production values
- Ensure `DJANGO_DEBUG=false`
- All required variables must be set (see below)

## Required Environment Variables

**Production-critical:**
- `DJANGO_SECRET_KEY` - Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DJANGO_DEBUG` - Set to `false` in production
- `DJANGO_ALLOWED_HOSTS` - Your domain(s)
- `DJANGO_CSRF_TRUSTED_ORIGINS` - Your domain(s)
- `DATABASE_URL` - Database connection string
- `SITE_URL` - Your domain with HTTPS

**Email:**
- `EMAIL_BACKEND` - SMTP or console
- `EMAIL_HOST` - SMTP server
- `EMAIL_PORT` - SMTP port (usually 587)
- `EMAIL_USE_TLS` - true/false
- `EMAIL_HOST_USER` - Email address
- `EMAIL_HOST_PASSWORD` - Password or app-specific password
- `DEFAULT_FROM_EMAIL` - Sender email
- `CONTACT_EMAIL` - Contact form recipient

**Payments:**
- `STRIPE_PUBLISHABLE_KEY` - From Stripe dashboard
- `STRIPE_SECRET_KEY` - From Stripe dashboard
- `STRIPE_WEBHOOK_SECRET` - Webhook signing secret

**Optional:**
- `CLOUDINARY_URL` or `CLOUDINARY_CLOUD_NAME` + `CLOUDINARY_API_KEY` + `CLOUDINARY_API_SECRET` - For media storage on stateless hosting. Hostinger VPS uses persistent local media storage when these variables are omitted.
- `INDEXNOW_KEY` - For search engine indexing

## Files

- `manage.py` - Django management script
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project metadata and dependencies
- `kinoushstore/` - Main project settings
- `shop/` - Django app
- `HOSTINGER_DEPLOYMENT.md` - Hostinger setup guide
- `HOSTINGER_ENV.md` - Environment variables reference
- `RENDER_TO_HOSTINGER.md` - Migration notes from Render
- `.env.example` - Environment file template

## Technologies

- Django 5.2.8
- Python 3.12+
- PostgreSQL/MySQL (recommended) or SQLite (dev)
- Stripe for payments
- Cloudinary for media storage
- WhiteNoise for static files

## Support

For Hostinger-specific issues, see **HOSTINGER_DEPLOYMENT.md**.
