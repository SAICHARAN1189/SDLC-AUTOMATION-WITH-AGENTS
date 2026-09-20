# 🚀 Render Deployment Guide: Single Web Service Architecture

This document provides step-by-step instructions for deploying **SDLC Nexus** on **Render** as a single, unified Web Service where both the React 19 frontend and Flask backend are served from a single public URL.

---

## 🏗️ Architecture Overview

```
                          Internet / Browser
                                   │
                                   ▼ HTTPS
             ┌───────────────────────────────────────────┐
             │       Render Web Service (Single URL)     │
             │           https://<app>.onrender.com      │
             ├───────────────────────────────────────────┤
             │           Gunicorn WSGI Server            │
             │  (Worker: gthread · Threads: 8 · Port: $PORT) │
             ├─────────────────────────────┬─────────────┤
             │      Flask Backend API      │ React / Vite│
             │  • /api/... endpoints       │ Static App  │
             │  • /api/.../stream (SSE)    │ • /assets/* │
             │  • /health (Render probe)   │ • SPA routes│
             └─────────────┬───────────────┴─────────────┘
                           │
             ┌─────────────▼─────────────────────────────┐
             │            Cloud Infrastructure           │
             │  • Supabase PostgreSQL (DATABASE_URL)    │
             │  • Google Gemini 3.8 / 3.5 API            │
             │  • Groq GPT-OSS API                       │
             └───────────────────────────────────────────┘
```

---

## 📋 Render Service Settings

In your **Render Dashboard** (https://dashboard.render.com), create a new **Web Service** connected to your repository with the following configuration:

| Setting | Value |
| :--- | :--- |
| **Name** | `sdlc-nexus` |
| **Environment** | `Python` |
| **Region** | Any (e.g. *Oregon (US West)* or *Frankfurt (EU)*) |
| **Branch** | `main` |
| **Root Directory** | *(Leave empty - defaults to repository root)* |
| **Build Command** | `pip install -r backend/requirements.txt && cd frontend && npm install && npm run build && cd ..` |
| **Start Command** | `gunicorn -k gthread --threads 8 --workers 2 --timeout 120 --bind 0.0.0.0:$PORT "backend.app:create_app()"` |
| **Plan** | Free or Starter |
| **Health Check Path** | `/health` |

---

## 🔑 Required Environment Variables

Configure the following environment variables in the **Environment** tab of your Render Web Service:

### 1. Database & Persistence (Backend Only)
| Variable | Value / Description | Sensitive? |
| :--- | :--- | :--- |
| `DATABASE_URL` | Your Supabase connection string: `postgresql://postgres.[REF]:[PASS]@[HOST]:6543/postgres` | **Yes (Secret)** |

### 2. LLM Inference APIs (Backend Only)
| Variable | Value / Description | Sensitive? |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google AI Studio Gemini API Key (`AIza...`) | **Yes (Secret)** |
| `GROQ_API_KEY` | Groq Cloud API Key (`gsk_...`) | **Yes (Secret)** |
| `LLM_PROVIDER` | `gemini` (default) or `groq` | No |
| `GEMINI_MODEL` | `gemini-3.8-flash` | No |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | No |

### 3. Application Security & Runtime
| Variable | Value / Description | Sensitive? |
| :--- | :--- | :--- |
| `SECRET_KEY` | Random secret key (e.g. `openssl rand -hex 32`) | **Yes (Secret)** |
| `FLASK_ENV` | `production` | No |
| `DEMO_MODE` | `false` | No |
| `CORS_ORIGINS` | `*` (or your Render URL: `https://<your-app>.onrender.com`) | No |

> [!IMPORTANT]
> All secrets are backend-only. None of these variables are exposed to the client or baked into frontend JavaScript assets.

---

## 🛠️ How It Works Under The Hood

1. **Vite Build**: The build command installs frontend dependencies and executes `npm run build`, producing an optimized production bundle inside `frontend/dist/`.
2. **Flask SPA Handler**: Flask inspects requests:
   - Requests matching `/api/...` execute backend endpoints.
   - Requests matching `/health` execute the health check probe.
   - Real asset paths matching `/assets/...` are served with correct MIME types.
   - All other routes (e.g. `/projects`, `/artifacts`, `/security`) serve `frontend/dist/index.html`, allowing React Router to handle client-side navigation without returning 404 on page refresh.
3. **SSE & Gunicorn Concurrency**: Gunicorn uses `--worker-class gthread` with `--threads 8`, ensuring that long-lived Server-Sent Events (SSE) streaming connections do not block standard REST API requests.

---

## 🧪 Verification Checklist

After deploying to Render, verify your deployment:

- [ ] **Health Endpoint**: Visit `https://<your-app>.onrender.com/health` &rarr; Returns `{"backend": "healthy", "database": "healthy"}` (HTTP 200).
- [ ] **Frontend Loading**: Visit `https://<your-app>.onrender.com/` &rarr; Loads the SDLC Nexus UI directly.
- [ ] **SPA Route Refresh**: Navigate to `/projects` and refresh the page &rarr; Page reloads without 404.
- [ ] **Cluster Services**: Bottom-left sidebar displays green indicators (`LIVE`, `CONNECTED`, `READY`, `ACTIVE`).
- [ ] **API Calls**: Opening projects or running agents successfully executes against `/api/...`.
