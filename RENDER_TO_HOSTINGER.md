# Render → Hostinger Migration

## Overview

Kinoush Store a été configuré initialement pour Render mais est maintenant hébergé sur **Hostinger**.

### Key Changes

| Aspect | Render | Hostinger |
|--------|--------|-----------|
| **Config file** | `render.yaml` | `.env` + cPanel/SSH |
| **Web server** | Render (gunicorn) | Passenger/cPanel or Nginx |
| **Database** | Render PostgreSQL | Hostinger PostgreSQL/MySQL |
| **Static files** | Handled by Render | WhiteNoise + Hostinger web root |
| **Deployment** | Git push to Render | Git pull + `deploy.sh` on server |
| **Environment vars** | `render.yaml` | `.env` file or cPanel |

## Files No Longer Used

These files were for Render/Vercel and can be removed (or kept for reference):

- `render.yaml` - Render configuration
- `vercel.json` - Vercel configuration  
- `api/index.py` - Vercel serverless entry point

## New Hostinger-Specific Files

- `HOSTINGER_DEPLOYMENT.md` - Complete setup guide
- `HOSTINGER_ENV.md` - Environment variables guide
- `deploy.sh` - Automated deployment script
- `public_html/.htaccess` - Web server configuration
- `.env` - Your environment variables (local + production)

## Quick Hostinger Setup

```bash
# SSH into your server
ssh user@yourdomain.com

# Clone and setup
git clone https://github.com/Konzopro7/kinoushstore.git
cd kinoushstore
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file with your settings
# (see HOSTINGER_DEPLOYMENT.md for details)

# Run deployment
bash deploy.sh
```

## Database Configuration

**For Hostinger-provided PostgreSQL/MySQL:**
```
DATABASE_URL=postgresql://username:password@localhost/database_name
# or
DATABASE_URL=mysql://username:password@localhost/database_name
```

## Environment Variables Priority

1. **Production (.env file)** - Place `.env` in project root on server
2. **Local (.env file)** - For development
3. **Defaults in settings.py** - Fallback values

## What Works the Same

✅ Django code structure (no changes needed)
✅ Models, views, URLs
✅ Static files serving (WhiteNoise handles it)
✅ Database migrations
✅ Email configuration
✅ Stripe payment integration
✅ Cloudinary media storage

## What's Different

❌ No automatic CI/CD from git push (set up webhook if desired)
❌ Manual/cPanel application setup required
❌ Different database setup procedure
❌ Security headers configured via `.htaccess` instead of framework

## Next Steps

1. Review `HOSTINGER_DEPLOYMENT.md` for detailed instructions
2. Update environment variables in `.env`
3. Test locally with `python manage.py runserver`
4. Deploy using `bash deploy.sh` or via cPanel
5. Test production at https://yourdomain.com

## Support Resources

- **Hostinger docs:** https://support.hostinger.com
- **Django docs:** https://docs.djangoproject.com
- **Render config reference:** `render.yaml` (for historical reference)
