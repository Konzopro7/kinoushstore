#!/bin/bash

# Hostinger Django Deployment Script
# Usage: ./deploy.sh [environment]
# Environments: staging, production

set -e

ENVIRONMENT=${1:-production}
PROJECT_ROOT=$(pwd)
VENV_DIR="$PROJECT_ROOT/venv"
STATIC_ROOT="$PROJECT_ROOT/staticfiles"

echo "🚀 Deploying Kinoush Store to $ENVIRONMENT..."

# Step 1: Create/activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Step 2: Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Step 3: Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --clear

# Step 4: Run migrations
echo "🔄 Running migrations..."
python manage.py migrate --noinput

# Step 5: Restart application (if using Passenger/cPanel)
if [ -f "$PROJECT_ROOT/tmp/restart.txt" ]; then
    touch "$PROJECT_ROOT/tmp/restart.txt"
    echo "✅ Touched tmp/restart.txt to restart Passenger"
fi

echo "✅ Deployment completed successfully!"
echo ""
echo "📝 Next steps:"
echo "  1. Verify DJANGO_SECRET_KEY is set in environment variables"
echo "  2. Verify DATABASE_URL is configured"
echo "  3. Test your application at https://yourdomain.com"
