# Deploying SARTHI (public demo)

Two services: the **Next.js frontend on Vercel** and the **FastAPI + LangGraph
backend on Render**. The frontend proxies `/api/agent/*` to the backend
(server-side), so the identity cookie stays first-party and there is no browser
CORS to configure.

> **Secrets rule:** API keys and the signing secret are entered *only* in the
> Render/Vercel dashboards. They are never committed and never printed.

Deploy the backend first (the frontend needs its URL).

## 1. Backend → Render

1. Push this repo to GitHub (already done).
2. Render Dashboard → **New → Blueprint** → select this repo. Render reads
   `render.yaml` and creates the `sarthi-backend` web service.
3. When prompted, set the secret env var **values**:
   - `NVIDIA_API_KEY` — your NVIDIA Build key.
   - `SARTHI_SECRET_KEY` — a long random string. Generate one with:
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`
     (this keeps anonymous identities stable across restarts).
   - `SARTHI_COOKIE_SECURE` is already set to `true` by the blueprint.
4. Deploy. When it's live, note the URL, e.g. `https://sarthi-backend.onrender.com`.
5. Sanity check: open `https://<your-backend>/health` → should return `{"status":"ok",...}`.

## 2. Frontend → Vercel

From `sarthi-web/` (after `vercel login`):

```bash
cd sarthi-web
vercel link          # create/link the project
vercel env add SARTHI_BACKEND_URL production   # paste the Render URL
vercel --prod        # deploy
```

Or via the dashboard: **New Project → import repo → Root Directory = `sarthi-web`**,
add env var `SARTHI_BACKEND_URL = https://<your-backend>.onrender.com`, deploy.

## 3. Verify

- Open the Vercel URL, go to **/chat**, send a message — the reply should stream.
- Check **/loan** and **/apply** load and compute/submit.
- First backend hit after idle is slow (Render free cold start ~30–60s).

## Notes & limits (free tier)

- **Ephemeral storage:** long-term memory, SOPs, and loan drafts reset when the
  Render service restarts/redeploys. Add a paid persistent disk for durability.
- **NVIDIA free tier rate-limits (429)** under load — fine for a demo, not for
  real traffic.
- **No account login yet:** identity is an anonymous signed cookie (no PII).
  Add real accounts before treating this as more than a demo.
