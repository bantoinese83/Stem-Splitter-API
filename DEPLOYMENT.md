# Deployment Guide

This guide covers multiple deployment options for the Stem Splitter API.

## Prerequisites

- Python 3.10+ installed
- Git repository (optional, for CI/CD)
- Account on your chosen hosting platform

## Quick Deploy Options

### Option 1: Railway (Recommended - Easiest)

Railway is the easiest option with automatic deployments from GitHub.

#### Steps:

1. **Push to GitHub** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy on Railway**:
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect the Dockerfile and deploy

3. **Set Environment Variables** (optional):
   - `MAX_FILE_SIZE_MB=100`
   - `RATE_LIMIT_PER_MINUTE=30`
   - `LOG_LEVEL=INFO`

4. **Get Your API URL**:
   - Railway provides a URL like: `https://your-app.railway.app`
   - Production URL: `https://stem-splitter-api-production.up.railway.app`
   - Use this URL in your SDK: `baseUrl: 'https://stem-splitter-api-production.up.railway.app'`

#### Railway Configuration:

The `railway.json` file is already configured. Railway will:
- Build using Dockerfile
- Start with 2 workers
- Auto-restart on failure

---

### Option 2: Render

Render offers free tier with automatic SSL.

#### Steps:

1. **Push to GitHub** (if not already done)

2. **Deploy on Render**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect settings from `render.yaml`

3. **Configuration**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
   - Environment: Python 3

4. **Get Your API URL**:
   - Render provides: `https://your-app.onrender.com`
   - Use this in your SDK

---

### Option 3: Docker (Any Platform)

Deploy using Docker on any platform that supports containers.

#### Build Docker Image:

```bash
docker build -t stem-splitter-api .
```

#### Run Locally:

```bash
docker run -p 8000:8000 \
  -e MAX_FILE_SIZE_MB=100 \
  -e RATE_LIMIT_PER_MINUTE=30 \
  stem-splitter-api
```

#### Deploy to Cloud:

**AWS ECS/Fargate:**
```bash
# Tag and push to ECR
docker tag stem-splitter-api:latest <account>.dkr.ecr.<region>.amazonaws.com/stem-splitter-api:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/stem-splitter-api:latest
```

**Google Cloud Run:**
```bash
gcloud builds submit --tag gcr.io/<project-id>/stem-splitter-api
gcloud run deploy stem-splitter-api \
  --image gcr.io/<project-id>/stem-splitter-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**DigitalOcean App Platform:**
- Connect GitHub repo
- Select Dockerfile
- Deploy automatically

---

### Option 4: Traditional VPS (Ubuntu/Debian)

Deploy on a VPS like DigitalOcean, Linode, or AWS EC2.

#### Steps:

1. **SSH into your server**:
   ```bash
   ssh user@your-server-ip
   ```

2. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y python3.11 python3-pip python3-venv ffmpeg libsndfile1 nginx
   ```

3. **Clone repository**:
   ```bash
   git clone <your-repo-url>
   cd stem-splitter-api
   ```

4. **Set up virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Create systemd service** (`/etc/systemd/system/stem-splitter-api.service`):
   ```ini
   [Unit]
   Description=Stem Splitter API
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/stem-splitter-api
   Environment="PATH=/opt/stem-splitter-api/venv/bin"
   ExecStart=/opt/stem-splitter-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

6. **Start service**:
   ```bash
   sudo systemctl enable stem-splitter-api
   sudo systemctl start stem-splitter-api
   sudo systemctl status stem-splitter-api
   ```

7. **Configure Nginx** (reverse proxy):
   ```nginx
   server {
       listen 80;
       server_name api.yourdomain.com;

       client_max_body_size 100M;
       client_body_timeout 600s;
       proxy_read_timeout 600s;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

8. **Set up SSL with Let's Encrypt**:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d api.yourdomain.com
   ```

---

## Environment Variables

Configure these via your hosting platform's dashboard:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Server port (auto-set by most platforms) |
| `MAX_FILE_SIZE_MB` | `100` | Maximum upload size in MB |
| `RATE_LIMIT_PER_MINUTE` | `30` | Requests per minute per IP |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `UPLOAD_DIR` | `temp/uploads` | Upload directory path |
| `OUTPUT_DIR` | `temp/output` | Output directory path |

---

## Post-Deployment Checklist

- [ ] API responds at `/health` endpoint
- [ ] API docs accessible at `/docs`
- [ ] Test separation endpoint with sample file
- [ ] Verify CORS headers (if needed)
- [ ] Check logs for errors
- [ ] Update SDK with production API URL
- [ ] Set up monitoring/alerting (optional)

---

## Monitoring

### Health Check Endpoint

Monitor your API using the `/health` endpoint:

```bash
curl https://your-api-url.com/health
```

### Logs

**Railway:**
- View logs in Railway dashboard

**Render:**
- View logs in Render dashboard

**Docker:**
```bash
docker logs <container-id>
```

**Systemd:**
```bash
sudo journalctl -u stem-splitter-api -f
```

---

## Troubleshooting

### API Not Starting

1. Check logs for errors
2. Verify Python version (3.10+)
3. Ensure all dependencies installed
4. Check port availability

### Out of Memory

- Reduce `--workers` count
- Increase server RAM
- Lower `MAX_FILE_SIZE_MB`

### Slow Processing

- Increase workers: `--workers 4`
- Use faster server (more CPU cores)
- Consider GPU instance for Spleeter

---

## Cost Estimates

| Platform | Free Tier | Paid Tier |
|----------|-----------|-----------|
| Railway | $5/month credit | ~$20/month |
| Render | Free (sleeps after inactivity) | ~$7/month |
| DigitalOcean | - | $6/month (basic) |
| AWS/GCP | Free tier available | Pay-as-you-go |

---

## Next Steps

After deployment:

1. **Update SDK** with your production API URL
2. **Publish npm package** (see PUBLISHING.md)
3. **Test integration** with SDK
4. **Set up domain** (optional)
5. **Configure monitoring** (optional)

---

## Support

For issues, check:
- API logs
- Health endpoint: `/health`
- API docs: `/docs`

