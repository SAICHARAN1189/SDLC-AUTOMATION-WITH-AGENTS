# Supabase Integration Guide

## 1. Overview

SDLC Nexus leverages Supabase as its primary cloud data and security tier:
- **Authentication**: User identity, JWT issuance, session management, and RBAC authorization.
- **PostgreSQL Database**: Persistent storage for projects, pipeline runs, workflow events, agent executions, security findings, test results, review decisions, and model comparisons.
- **Storage Buckets**: Storage for large exported artifacts (e.g. full project zip archives, multi-file code snapshots).

```
┌────────────────────────────────────────────────────────┐
│                        SUPABASE                        │
│                                                        │
│  ┌──────────────────┐  ┌────────────────────────────┐  │
│  │  Supabase Auth   │  │   PostgreSQL (DATABASE_URL)│  │
│  │  - User Accounts │  │   - Projects               │  │
│  │  - Verified JWTs │  │   - Pipeline Runs          │  │
│  │  - RLS Policies  │  │   - Workflow Events        │  │
│  └──────────────────┘  │   - Security Findings      │  │
│                        │   - Test Results           │  │
│  ┌──────────────────┐  │   - Review Results         │  │
│  │ Supabase Storage │  │   - Model Comparisons      │  │
│  │ - sdlc-artifacts │  └────────────────────────────┘  │
│  └──────────────────┘                                  │
└────────────────────────────────────────────────────────┘
```

## 2. Environment Configuration

In `.env`:
```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-backend-only-service-role-key
SUPABASE_STORAGE_BUCKET=sdlc-artifacts

# Database Connection (Direct or Pooled Connection String)
DATABASE_URL=postgresql://postgres.your-project:your-password@aws-0-region.pooler.supabase.com:6543/postgres
```

## 3. Strict Credential Isolation Rule

- `SUPABASE_ANON_KEY` is public and safe to use in frontend client code (`frontend/src/lib/supabase.ts`).
- `SUPABASE_SERVICE_ROLE_KEY` is **strictly backend-only**. It is loaded only by `backend/config/settings.py` and never injected into client bundles or returned in API responses.
