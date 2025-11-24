# Railway Timeout Configuration Guide

## How to Check Railway Timeout Settings

### Method 1: Railway Dashboard (UI)

1. **Go to Railway Dashboard**:
   - Visit: https://railway.app/dashboard
   - Log in to your account

2. **Select Your Project**:
   - Click on your project: `Stem-Splitter-API` (or your project name)

3. **Select Your Service**:
   - Click on the service running your API

4. **Check Settings**:
   - Click on **"Settings"** tab
   - Look for:
     - **"Deployments"** section
     - **"Environment Variables"** section
     - **"Network"** or **"Advanced"** settings
     - Any timeout-related options

5. **Check Environment Variables**:
   - In the **"Variables"** tab
   - Look for variables like:
     - `TIMEOUT`
     - `REQUEST_TIMEOUT`
     - `PROXY_TIMEOUT`
     - `RAILWAY_TIMEOUT`

### Method 2: Railway CLI

```bash
# Install Railway CLI (if not installed)
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# List environment variables
railway variables

# Check service settings
railway status
```

### Method 3: Railway API

Railway doesn't expose timeout settings via their API or dashboard directly. The edge proxy timeout is typically:
- **Default**: ~30 seconds for HTTP requests
- **Edge Proxy Timeout**: ~6-10 seconds (this is what's causing 502 errors)

## The Problem

Railway's **edge proxy** (the load balancer in front of your service) has a hardcoded timeout of approximately **6-10 seconds**. This is separate from your application timeout and cannot be configured via Railway's dashboard.

When your separation process takes longer than this, Railway's edge proxy returns a **502 Bad Gateway** error before your application can respond.

## Solutions

### Solution 1: Pre-warm TensorFlow Models (Recommended)

Pre-load TensorFlow models on application startup so the first request is faster:

**File: `app/main.py`** - Add model pre-warming:

```python
@app.on_event("startup")
async def startup_event():
    """Pre-warm TensorFlow models on startup."""
    logger.info("Pre-warming TensorFlow models...")
    try:
        # Pre-initialize separators for common stem counts
        for stems in [2, 4]:
            logger.info(f"Pre-warming {stems}-stem model...")
            separator = spleeter_service.get_separator(stems)
            logger.info(f"{stems}-stem model ready")
    except Exception as e:
        logger.warning(f"Model pre-warming failed (non-critical): {e}")
    logger.info("Startup complete - models ready")
```

### Solution 2: Increase Uvicorn Timeout

**File: `start.sh`** - Add timeout settings:

```bash
#!/bin/bash
PORT=${PORT:-8000}

# Increase timeout for long-running requests
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --workers 1 \
  --timeout-keep-alive 300 \
  --timeout-graceful-shutdown 30
```

### Solution 3: Use Async Processing with Job Queue

Implement background job processing:

1. Client sends request → Returns job ID immediately
2. Processing happens in background
3. Client polls `/status/{job_id}` to check progress
4. Client downloads result when ready

### Solution 4: Optimize Separation Process

- Cache TensorFlow sessions
- Use smaller model variants
- Optimize I/O operations

### Solution 5: Contact Railway Support

If you have a paid plan, contact Railway support:
- Email: support@railway.app
- Discord: https://discord.gg/railway
- Ask about: Increasing edge proxy timeout for your service

## Current Configuration

Your `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "./start.sh",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Note**: Railway doesn't support timeout configuration in `railway.json`. The timeout is controlled by Railway's edge proxy.

## Recommended Immediate Fix

**Pre-warm models on startup** - This will reduce the first request time significantly and may prevent timeouts.

## Testing Timeout

To test if timeout is the issue:

```bash
# Test with a very small file first
curl -X POST "https://stem-splitter-api-production.up.railway.app/separate" \
  -F "file=@small_audio.mp3" \
  -F "stems=2" \
  -o output.zip \
  --max-time 120
```

If small files work but larger ones timeout, it confirms the timeout issue.

