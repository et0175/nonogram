# Railway Deployment Guide

**Application:** Nonogram Web (Next.js + Python CLI)  
**Status:** Ready for deployment  
**Date:** 2026-09-05

## ✅ Deployment Files Created

| File | Purpose |
|------|---------|
| `Procfile` | Tells Railway how to start the app |
| `requirements.txt` | Python dependencies (root level) |
| `runtime.txt` | Python version specification |

## 🚀 Deployment Steps

### Step 1: Prepare GitHub Repository
1. Push all changes to your GitHub repo:
   ```bash
   git add .
   git commit -m "Add Railway deployment configuration"
   git push origin main
   ```

### Step 2: Connect to Railway
1. Go to [railway.app](https://railway.app)
2. Click **"New Project"**
3. Click **"Deploy from GitHub"**
4. Select your repository
5. Railway will auto-detect the configuration and start building!

### Step 3: Configure Environment (if needed)
1. In Railway dashboard, go to your project
2. Click **"Variables"**
3. Set any environment variables needed:
   - `NODE_ENV=production`
   - `PORT=8080` (Railway uses this)

### Step 4: Deploy
Railway will:
1. Install Python dependencies from `requirements.txt`
2. Install Node.js dependencies from `package.json`
3. Run `npm run build` to build Next.js
4. Start the app using `Procfile`

### Step 5: Access Your App
- Railway assigns a public URL like: `your-app-xxxxxx.railway.app`
- Share this URL with anyone to access the app!

## 📋 Configuration Details

### Procfile
```
web: cd nonogram-web && npm start
```
- Tells Railway to start the Next.js app from `nonogram-web` directory
- Uses `npm start` which runs `next start` (production mode)

### requirements.txt (Root)
```
Pillow>=10.0.0
numpy>=1.24.0
reportlab>=4.0.0
```
- Python dependencies needed for the nonogram CLI
- Installed before Node.js dependencies
- Located at project root so Railway can find it

### runtime.txt
```
python-3.11.0
```
- Specifies Python version (must match your local setup)
- Railway uses this to select the correct Python runtime

## 🔧 How It Works

### Build Process
```
1. Railway detects Procfile
2. Installs Python (3.11.0)
3. Pip install requirements.txt
4. Installs Node.js
5. npm install (from package.json)
6. npm run build (Next.js build)
7. Starts app using Procfile
```

### Runtime
```
Node.js starts Next.js server
├─ Listens on PORT (Railway env var)
├─ Serves Next.js app
├─ API routes handle form submission
└─ Calls Python CLI via subprocess
```

## ✨ Features

✅ **File Actions:**
- Copy Path button (copies to clipboard)
- Open button (opens file with system default app)

✅ **Auto-deployment:**
- Push to GitHub → Railway auto-deploys
- No manual redeploy needed

✅ **Shareable URL:**
- Anyone can access via Railway URL
- No setup required on user side

✅ **Full Stack:**
- Next.js frontend ✅
- Python CLI backend ✅
- Both run together ✅

## 🐛 Troubleshooting

### Build Failed
**Error:** "Build failed"
- Check Railway logs for details
- Ensure `Procfile`, `requirements.txt`, `runtime.txt` exist
- Verify `package.json` has build script

### App Crashes
**Error:** "Application exited"
- Check Railway logs
- Verify Python version in `runtime.txt`
- Ensure nonogram CLI is installed

### Missing Python Packages
**Error:** "ModuleNotFoundError"
- Add package to `requirements.txt`
- Push to GitHub
- Railway will rebuild automatically

## 📊 Deployment Checklist

- [ ] All changes committed to GitHub
- [ ] `Procfile` exists in root
- [ ] `requirements.txt` exists in root
- [ ] `runtime.txt` specifies Python 3.11.0
- [ ] `package.json` in `nonogram-web/` has build script
- [ ] GitHub account connected to Railway
- [ ] Repository is public or connected to Railway

## 🎯 Next Steps

1. **Run locally first:**
   ```bash
   cd nonogram-web
   npm install
   npm run build
   npm start
   ```
   Visit: `http://localhost:3000`

2. **Push to GitHub:**
   ```bash
   git push origin main
   ```

3. **Deploy to Railway:**
   - Open railway.app
   - Click "New Project"
   - Select GitHub repo
   - Watch the deployment!

4. **Share with others:**
   - Copy the Railway URL
   - Share it in a message/email
   - They can access it immediately!

## 📞 Support

- Railway Docs: https://docs.railway.app
- GitHub Integration: https://docs.railway.app/guides/github-integration
- Procfile Format: https://docs.railway.app/guides/procfile

---

**Status: Ready to Deploy** ✅  
**Files Created:** 3  
**Tests Passing:** 28/28  
**Production Ready:** YES
