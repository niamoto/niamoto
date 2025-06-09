# Deployment Guide

This guide covers deploying your Niamoto-generated static website to various hosting platforms, from simple static hosts to advanced CI/CD workflows.

## Overview

Niamoto generates completely static websites that can be hosted anywhere that serves HTML files. This guide covers:

1. Built-in deployment commands
2. Manual deployment methods
3. Automated CI/CD workflows
4. Performance optimization
5. Domain configuration

## Prerequisites

- Completed Niamoto project with exported website
- Basic understanding of web hosting
- Command line access

## Built-in Deployment Commands

Niamoto provides built-in deployment commands for popular platforms.

### GitHub Pages

Deploy directly to GitHub Pages with a single command:

```bash
# Deploy to GitHub Pages
niamoto deploy github --repo https://github.com/username/project-name.git

# Deploy to custom branch
niamoto deploy github --repo https://github.com/username/project-name.git --branch main

# Deploy with custom commit author
niamoto deploy github --repo https://github.com/username/project-name.git \
  --name "Your Name" --email "your.email@example.com"
```

**Prerequisites for GitHub Pages:**
1. GitHub repository created
2. GitHub Pages enabled in repository settings (source: Deploy from branch `gh-pages`)
3. Write access to the repository
4. Completed website export (`niamoto export` or `niamoto run`)

**Setup steps:**
```bash
# Run from your Niamoto project directory
niamoto deploy github --repo https://github.com/username/project-name.git
```

**How it works:**
- The command operates on your exported website in the output directory (typically `exports/web/`)
- Automatically initializes Git in the output directory if needed
- Creates or switches to the `gh-pages` branch
- Commits all website files with timestamp
- Force pushes to the specified repository

**Note**: You don't need to manually initialize Git or manage branches - the deploy command handles everything automatically.

**Result:** Your site will be available at `https://username.github.io/project-name/`

### Netlify

Deploy to Netlify with their site ID:

```bash
# Deploy to Netlify
niamoto deploy netlify --site-id your-netlify-site-id
```

**Prerequisites for Netlify:**
1. Netlify account created
2. Site created in Netlify dashboard
3. Netlify CLI installed (optional but recommended)

**Setup steps:**
```bash
# 1. Install Netlify CLI (optional)
npm install -g netlify-cli
netlify login

# 2. Create site and get site ID
netlify sites:create --name your-site-name

# 3. Deploy
niamoto deploy netlify --site-id abc123-def456-ghi789
```

## Manual Deployment Methods

### Static File Hosting

For any static file host, simply upload the contents of `exports/web/`:

```bash
# Copy to server via rsync
rsync -avz exports/web/ user@yourserver.com:/var/www/html/

# Or upload via FTP/SFTP
sftp user@yourserver.com
put -r exports/web/* /var/www/html/
```

### Amazon S3 + CloudFront

Deploy to S3 for scalable static hosting:

```bash
# Install AWS CLI
pip install awscli
aws configure

# Sync to S3 bucket
aws s3 sync exports/web/ s3://your-bucket-name/ --delete

# Set up CloudFront distribution (optional)
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

**S3 Bucket Policy Example:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

### Vercel

Deploy to Vercel with their CLI:

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd exports/web
vercel --prod
```

### Firebase Hosting

Deploy to Firebase Hosting:

```bash
# Install Firebase CLI
npm install -g firebase-tools
firebase login

# Initialize Firebase project
firebase init hosting

# Configure firebase.json
{
  "hosting": {
    "public": "exports/web",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"]
  }
}

# Deploy
firebase deploy --only hosting
```

## Automated CI/CD Workflows

### GitHub Actions

Create automated deployments with GitHub Actions:

**.github/workflows/deploy.yml:**
```yaml
name: Deploy Niamoto Site

on:
  push:
    branches: [ main ]
  schedule:
    # Rebuild daily at 6 AM UTC (for data updates)
    - cron: '0 6 * * *'

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install niamoto
        pip install -r requirements.txt  # if you have additional deps

    - name: Run Niamoto pipeline
      run: |
        niamoto run

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./exports/web
        cname: your-domain.com  # optional custom domain
```

### GitLab CI/CD

**.gitlab-ci.yml:**
```yaml
stages:
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip/
    - venv/

build_site:
  stage: build
  image: python:3.11
  script:
    - python -m venv venv
    - source venv/bin/activate
    - pip install niamoto
    - niamoto run
  artifacts:
    paths:
      - exports/web/
    expire_in: 1 hour

pages:
  stage: deploy
  script:
    - mkdir public
    - cp -r exports/web/* public/
  artifacts:
    paths:
      - public
  only:
    - main
```

### Custom CI Script

Create a reusable deployment script:

**scripts/deploy.sh:**
```bash
#!/bin/bash
set -e

echo "🚀 Starting Niamoto deployment..."

# Configuration
SITE_URL=${SITE_URL:-"https://your-site.com"}
DEPLOY_METHOD=${DEPLOY_METHOD:-"github"}
BRANCH=${BRANCH:-"gh-pages"}

# Run Niamoto pipeline
echo "📊 Running Niamoto pipeline..."
niamoto run

# Optimize build
echo "⚡ Optimizing build..."
python scripts/optimize_build.py

# Deploy based on method
case $DEPLOY_METHOD in
  "github")
    echo "📤 Deploying to GitHub Pages..."
    niamoto deploy github --repo $GITHUB_REPO --branch $BRANCH
    ;;
  "netlify")
    echo "📤 Deploying to Netlify..."
    niamoto deploy netlify --site-id $NETLIFY_SITE_ID
    ;;
  "s3")
    echo "📤 Deploying to S3..."
    aws s3 sync exports/web/ s3://$S3_BUCKET/ --delete
    aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_ID --paths "/*"
    ;;
  *)
    echo "❌ Unknown deployment method: $DEPLOY_METHOD"
    exit 1
    ;;
esac

echo "✅ Deployment complete! Site available at $SITE_URL"
```

Make it executable and use it:
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

## Performance Optimization

### Build Optimization

Create a build optimization script:

**scripts/optimize_build.py:**
```python
#!/usr/bin/env python3
"""Optimize Niamoto build for production deployment."""

import os
import gzip
import shutil
from pathlib import Path
import json
import re

def minify_html(html_content):
    """Basic HTML minification."""
    # Remove comments
    html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
    # Remove extra whitespace
    html_content = re.sub(r'\s+', ' ', html_content)
    # Remove whitespace around tags
    html_content = re.sub(r'>\s+<', '><', html_content)
    return html_content.strip()

def compress_files(build_dir):
    """Create gzipped versions of text files."""
    text_extensions = {'.html', '.css', '.js', '.json', '.xml', '.txt'}

    for file_path in Path(build_dir).rglob('*'):
        if file_path.is_file() and file_path.suffix in text_extensions:
            # Create gzipped version
            gz_path = file_path.with_suffix(file_path.suffix + '.gz')
            with open(file_path, 'rb') as f_in:
                with gzip.open(gz_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            print(f"Compressed: {file_path.name}")

def optimize_images(build_dir):
    """Optimize images (requires pillow)."""
    try:
        from PIL import Image

        for img_path in Path(build_dir).rglob('*.jpg'):
            with Image.open(img_path) as img:
                # Optimize JPEG quality
                img.save(img_path, 'JPEG', quality=85, optimize=True)
                print(f"Optimized: {img_path.name}")

        for img_path in Path(build_dir).rglob('*.png'):
            with Image.open(img_path) as img:
                # Optimize PNG
                img.save(img_path, 'PNG', optimize=True)
                print(f"Optimized: {img_path.name}")

    except ImportError:
        print("PIL not available, skipping image optimization")

def main():
    build_dir = Path('exports/web')

    if not build_dir.exists():
        print("❌ Build directory not found. Run 'niamoto export' first.")
        return

    print("🔧 Optimizing build...")

    # Minify HTML files
    for html_file in build_dir.rglob('*.html'):
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        minified = minify_html(content)

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(minified)

        print(f"Minified: {html_file.name}")

    # Compress files
    compress_files(build_dir)

    # Optimize images
    optimize_images(build_dir)

    print("✅ Build optimization complete!")

if __name__ == '__main__':
    main()
```

### Web Server Configuration

#### Nginx

**nginx.conf:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/html;
    index index.html;

    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_min_length 1000;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Cache HTML files for shorter time
    location ~* \.html$ {
        expires 1h;
        add_header Cache-Control "public";
    }

    # Handle client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
```

#### Apache

**.htaccess:**
```apache
# Enable compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/plain
    AddOutputFilterByType DEFLATE text/html
    AddOutputFilterByType DEFLATE text/xml
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/xml
    AddOutputFilterByType DEFLATE application/xhtml+xml
    AddOutputFilterByType DEFLATE application/rss+xml
    AddOutputFilterByType DEFLATE application/javascript
    AddOutputFilterByType DEFLATE application/x-javascript
</IfModule>

# Cache static files
<IfModule mod_expires.c>
    ExpiresActive on
    ExpiresByType text/css "access plus 1 year"
    ExpiresByType application/javascript "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType image/jpg "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType text/html "access plus 1 hour"
</IfModule>

# Client-side routing fallback
RewriteEngine On
RewriteBase /
RewriteRule ^index\.html$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.html [L]
```

## Custom Domain Configuration

### DNS Configuration

Point your domain to your hosting platform:

**For GitHub Pages:**
```
CNAME record: www.yourdomain.com → username.github.io
A records for apex domain:
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

**For Netlify:**
```
CNAME record: www.yourdomain.com → your-site.netlify.app
NETLIFY record: yourdomain.com → your-site.netlify.app
```

### SSL/HTTPS Setup

Most platforms provide free SSL certificates:

- **GitHub Pages**: Automatic with custom domains
- **Netlify**: Automatic with Let's Encrypt
- **Cloudflare**: Free SSL proxy
- **AWS**: Certificate Manager integration

## Monitoring and Analytics

### Google Analytics

Add to your custom templates:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

### Plausible Analytics (Privacy-friendly alternative)

```html
<script defer data-domain="yourdomain.com" src="https://plausible.io/js/plausible.js"></script>
```

### Uptime Monitoring

Set up monitoring with services like:
- **UptimeRobot** (free)
- **Pingdom**
- **StatusPage**

## Data Updates

### Automated Data Refresh

For sites with changing data, set up automated rebuilds:

**crontab example:**
```bash
# Rebuild site daily at 6 AM
0 6 * * * cd /path/to/project && ./scripts/deploy.sh
```

**GitHub Actions with data updates:**
```yaml
- name: Update data
  run: |
    # Download fresh data
    curl -o imports/new_data.csv "https://api.example.com/data.csv"

    # Run pipeline
    niamoto import
    niamoto transform
    niamoto export
```

### Webhook Triggers

Set up webhooks to trigger rebuilds when data changes:

**webhook endpoint (Flask example):**
```python
from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Verify webhook signature (recommended)
    signature = request.headers.get('X-Signature')

    if verify_signature(signature, request.data):
        # Trigger rebuild
        subprocess.Popen(['./scripts/deploy.sh'])
        return 'OK', 200

    return 'Unauthorized', 401
```

## Troubleshooting Deployment

### Common Issues

#### Build Fails in CI
```bash
# Check Python version
python --version

# Install exact dependencies
pip install -r requirements.txt

# Run with verbose output
niamoto run --verbose
```

#### Large File Sizes
```bash
# Check file sizes
du -sh exports/web/*

# Optimize images
python scripts/optimize_build.py

# Enable compression
gzip exports/web/*.html
```

#### Broken Links
```bash
# Check for absolute paths
grep -r "file://" exports/web/
grep -r "C:/" exports/web/

# Validate links
npm install -g broken-link-checker
blc http://localhost:8000 -ro
```

### Debugging Steps

1. **Test locally first**:
   ```bash
   cd exports/web
   python -m http.server 8000
   ```

2. **Check file permissions**:
   ```bash
   find exports/web -type f -exec chmod 644 {} \;
   find exports/web -type d -exec chmod 755 {} \;
   ```

3. **Validate HTML**:
   ```bash
   npm install -g html-validate
   html-validate exports/web/*.html
   ```

4. **Check console errors**:
   - Open browser developer tools
   - Check for JavaScript errors
   - Verify all assets load correctly

## Best Practices

### Security
- Use HTTPS everywhere
- Set appropriate security headers
- Keep dependencies updated
- Don't commit sensitive data

### Performance
- Optimize images before deployment
- Enable compression
- Use CDN for static assets
- Monitor Core Web Vitals

### Reliability
- Set up monitoring
- Use automated deployments
- Test in staging environment
- Have rollback procedures

### SEO
- Generate sitemap.xml
- Add meta descriptions
- Use structured data
- Optimize for mobile

## Next Steps

After successful deployment:

1. **Monitor performance** with tools like PageSpeed Insights
2. **Set up analytics** to track usage
3. **Configure alerts** for downtime
4. **Plan data update workflows**
5. **Document your deployment process**

For more advanced configurations:
- [Performance Optimization Guide](../advanced/optimization.md)
- [CI/CD Best Practices](../development/contributing.md)
- [Troubleshooting Guide](../troubleshooting/common-issues.md)
