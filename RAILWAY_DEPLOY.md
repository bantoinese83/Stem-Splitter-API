# Railway Deployment Guide

Complete step-by-step guide to deploy Stem Splitter API on Railway.

## Prerequisites

- Railway account (sign up at https://railway.app - free $5 credit)
- GitHub repository: `bantoinese83/Stem-Splitter-API` (already pushed ✅)

## Step-by-Step Deployment

### Step 1: Sign Up / Login to Railway

1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"** or **"Login"**
3. Sign up with GitHub (recommended) or email

### Step 2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub (if first time)
4. Select repository: **`bantoinese83/Stem-Splitter-API`**
5. Click **"Deploy Now"**

### Step 3: Railway Auto-Detection

Railway will automatically:
- ✅ Detect the `Dockerfile`
- ✅ Read `railway.json` configuration
- ✅ Start building your app
- ✅ Deploy to a public URL

**Note:** The build may take 5-10 minutes the first time (downloading dependencies and models).

### Step 4: Configure Environment Variables (Optional)

While building, you can set environment variables:

1. Click on your service
2. Go to **"Variables"** tab
3. Add variables (optional):
   ```
   MAX_FILE_SIZE_MB=100
   RATE_LIMIT_PER_MINUTE=30
   LOG_LEVEL=INFO
   ```

These are optional - defaults will work fine.

### Step 5: Get Your API URL

After deployment completes:

1. Go to your project dashboard
2. Click on the service
3. Go to **"Settings"** tab
4. Find **"Generate Domain"** button
5. Click it to get a public URL like: `https://stem-splitter-api-production.up.railway.app`

Or Railway may auto-generate one: `https://your-app-name.up.railway.app`

### Step 6: Test Your API

```bash
# Health check
curl https://stem-splitter-api-production.up.railway.app/health

# Should return:
# {
#   "status": "healthy",
#   "service": "Stem Splitter API",
#   "version": "1.0.0",
#   ...
# }
```

### Step 7: Test Separation Endpoint

```bash
curl -X POST "https://stem-splitter-api-production.up.railway.app/separate" \
  -F "file=@audio.mp3" \
  -F "stems=2" \
  -o output.zip
```

## Railway Configuration

Your `railway.json` is already configured:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Railway will:
- ✅ Build using Dockerfile
- ✅ Start with 2 workers
- ✅ Auto-restart on failure
- ✅ Use PORT environment variable automatically

## Custom Domain (Optional)

1. Go to your service → **"Settings"**
2. Click **"Custom Domain"**
3. Add your domain (e.g., `api.yourdomain.com`)
4. Follow DNS instructions to point domain to Railway

## Monitoring & Logs

### View Logs

1. Go to your service dashboard
2. Click **"Deployments"** tab
3. Click on latest deployment
4. View **"Build Logs"** and **"Deploy Logs"**

### Real-time Logs

1. Go to your service
2. Click **"View Logs"** button
3. See real-time application logs

## Troubleshooting

### Build Fails

**Issue:** Build timeout or errors

**Solutions:**
- Check build logs in Railway dashboard
- Verify Dockerfile is correct
- Ensure `requirements.txt` has all dependencies
- Check if models are too large (may need Git LFS)

### Out of Memory

**Issue:** Service crashes or runs out of memory

**Solutions:**
- Upgrade Railway plan (more RAM)
- Reduce workers in `railway.json`: `--workers 1`
- Lower `MAX_FILE_SIZE_MB` environment variable

### Service Won't Start

**Issue:** Service shows as "Failed" or won't start

**Solutions:**
- Check deploy logs
- Verify PORT environment variable (Railway sets this automatically)
- Check health check endpoint: `/health`
- Verify all dependencies installed correctly

### Slow Performance

**Issue:** API responses are slow

**Solutions:**
- Upgrade to higher plan (more CPU/RAM)
- Increase workers: `--workers 4` (if plan allows)
- Check Railway region (choose closest to users)

## Cost

Railway offers:
- **Free $5 credit** when you sign up
- **Pay-as-you-go** pricing
- **Hobby plan**: ~$5-10/month for small apps
- **Pro plan**: $20/month for production apps

**Estimated costs:**
- Small usage: $5-10/month
- Medium usage: $10-20/month
- High usage: $20-50/month

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | Auto-set by Railway | Server port (don't change) |
| `MAX_FILE_SIZE_MB` | 100 | Maximum upload size in MB |
| `RATE_LIMIT_PER_MINUTE` | 30 | Requests per minute per IP |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Post-Deployment Checklist

- [ ] API responds at `/health` endpoint
- [ ] API docs accessible at `/docs`
- [ ] Test separation endpoint with sample file
- [ ] Check logs for any errors
- [ ] Update SDK with production API URL
- [ ] Set up monitoring/alerts (optional)

## Update SDK with Production URL

After deployment, update your SDK examples:

```typescript
// In stem-splitter-sdk/README.md or examples
const client = new StemSplitterClient({
  baseUrl: 'https://stem-splitter-api-production.up.railway.app'
});
```

Then publish update:
```bash
cd stem-splitter-sdk
npm version patch
npm publish
```

## Continuous Deployment

Railway automatically deploys when you push to GitHub:

1. Make changes to your code
2. Commit and push:
   ```bash
   git add .
   git commit -m "Update API"
   git push
   ```
3. Railway detects push and redeploys automatically
4. New deployment appears in Railway dashboard

## Scaling

### Vertical Scaling (More Resources)

1. Go to service → **"Settings"**
2. Click **"Resources"**
3. Adjust CPU/RAM allocation
4. Railway will restart with new resources

### Horizontal Scaling (More Instances)

1. Go to service → **"Settings"**
2. Click **"Scaling"**
3. Increase instance count
4. Railway will create multiple instances

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Status Page: https://status.railway.app

## Quick Commands Reference

```bash
# Test health
curl https://stem-splitter-api-production.up.railway.app/health

# Test separation
curl -X POST "https://stem-splitter-api-production.up.railway.app/separate" \
  -F "file=@audio.mp3" \
  -F "stems=2" \
  -o output.zip

# View API docs
open https://stem-splitter-api-production.up.railway.app/docs
```

---

## Summary

Railway is the easiest deployment option:
- ✅ 5-minute setup
- ✅ Automatic deployments from GitHub
- ✅ Free $5 credit to start
- ✅ Auto SSL certificates
- ✅ Built-in monitoring
- ✅ Easy scaling

Your API will be live at: `https://stem-splitter-api-production.up.railway.app`

