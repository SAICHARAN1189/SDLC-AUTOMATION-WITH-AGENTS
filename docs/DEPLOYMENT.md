# Production Deployment Guide

## 1. Architecture Deployment Overview

SDLC Nexus is built as a decoupled, cloud-native system:

- **Frontend**: Single Page Application built with React 19 + Vite + Tailwind CSS. Deployed to Vercel, Netlify, or AWS CloudFront/S3.
- **Backend**: Flask WSGI application managed by Gunicorn, deployed to AWS ECS, Google Cloud Run, Render, or any Linux VM.
- **Database & Auth**: Supabase managed PostgreSQL with connection pooling.
- **LLM Provider**: Groq API cloud inference.

```
[ CDN / Vercel ] ------> [ Browser (React 19 SPA) ]
                               │
                               │ HTTPS REST & SSE
                               ▼
            [ Gunicorn / Flask Backend (Python 3.13) ]
                    │                        │
       DATABASE_URL │                        │ GROQ_API_KEY
                    ▼                        ▼
        [ Supabase PostgreSQL ]         [ Groq Cloud LLM ]
```

## 2. Backend Gunicorn Service Setup

The backend includes a production-tuned `gunicorn.conf.py`:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start Gunicorn server with 4 worker threads
gunicorn -c gunicorn.conf.py "app:app"
```

## 3. Frontend Production Build

```bash
cd frontend
npm install
npm run build
```
Static output is generated in `frontend/dist/` ready to be served by Nginx or uploaded to any CDN.

## 4. Production Environment Checklist

| Variable | Environment | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | Backend | Supabase PostgreSQL pooled URI |
| `GROQ_API_KEY` | Backend | Production Groq API key |
| `SUPABASE_URL` | Backend + Frontend | Supabase project endpoint |
| `SUPABASE_ANON_KEY` | Backend + Frontend | Public client anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend ONLY | Secret service role key (never expose to client) |
| `SECRET_KEY` | Backend | Flask session encryption secret |
| `DEMO_MODE` | Backend | Set to `false` for live Groq inference |
| `CORS_ORIGINS` | Backend | Production frontend URL (e.g. `https://nexus.yourcompany.com`) |
