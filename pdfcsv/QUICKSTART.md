# 🚀 Quick Start Guide - Get Running in 10 Minutes

## Step 1: Start Database (1 minute)

```bash
# In project root (pdfcsv folder)
docker-compose up -d
```

**Check it worked:**
```bash
docker ps
```
You should see `finflow-postgres` and `finflow-redis` running.

---

## Step 2: Setup Backend (3 minutes)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # Mac/Linux

# Install dependencies (this takes a minute)
pip install -r requirements.txt

# Setup environment file
copy env.example .env  # Windows
# OR
cp env.example .env    # Mac/Linux
```

**Edit `.env` file and add your API keys:**

You need at minimum:
```
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

For now, you can use fake values for Stripe and QuickBooks to test locally:
```
STRIPE_SECRET_KEY=sk_test_fake
STRIPE_PUBLISHABLE_KEY=pk_test_fake
QUICKBOOKS_CLIENT_ID=fake
QUICKBOOKS_CLIENT_SECRET=fake
```

**Start backend:**
```bash
# Make sure you're in /backend with venv activated
uvicorn app.main:app --reload
```

✅ Backend should be running at: http://localhost:8000

---

## Step 3: Setup Frontend (3 minutes)

**Open a NEW terminal** (keep backend running):

```bash
cd frontend

# Install dependencies
npm install

# Setup environment file
copy env.example .env.local  # Windows
# OR
cp env.example .env.local    # Mac/Linux

# Start frontend
npm run dev
```

✅ Frontend should be running at: http://localhost:3000

---

## Step 4: Test It! (3 minutes)

1. Open browser: **http://localhost:3000**
2. Click **"Sign Up"**
3. Enter any email/password (test@test.com / password123)
4. Click **"Create Account"**

You should be redirected to the dashboard! 🎉

---

## ✅ You're Ready!

**What's working right now:**
- ✅ User registration/login
- ✅ Dashboard
- ✅ File upload (stores locally)
- ✅ Database (PostgreSQL)

**What's NOT working yet (we'll build next):**
- ❌ OCR processing (Week 2)
- ❌ AI extraction (Week 3)
- ❌ Transaction table (Week 4)
- ❌ QuickBooks sync (Week 5)
- ❌ Billing (Week 6)

---

## 🐛 If Something Doesn't Work

### Backend error: "connection refused"
```bash
# Make sure Docker is running
docker ps

# Restart database
docker-compose down
docker-compose up -d
```

### Backend error: "module not found"
```bash
# Make sure venv is activated (you should see (venv) in terminal)
# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend error: "EADDRINUSE"
```bash
# Port 3000 is in use. Kill it:
# Windows: netstat -ano | findstr :3000 (then kill process ID)
# Mac/Linux: lsof -ti:3000 | xargs kill
```

### Can't access http://localhost:3000
- Check frontend terminal - is it running?
- Check backend terminal - is it running?
- Try: http://127.0.0.1:3000

---

## 📸 What You Should See

### Landing Page
![Beautiful landing page with "Stop Manually Importing Bank Statements"]

### Dashboard
![Clean dashboard with upload area and document list]

---

## ➡️ Next Steps

Once everything is running:

1. **Week 1 ✅ DONE** - You just completed this!
2. **Week 2** - Add OCR processing (Tesseract)
3. **Week 3** - Add GPT-4 extraction
4. **Week 4** - Build transaction review table
5. **Week 5** - QuickBooks integration
6. **Week 6** - Stripe billing & launch!

---

## 🎯 Current Status: MVP Foundation Complete

You have:
- ✅ Full authentication system
- ✅ Database models (User, Document, Transaction)
- ✅ API endpoints (REST API)
- ✅ Modern UI (Next.js + Tailwind)
- ✅ File upload capability
- ✅ Dashboard

**This is 15-20% of the final product.** We're ahead of schedule! 🚀

---

## 💡 Pro Tips

**Keep 3 terminals open:**
1. Backend: `cd backend && venv\Scripts\activate && uvicorn app.main:app --reload`
2. Frontend: `cd frontend && npm run dev`
3. General: For git, docker, etc.

**Check API docs:**
- Go to: http://localhost:8000/docs
- See all API endpoints with interactive testing!

**Database GUI (optional):**
- Install: https://www.pgadmin.org/
- Connect to: localhost:5432, user: finflow, password: finflow123

---

**🎉 Congratulations! You've built the foundation of a $1M SaaS product!**
