# DigitalOcean Deployment Guide

Complete guide to deploy Stem Splitter API on DigitalOcean.

## Option 1: App Platform (Recommended - Easiest)

DigitalOcean App Platform is the easiest way to deploy - similar to Railway/Render.

### Prerequisites

- DigitalOcean account (sign up at https://www.digitalocean.com)
- GitHub repository pushed (already done: https://github.com/bantoinese83/Stem-Splitter-API)

### Step-by-Step Deployment

#### 1. Create New App

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click **"Create App"**
3. Select **"GitHub"** as source
4. Authorize DigitalOcean to access your GitHub (if first time)
5. Select repository: `bantoinese83/Stem-Splitter-API`
6. Select branch: `main`
7. Click **"Next"**

#### 2. Configure Build Settings

DigitalOcean will auto-detect the Dockerfile. Verify:

- **Type**: Docker
- **Dockerfile Path**: `Dockerfile` (should be auto-detected)
- **Dockerfile Location**: Root directory

If Dockerfile is not detected:
- Click **"Edit"** next to the service
- Change **Type** to **"Docker"**
- Set **Dockerfile Path** to `Dockerfile`

#### 3. Configure App Settings

**Basic Settings:**
- **App Name**: `stem-splitter-api` (or your preferred name)
- **Region**: Choose closest to your users (e.g., `NYC`, `SFO`, `AMS`)

**Resource Settings:**
- **Plan**: **Basic** ($5/month) or **Professional** ($12/month)
- **CPU**: 1 GB RAM, 1 vCPU (minimum for Spleeter)
- **Note**: Spleeter needs at least 1GB RAM

**Environment Variables** (optional):
```
MAX_FILE_SIZE_MB=100
RATE_LIMIT_PER_MINUTE=30
LOG_LEVEL=INFO
```

#### 4. Review and Deploy

1. Review all settings
2. Click **"Create Resources"**
3. DigitalOcean will:
   - Build the Docker image
   - Deploy your app
   - Provide a URL like: `https://stem-splitter-api-xxxxx.ondigitalocean.app`

#### 5. Get Your API URL

After deployment (5-10 minutes):
- Go to your app dashboard
- Find **"Live App"** section
- Copy the URL: `https://your-app.ondigitalocean.app`
- Test: `curl https://your-app.ondigitalocean.app/health`

### Post-Deployment

#### Test Your API

```bash
# Health check
curl https://your-app.ondigitalocean.app/health

# Test separation (replace with your URL)
curl -X POST "https://your-app.ondigitalocean.app/separate" \
  -F "file=@audio.mp3" \
  -F "stems=2" \
  -o output.zip
```

#### Update SDK with Production URL

Update `stem-splitter-sdk/src/index.ts` or documentation:

```typescript
const client = new StemSplitterClient({
  baseUrl: 'https://your-app.ondigitalocean.app'
});
```

---

## Option 2: Droplet (VPS) - More Control

Deploy on a DigitalOcean Droplet for more control and lower cost.

### Step 1: Create Droplet

1. Go to [DigitalOcean Droplets](https://cloud.digitalocean.com/droplets/new)
2. **Choose an image**: Ubuntu 22.04 LTS
3. **Choose a plan**: 
   - **Basic**: $6/month (1GB RAM, 1 vCPU) - minimum
   - **Regular**: $12/month (2GB RAM, 1 vCPU) - recommended
4. **Choose a datacenter region**: Closest to your users
5. **Authentication**: SSH keys (recommended) or root password
6. Click **"Create Droplet"**

### Step 2: SSH into Droplet

```bash
ssh root@your-droplet-ip
```

### Step 3: Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python and dependencies
apt install -y python3.11 python3-pip python3-venv ffmpeg libsndfile1 nginx git

# Install Docker (optional, for containerized deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

### Step 4: Clone Repository

```bash
cd /opt
git clone https://github.com/bantoinese83/Stem-Splitter-API.git
cd Stem-Splitter-API
```

### Step 5: Set Up Application

**Option A: Direct Python Deployment**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p temp/uploads temp/output logs

# Test run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Option B: Docker Deployment**

```bash
# Build Docker image
docker build -t stem-splitter-api .

# Run container
docker run -d \
  --name stem-splitter-api \
  -p 8000:8000 \
  -v $(pwd)/pretrained_models:/app/pretrained_models \
  stem-splitter-api
```

### Step 6: Set Up Systemd Service

Create `/etc/systemd/system/stem-splitter-api.service`:

```ini
[Unit]
Description=Stem Splitter API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/Stem-Splitter-API
Environment="PATH=/opt/Stem-Splitter-API/venv/bin"
ExecStart=/opt/Stem-Splitter-API/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable stem-splitter-api
systemctl start stem-splitter-api
systemctl status stem-splitter-api
```

### Step 7: Configure Nginx (Reverse Proxy)

Create `/etc/nginx/sites-available/stem-splitter-api`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # or your droplet IP

    client_max_body_size 100M;
    client_body_timeout 600s;
    proxy_read_timeout 600s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
ln -s /etc/nginx/sites-available/stem-splitter-api /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Step 8: Set Up SSL (Let's Encrypt)

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

Certbot will automatically:
- Obtain SSL certificate
- Configure Nginx
- Set up auto-renewal

---

## Option 3: Container Registry + App Platform

Use DigitalOcean Container Registry for Docker images.

### Step 1: Create Container Registry

1. Go to [Container Registry](https://cloud.digitalocean.com/registry)
2. Click **"Create Registry"**
3. Choose name: `stem-splitter-api`
4. Choose plan: **Basic** ($5/month)
5. Click **"Create Registry"**

### Step 2: Build and Push Image

```bash
# Install doctl (DigitalOcean CLI)
# macOS: brew install doctl
# Linux: https://docs.digitalocean.com/reference/doctl/how-to/install/

# Authenticate
doctl registry login

# Build image
docker build -t registry.digitalocean.com/your-registry/stem-splitter-api:latest .

# Push image
docker push registry.digitalocean.com/your-registry/stem-splitter-api:latest
```

### Step 3: Deploy via App Platform

1. Create new App Platform app
2. Select **"Container Registry"** as source
3. Choose your registry and image
4. Configure resources and deploy

---

## Cost Comparison

| Option | Monthly Cost | Setup Difficulty | Best For |
|--------|-------------|------------------|----------|
| App Platform | $5-12 | ⭐ Easy | Quick deployment |
| Droplet | $6-12 | ⭐⭐ Medium | More control |
| Container Registry + App | $10-17 | ⭐⭐ Medium | CI/CD workflows |

---

## Environment Variables

Set these in App Platform or `.env` file:

```env
MAX_FILE_SIZE_MB=100
RATE_LIMIT_PER_MINUTE=30
LOG_LEVEL=INFO
UPLOAD_DIR=temp/uploads
OUTPUT_DIR=temp/output
```

---

## Monitoring & Logs

### App Platform

- View logs in App Platform dashboard
- Go to your app → **"Runtime Logs"**

### Droplet

```bash
# View service logs
journalctl -u stem-splitter-api -f

# View Docker logs (if using Docker)
docker logs -f stem-splitter-api
```

---

## Troubleshooting

### App Platform Issues

**Build Fails:**
- Check Dockerfile path is correct
- Verify all dependencies in requirements.txt
- Check build logs in dashboard

**Out of Memory:**
- Upgrade to larger plan (2GB RAM)
- Reduce `--workers` count in Dockerfile

**Slow Performance:**
- Upgrade to Professional plan
- Increase CPU/RAM allocation

### Droplet Issues

**Service Won't Start:**
```bash
# Check status
systemctl status stem-splitter-api

# Check logs
journalctl -u stem-splitter-api -n 50

# Verify Python/venv
which python3
source /opt/Stem-Splitter-API/venv/bin/activate
python --version
```

**Port Already in Use:**
```bash
# Find process using port 8000
lsof -i :8000
# Kill process or change port
```

**Nginx 502 Bad Gateway:**
- Check API is running: `curl http://localhost:8000/health`
- Check Nginx config: `nginx -t`
- Check Nginx logs: `tail -f /var/log/nginx/error.log`

---

## Recommended: App Platform

For most users, **App Platform** is the best choice:
- ✅ Easiest setup (5 minutes)
- ✅ Automatic SSL
- ✅ Auto-scaling
- ✅ Built-in monitoring
- ✅ GitHub integration
- ✅ $5/month starting cost

---

## Next Steps After Deployment

1. **Test API**: `curl https://your-app.ondigitalocean.app/health`
2. **Update SDK**: Add production URL to examples
3. **Monitor**: Set up alerts in DigitalOcean dashboard
4. **Scale**: Upgrade plan if needed based on usage

---

## Support

- DigitalOcean Docs: https://docs.digitalocean.com
- App Platform Docs: https://docs.digitalocean.com/products/app-platform
- Community: https://www.digitalocean.com/community

