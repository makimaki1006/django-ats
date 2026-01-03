#!/usr/bin/env bash
# Render Build Script for Django ATS
# This script is executed during the build phase on Render

set -o errexit  # Exit on error
set -o pipefail # Exit on pipe failure

echo "=== Django ATS Build Script ==="
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Upgrade pip
echo "=== Upgrading pip ==="
pip install --upgrade pip

# Install dependencies
echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

# Install Node.js dependencies for Tailwind CSS (if needed)
if [ -f "package.json" ]; then
    echo "=== Installing Node.js dependencies ==="
    npm install

    # Build Tailwind CSS
    echo "=== Building Tailwind CSS ==="
    npm run build:css || echo "Warning: Tailwind CSS build skipped or failed"
fi

# Collect static files
echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

# Run database migrations
echo "=== Running database migrations ==="
python manage.py migrate --no-input

# Create cache table (if using database cache)
echo "=== Creating cache table ==="
python manage.py createcachetable || echo "Cache table already exists or not needed"

echo "=== Build completed successfully ==="
