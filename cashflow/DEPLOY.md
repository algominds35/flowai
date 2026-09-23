# Deploying CashFlow

## Part 1 — Deploy Backend to Railway

### Step 1: Create accounts
- [railway.app](https://railway.app) → sign up (free)
- [vercel.com](https://vercel.com) → sign up (free)

### Step 2: Push to GitHub (required by Railway and Vercel)
```bash
cd c:\Users\mrjoj\cashflow
git init   # if not already a repo
git add .
git commit -m "Initial CashFlow V1"
```
Then create a repo on GitHub and push:
```bash
git remote add origin https://github.com/YOUR_USERNAME/cashflow.git
git push -u origin main
```

### Step 3: Deploy backend on Railway
1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select your `cashflow` repo
3. Set **Root Directory** to `backend`
4. Railway will detect `railway.toml` and deploy automatically

### Step 4: Add PostgreSQL to Railway
1. In your Railway project → **+ New** → **Database** → **PostgreSQL**
2. Railway auto-sets `DATABASE_URL` in your backend service — nothing to do

### Step 5: Set environment variables in Railway
Go to your backend service → Variables tab → add these:

| Variable | Value |
|---|---|
| `SECRET_KEY` | Run `python -c "import secrets; print(secrets.token_hex(32))"` and paste result |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` |
| `ENVIRONMENT` | `production` |
| `FRONTEND_URL` | (set after Vercel deploy, e.g. `https://cashflow.vercel.app`) |

Your backend URL will be something like `https://cashflow-backend-production.up.railway.app`

---

## Part 2 — Deploy Frontend to Vercel

### Step 1: Import project
1. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
2. Select your `cashflow` repo
3. Set **Root Directory** to `frontend`
4. Vercel detects Next.js automatically

### Step 2: Set environment variable
In Vercel project settings → Environment Variables:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | Your Railway backend URL (e.g. `https://cashflow-backend-production.up.railway.app`) |

### Step 3: Deploy
Click Deploy. Your app will be live at `https://your-project.vercel.app`

### Step 4: Update CORS
Back in Railway → set `FRONTEND_URL` to your Vercel URL → Railway redeploys automatically.

---

## Integration API Keys (optional — app works with fixture data without these)

Add these to Railway environment variables when you have them:

| Key | Where to get it |
|---|---|
| `PLAID_CLIENT_ID` + `PLAID_SECRET` | [dashboard.plaid.com](https://dashboard.plaid.com) → Keys |
| `QBO_CLIENT_ID` + `QBO_CLIENT_SECRET` | [developer.intuit.com](https://developer.intuit.com) → Create App |
| `SHOPIFY_API_KEY` + `SHOPIFY_API_SECRET` | [partners.shopify.com](https://partners.shopify.com) → Apps |
| `AMAZON_CLIENT_ID` + `AMAZON_CLIENT_SECRET` + `AMAZON_REFRESH_TOKEN` | Seller Central → Developer Console → SP-API |

---

## Estimated costs
- Railway free tier: 500 hours/month (enough for testing; $5/mo for always-on)
- Vercel free tier: unlimited for personal projects
- **Total to start: $0**
