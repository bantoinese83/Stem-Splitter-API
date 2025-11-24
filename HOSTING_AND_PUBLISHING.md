# Hosting API & Publishing npm Package - Quick Start

Complete guide to host your API and publish the npm SDK package.

## 🚀 Part 1: Host the API

### Option A: Railway (Easiest - Recommended)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy on Railway**:
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway auto-detects Dockerfile and deploys
   - Get your API URL: `https://your-app.railway.app`

3. **Test**:
   ```bash
   curl https://your-app.railway.app/health
   ```

**Done!** Your API is live. Use the URL in your SDK.

---

### Option B: Render (Free Tier)

1. **Push to GitHub** (same as above)

2. **Deploy on Render**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect GitHub repo
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`

3. **Get URL**: `https://your-app.onrender.com`

---

### Option C: Docker (Any Platform)

```bash
# Build
docker build -t stem-splitter-api .

# Run
docker run -p 8000:8000 stem-splitter-api
```

Deploy to:
- **AWS**: ECS/Fargate
- **Google Cloud**: Cloud Run
- **DigitalOcean**: App Platform
- **Heroku**: Container Registry

See `DEPLOYMENT.md` for detailed instructions.

---

## 📦 Part 2: Publish npm Package

### Step 1: Check Package Name Availability

```bash
cd stem-splitter-sdk
npm view stem-splitter-api
```

If taken, update `package.json` with a different name:
- `@your-username/stem-splitter-api` (scoped)
- `stem-splitter-sdk`
- `stem-splitter-client`

### Step 2: Update package.json

Edit `stem-splitter-sdk/package.json`:

```json
{
  "name": "stem-splitter-api",  // or your chosen name
  "version": "1.0.0",
  "author": "Your Name <your.email@example.com>",
  "repository": {
    "type": "git",
    "url": "https://github.com/your-username/stem-splitter-api.git"
  }
}
```

### Step 3: Build & Quality Check

```bash
cd stem-splitter-sdk
npm run build
npm run quality
```

### Step 4: Login to npm

```bash
npm login
```

Enter your npm credentials.

### Step 5: Publish

```bash
npm publish
```

For scoped packages:
```bash
npm publish --access public
```

### Step 6: Verify

```bash
npm view stem-splitter-api
```

Or visit: `https://www.npmjs.com/package/stem-splitter-api`

---

## 🔗 Part 3: Update SDK with Production API URL

After hosting, update the SDK default baseUrl:

1. **Update SDK README** with production URL example
2. **Update examples** to use production URL
3. **Publish update**:

```bash
cd stem-splitter-sdk
npm version patch  # 1.0.0 -> 1.0.1
npm publish
```

---

## ✅ Checklist

### API Hosting:
- [ ] Code pushed to GitHub
- [ ] Deployed on hosting platform
- [ ] Health check passes: `/health`
- [ ] API docs accessible: `/docs`
- [ ] Test separation endpoint works
- [ ] Got production API URL

### npm Publishing:
- [ ] Package name available
- [ ] package.json updated (author, repository)
- [ ] Build successful
- [ ] Quality checks pass
- [ ] Logged in to npm
- [ ] Published successfully
- [ ] Verified on npm website

### Post-Publishing:
- [ ] Updated SDK with production API URL
- [ ] Updated documentation
- [ ] Tested installation: `npm install stem-splitter-api`
- [ ] Shared with community

---

## 📚 Detailed Guides

- **Full Deployment Guide**: See `DEPLOYMENT.md`
- **Full Publishing Guide**: See `stem-splitter-sdk/PUBLISHING.md`

---

## 🆘 Troubleshooting

### API Not Starting
- Check logs on hosting platform
- Verify Python 3.10+ installed
- Check port configuration

### npm Publish Fails
- Verify login: `npm whoami`
- Check package name availability
- Ensure build succeeds: `npm run build`

### Package Name Taken
- Use scoped package: `@username/package-name`
- Choose different name
- Check npm for alternatives

---

## 🎉 You're Done!

Your API is hosted and npm package is published!

**Next Steps:**
1. Share your API URL
2. Share npm package: `npm install stem-splitter-api`
3. Update documentation with production URLs
4. Monitor usage and respond to issues

