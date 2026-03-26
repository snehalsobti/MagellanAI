# MagellanAI — Deployment & Authentication Setup Guide

This document contains every manual step you need to perform on external platforms
to deploy MagellanAI with real Google OAuth and Supabase-backed history.

> **Do these steps after all code is pushed to GitHub `main`.**
> Steps are ordered so earlier steps provide values needed by later ones.

---

## Overview of the architecture

```
Browser  ──→  Vercel (SvelteKit frontend)  ──→  Render (FastAPI backend)
                       │                                │
                       └──────────────────────────────→ Supabase (auth + history DB)
```

- **Vercel**: SvelteKit frontend (auto-deploys on every `git push main`)
- **Render**: Python FastAPI backend (auto-deploys on every `git push main`)
- **Supabase**: Google OAuth provider + `generation_history` table + anonymous sign-ins

---

## Step 1 — Create a Supabase project

1. Go to [https://supabase.com](https://supabase.com) and sign in / create an account.
2. Click **New project**.
3. Fill in:
   - **Organisation**: your org (or create one)
   - **Name**: `magellanai` (or similar)
   - **Database password**: generate a strong password and save it somewhere safe
   - **Region**: choose the region nearest to your users (e.g. `us-east-1`)
4. Click **Create new project** and wait ~2 minutes for provisioning.
5. Once provisioned, go to **Project Settings → API**.
   - Copy **Project URL** → this is `PUBLIC_SUPABASE_URL`
   - Copy **anon / public** key → this is `PUBLIC_SUPABASE_ANON_KEY`
   - Keep the **service_role** key private — you will NOT need it for this project.

---

## Step 2 — Enable anonymous sign-ins in Supabase

1. In the Supabase dashboard, go to **Authentication → Providers → Anonymous**.
2. Toggle **Enable anonymous sign-ins** to ON.
3. Under **Clean up anonymous users**, enable **Auto clean up** and set the period to
   **30 days**. This prevents orphaned guest records from accumulating.
4. Click **Save**.

---

## Step 3 — Set up Google OAuth in Supabase

### 3a. Create OAuth credentials in Google Cloud Console

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com).
2. Create a new project (or select an existing one).
3. In the left menu, navigate to **APIs & Services → OAuth consent screen**.
4. Set **User type** to **External**, click **Create**.
5. Fill in:
   - **App name**: `MagellanAI`
   - **User support email**: your email
   - **Authorised domains**: add `supabase.co`
   - **Developer contact email**: your email
6. Click **Save and Continue** through Scopes (no extra scopes needed) and Test users.
7. Navigate to **APIs & Services → Credentials**.
8. Click **+ Create Credentials → OAuth client ID**.
9. Set **Application type** to **Web application**.
10. Under **Authorised redirect URIs**, add:
    ```
    https://YOUR_PROJECT_ID.supabase.co/auth/v1/callback
    ```
    Replace `YOUR_PROJECT_ID` with the ID from your Supabase project URL
    (e.g. if URL is `https://abcdefgh.supabase.co` then ID is `abcdefgh`).
11. Click **Create**.
12. Copy the **Client ID** and **Client secret** — you will need both next.

### 3b. Add Google provider to Supabase

1. In Supabase dashboard, go to **Authentication → Providers → Google**.
2. Toggle **Enable Google provider** to ON.
3. Paste the **Client ID** and **Client secret** from step 3a.
4. The **Callback URL (for OAuth)** shown in Supabase is what you pasted in step 3a.10
   (confirm they match).
5. Click **Save**.

---

## Step 4 — Create the generation_history table in Supabase

1. In the Supabase dashboard, go to **SQL Editor**.
2. Paste and run the following SQL:

```sql
-- History table for persisting generation sessions per user
CREATE TABLE IF NOT EXISTS generation_history (
    id                   UUID         DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id              UUID         REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    iteration            INTEGER      NOT NULL,
    profile              JSONB        NOT NULL,
    feedback             JSONB        NOT NULL DEFAULT '{}',
    original_preferences JSONB        NOT NULL DEFAULT '[]',
    year12_choice        TEXT,
    created_at           TIMESTAMPTZ  DEFAULT NOW()
);

-- Index for fast per-user queries ordered by recency
CREATE INDEX IF NOT EXISTS idx_generation_history_user ON generation_history(user_id, created_at DESC);

-- Row Level Security: users can only see and modify their own rows
ALTER TABLE generation_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_select_own" ON generation_history
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "users_insert_own" ON generation_history
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "users_delete_own" ON generation_history
    FOR DELETE USING (auth.uid() = user_id);
```

3. Click **Run**. You should see "Success. No rows returned."

---

## Step 5 — Deploy the backend to Render

> **Note:** Render may not auto-detect `render.yaml`. Configure the service manually
> as described below — it takes 2 minutes and is the most reliable approach.

1. Go to [https://render.com](https://render.com) and sign in / create an account.
2. Click **New → Web Service**.
3. Connect your GitHub account and select the **MagellanAI** repository.
4. If Render shows a blueprint/render.yaml option, skip it. Instead, choose
   **"Configure manually"** and fill in:
   - **Name**: `magellanai-backend`
   - **Branch**: `main`
   - **Runtime**: **Python 3**
   - **Root Directory**: *(leave blank — the repo root is correct)*
   - **Build Command**:
     ```
     pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && pip install -r requirements_api.txt
     ```
   - **Start Command**: `python api_server.py`
   - **Instance Type**: **Free** (or Starter $7/mo to avoid cold starts)
5. Under **Environment Variables**, add **all of these before clicking Deploy**:

   | Key | Value |
   |-----|-------|
   | `OPENAI_API_KEY` | your OpenAI key (starts with `sk-`) |
   | `RAG_OPENAI_MODEL` | `gpt-4.1` |
   | `PYTHON_VERSION` | `3.11.10` |
   | `MAGELLAN_ALLOWED_ORIGINS` | *(leave blank for now; fill in after Step 6)* |

7. **Do NOT add a persistent disk.** `data/magellan.db` is already committed to the
   git repository. Render uses it directly from the build checkout. A mounted disk
   would override (and hide) that file with an empty directory — exactly the wrong
   thing. If the service currently has a disk attached, remove it in
   **Service → Settings → Disks → Delete disk** before redeploying.
8. Click **Create Web Service**.
9. Wait for the deploy to succeed. The **first build takes 5–10 minutes** (downloading
   OR-Tools, PyTorch, and sentence-transformers). Subsequent deploys are faster.
   > **No database initialisation is needed.** The committed `data/magellan.db` contains
   > the full course catalogue. The server reads it directly — no shell commands required.
10. Copy the **public URL** Render shows (e.g. `https://magellanai-backend.onrender.com`).
    You will need this in Step 6.

---

## Step 6 — Deploy the frontend to Vercel

1. Go to [https://vercel.com](https://vercel.com) and sign in / create an account.
2. Click **Add New → Project**.
3. Import your **MagellanAI** GitHub repository.
4. Vercel auto-detects SvelteKit. Confirm:
   - **Framework Preset**: SvelteKit
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `.svelte-kit/output` (auto-detected)
5. Under **Environment Variables**, add:

   | Key | Value |
   |-----|-------|
   | `PUBLIC_API_BASE_URL` | `https://magellanai-backend.onrender.com` *(from Step 5.8)* |
   | `PUBLIC_SUPABASE_URL` | `https://YOUR_PROJECT_ID.supabase.co` *(from Step 1.5)* |
   | `PUBLIC_SUPABASE_ANON_KEY` | your Supabase anon/public key *(from Step 1.5)* |

6. Click **Deploy**.
7. Once deployed, Vercel shows a URL (e.g. `https://magellanai.vercel.app`).
   Copy this URL — you need it for the next two steps.

---

## Step 7 — Configure authorised redirect URIs for Google OAuth

Now that you have the live Vercel URL, update Google Cloud Console:

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com).
2. Navigate to **APIs & Services → Credentials → your OAuth client**.
3. Under **Authorised JavaScript origins**, add:
   ```
   https://magellanai.vercel.app
   ```
4. Under **Authorised redirect URIs**, the Supabase callback you added in Step 3a.10
   is already correct and does not change. No new entry needed here.
5. Click **Save**.

---

## Step 8 — Add the Vercel URL to Supabase allowed redirect URLs

1. In the Supabase dashboard, go to **Authentication → URL Configuration**.
2. Under **Redirect URLs**, add:
   ```
   https://magellanai.vercel.app/auth/callback
   ```
   (Also add `http://localhost:5173/auth/callback` if not already present for local dev.)
3. Click **Save**.

---

## Step 9 — Update Render CORS to allow the Vercel frontend

1. In the Render dashboard, go to your **magellanai-backend** service → **Environment**.
2. Set:

   | Key | Value |
   |-----|-------|
   | `MAGELLAN_ALLOWED_ORIGINS` | `https://magellanai.vercel.app,http://localhost:5173` |

3. Click **Save** — Render will redeploy automatically.

---

## Step 10 — Verify everything works

### Smoke tests (do these in order)

1. **Backend health**: visit `https://magellanai-backend.onrender.com/health` — should
   return `{"status":"healthy","data_loaded":true,...}`.
   > If `data_loaded` is `false`, the DB has not been initialised yet — see Step 5 note.

2. **Frontend loads**: visit `https://magellanai.vercel.app` — should redirect to `/signin`.

3. **Guest sign-in**: click **Continue as Guest** — should navigate to `/options` in under 2 s.

4. **Generate profile**: go to Generate, enter interests, generate a profile.
   > The very first generate request after a fresh deploy (or after Render's free-tier
   > cold start) will take 1–3 minutes — the sentence-transformer model loads and caches
   > embeddings on first use. All subsequent requests are fast.
   
   Refresh the page — history should be restored (same browser session).

5. **Google OAuth**: click **Sign in with Google** on the sign-in page:
   - Browser should redirect to Google's consent screen.
   - After granting permission, browser should return to `https://magellanai.vercel.app/options`.
   - Profile generation and history should work exactly as before.

6. **Sign out**: click **Sign out** on any page — should return to `/signin`.

### First-request cold-start (Render free tier)

If the backend hasn't received a request in >15 minutes, the first request to
`/generate-profile` will trigger a Render cold start and may take 30–60 seconds. This
is normal on the free tier. A loading spinner is shown to the user during this time.
Upgrade to Render's **Starter** plan ($7/month) to eliminate cold starts entirely.

---

## Local development (always works, no cloud required)

Local dev requires only a real Supabase project (free tier is sufficient). Google OAuth
also works locally because Supabase proxies the callback through its own server.

1. Ensure `frontend/.env` contains your real Supabase values:
   ```
   PUBLIC_API_BASE_URL=http://localhost:8000
   PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
   PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
   ```
2. Ensure `http://localhost:5173/auth/callback` is in Supabase **Redirect URLs**
   (Authentication → URL Configuration).
3. Start backend: `./start_backend.sh`
4. Start frontend: `./start_frontend.sh`

---

## Environment variable reference

### Backend (root `.env` / Render dashboard)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4 reranking |
| `RAG_OPENAI_MODEL` | No (default `gpt-4`) | Model name for RAG reranking |
| `MAGELLAN_ALLOWED_ORIGINS` | No (defaults to localhost) | Comma-separated list of allowed CORS origins |

### Frontend (`frontend/.env` / Vercel environment variables)

| Variable | Required | Description |
|----------|----------|-------------|
| `PUBLIC_API_BASE_URL` | Yes | FastAPI backend URL |
| `PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon/public key (safe to expose) |

---

## Manual testing checklist (cannot be automated)

- [ ] Google OAuth full browser round-trip: sign-in → Google consent → redirect back → `/options`
- [ ] Guest session: sign in as guest → generate profile → refresh page → history restored
- [ ] Google user: sign in → generate → refresh → history still present (Supabase-backed)
- [ ] Sign out clears session: click sign out → can no longer access `/options` without signing in again
- [ ] Google user in new incognito window: can see same history (tied to Google account)
- [ ] Guest in new incognito window: no history (new anonymous user)
- [ ] Generate Fresh: clears history from Supabase; new profile starts fresh
- [ ] All existing features unchanged: CP-SAT generation, constraint verification, feedback loop (LOCK/EXCLUDE/LIKE/DISLIKE), honor report, slot editor, course details modal, course search, requirements page
- [ ] Rate limit (429): rapid-fire 9+ requests to `/generate-profile` — should receive a 429 response on the 9th
- [ ] Render cold-start: if backend idle >15 min, first generation request takes 30–60 s but succeeds
- [ ] Vercel production build: push a change to `main` → Vercel auto-deploys → verify deploy succeeded in Vercel dashboard
