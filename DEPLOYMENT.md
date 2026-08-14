# 🚀 Deployment Guide: Render (Backend) & Vercel (Frontend)

This guide provides step-by-step instructions for deploying **COE Automator** (FastAPI backend + React Vite frontend) to **Render** and **Vercel**.

---

## 🛠️ Step 1: Deploy Backend on Render

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** > **Web Service**.
3. Connect your GitHub repository (`COE-Assistant` / `coeautomator`).
4. Configure the Web Service settings:
   - **Name**: `coe-automator-api`
   - **Region**: Select your preferred region (e.g. Singapore / US East)
   - **Branch**: `main`
   - **Root Directory**: Leave blank (or `.`)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

5. Under **Environment Variables**, add the following keys:
   | Key | Description | Example / Value |
   |---|---|---|
   | `PYTHON_VERSION` | Python Runtime Version | `3.11.0` |
   | `GEMINI_API_KEY` | Google Gemini API Key | `AIzaSy...` |
   | `OPENAI_API_KEY` | OpenAI API Key (Fallback) | `sk-proj-...` |
   | `TURSO_DATABASE_URL` | Turso Cloud Database URL | `libsql://your-db.turso.io` |
   | `TURSO_AUTH_TOKEN` | Turso Auth Token | `ey...` |
   | `ALLOWED_ORIGINS` | Allowed Frontend CORS Origins | `*` (or `https://your-app.vercel.app`) |

6. Click **Create Web Service**. Once deployed, copy your backend URL:
   `https://coe-automator-api.onrender.com`

---

## ⚡ Step 2: Deploy Frontend on Vercel

1. Log in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** > **Project**.
3. Import your GitHub repository.
4. Configure Project Settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` (click Edit, select `frontend`)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

5. Verify `frontend/vercel.json` rewrites are configured to proxy `/api/` calls to your Render backend:
   ```json
   {
     "buildCommand": "npm run build",
     "outputDirectory": "dist",
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "https://coe-automator-api.onrender.com/api/:path*"
       },
       {
         "source": "/(.*)",
         "destination": "/index.html"
       }
     ]
   }
   ```
   *(Replace `https://coe-automator-api.onrender.com` with your actual Render backend URL)*

6. Click **Deploy**. Vercel will build and host your frontend application.

---

## 🔍 Verification & Health Check

1. **Backend Health Check**:
   Open `https://coe-automator-api.onrender.com/api/status` in your browser. You should receive a JSON response with database stats.

2. **Frontend Interactivity**:
   Open your Vercel URL (`https://your-app.vercel.app`), try searching courses, asking an AI question, or clicking **Syllabus Queries**.
