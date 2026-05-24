# Hostinger Deployment Guide

## ✅ Prerequisites

- Hostinger hosting with SSH/terminal access
- Python 3.8+ available on server
- PostgreSQL or MySQL database (recommended)
- Domain pointed to Hostinger

## 📋 Installation Steps

### 1. Access Your Server via SSH

```bash
ssh user@your-domain.com
cd ~/public_html  # or your web root
```

### 2. Clone the Repository

```bash
git clone https://github.com/Konzopro7/kinoushstore.git
cd kinoushstore
```

### 3. Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create Environment File

Create a `.env` file with your production variables:

```bash
cat > .env << 'EOF'
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=your-very-secure-secret-key-here
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

SITE_URL=https://yourdomain.com
DATABASE_URL=postgresql://dbuser:dbpass@localhost/kinoushstore
# or for MySQL:
# DATABASE_URL=mysql://dbuser:dbpass@localhost/kinoushstore

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Kinoush Store <your-email@gmail.com>
CONTACT_EMAIL=support@yourdomain.com

STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

CLOUDINARY_URL=cloudinary://api-key:api-secret@cloud-name

SECURE_SSL_REDIRECT=true
INDEXNOW_KEY=your-indexnow-key
EOF
```

### 5. Set Up Database

If using PostgreSQL:
```bash
psql -U postgres
CREATE DATABASE kinoushstore;
CREATE USER dbuser WITH PASSWORD 'secure-password';
ALTER ROLE dbuser SET client_encoding TO 'utf8';
ALTER ROLE dbuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE dbuser SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE kinoushstore TO dbuser;
```

### 6. Run Migrations and Collect Static Files

```bash
python manage.py migrate
python manage.py collectstatic --noinput --clear
```

### 7. Configure Web Server (cPanel)

If using cPanel with Passenger:

1. Go to **cPanel > Setup Python App**
2. Create a new Python application
3. Select your domain
4. Python version: 3.8+
5. Application URL: `/`
6. Application startup file: `kinoushstore/wsgi.py`
7. Application entry point: `application`
8. Passenger log file: `tmp/passenger.log`

Then update `.htaccess` in public_html:

```apache
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteCond %{HTTP:Authorization} ^(.*)
  RewriteRule .* - [e=HTTP_AUTHORIZATION:%1]
</IfModule>
```

### 8. Alternative: Use Gunicorn + Nginx (Advanced)

If your host supports it:

```bash
# Install gunicorn
pip install gunicorn

# Create systemd service at /etc/systemd/system/kinoushstore.service
[Unit]
Description=Kinoush Store
After=network.target

[Service]
User=your-user
Group=www-data
WorkingDirectory=/home/your-user/public_html/kinoushstore
ExecStart=/home/your-user/public_html/kinoushstore/venv/bin/gunicorn \
  --workers=3 \
  --bind=127.0.0.1:8000 \
  kinoushstore.wsgi:application

[Install]
WantedBy=multi-user.target
```

Then configure Nginx as reverse proxy.

## 🚀 Automated Deployment with Git Webhook

1. Set up a Git webhook in your repository settings
2. Configure the webhook to trigger a script on your server
3. The script pulls latest code and runs migrations

Example webhook handler script:

```bash
#!/bin/bash
cd /home/user/public_html/kinoushstore
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
touch tmp/restart.txt  # For Passenger
```

## 🔒 Security Checklist

- [ ] `DJANGO_SECRET_KEY` is set and unique (use `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- [ ] `DJANGO_DEBUG=false` in production
- [ ] `ALLOWED_HOSTS` set correctly
- [ ] `CSRF_TRUSTED_ORIGINS` includes your domain
- [ ] HTTPS/SSL certificate installed
- [ ] `SECURE_SSL_REDIRECT=true`
- [ ] Database credentials secured
- [ ] Email credentials stored securely (use app-specific passwords, not account password)
- [ ] Stripe keys are from production account
- [ ] `.env` file is not in version control (check `.gitignore`)

## 📊 Database Backup

Regular backups via Hostinger:

1. **cPanel > Backups** - configure automated daily backups
2. **cPanel > phpMyAdmin** (if MySQL) - export database regularly

## 🆘 Troubleshooting

### Static files not loading
```bash
python manage.py collectstatic --noinput --clear
```

### Database connection errors
Check `DATABASE_URL` format and ensure database server is running.

### Permission issues
```bash
chmod -R 755 ~/public_html/kinoushstore
chmod -R 775 ~/public_html/kinoushstore/media
chmod -R 775 ~/public_html/kinoushstore/staticfiles
```

### View logs
```bash
tail -f tmp/passenger.log
# or
tail -f ~/public_html/kinoushstore/logs/django.log
```

## 📞 Support

For Hostinger-specific issues, contact Hostinger support.
For Django issues, check Django documentation: https://docs.djangoproject.com/
