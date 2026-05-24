# Hostinger Environment Variables Setup

## Option 1: Using .env File (Recommended)

Place a `.env` file in your project root. Django will automatically load it.

**File: `.env`**
```
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=your-secret-key
DJANGO_ALLOWED_HOSTS=yourdomain.com
# ... other variables
```

Ensure `.env` is in `.gitignore` to prevent accidental commits.

## Option 2: cPanel Environment Variables

1. Log in to cPanel
2. Go to **Software > Setup Python App**
3. Click on your application
4. In the environment variables section, add:
   - Key: `DJANGO_DEBUG` | Value: `false`
   - Key: `DJANGO_SECRET_KEY` | Value: `your-secret-key`
   - etc.

## Option 3: Using a .envrc File (If direnv is installed)

Create `.envrc` and ensure direnv is configured on your server.

## Recommended: Use Option 1 + GitHub Secrets

1. Store `.env` template in `.env.example` (with placeholder values)
2. Create `.env` on production server manually
3. Use GitHub Actions or Hostinger webhooks for deployments
4. Never commit `.env` to version control

## Important Variables for Hostinger

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_DEBUG` | Disable in production | `false` |
| `DJANGO_SECRET_KEY` | Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` | (long random string) |
| `DJANGO_ALLOWED_HOSTS` | Your domains | `yourdomain.com,www.yourdomain.com` |
| `DATABASE_URL` | Hostinger database | `postgresql://user:pass@localhost/dbname` |
| `STRIPE_SECRET_KEY` | From Stripe dashboard | `sk_live_xxx` |

## Security Notes

- Never commit `.env` files
- Use strong `DJANGO_SECRET_KEY` (50+ characters)
- Rotate `STRIPE_SECRET_KEY` regularly
- Store email passwords as app-specific passwords, not account passwords
- Use HTTPS on production
