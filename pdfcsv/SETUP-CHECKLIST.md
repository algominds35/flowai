# 📋 Setup Checklist

Use this to track your setup progress.

## Prerequisites

- [ ] Python 3.12+ installed (`python --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Docker Desktop installed and running
- [ ] Git installed

## API Keys

- [ ] OpenAI account created
- [ ] OpenAI API key obtained (starts with `sk-proj-...`)
- [ ] $20 added to OpenAI account
- [ ] Stripe account created
- [ ] Stripe test keys obtained (`sk_test_...` and `pk_test_...`)
- [ ] QuickBooks Developer account created
- [ ] QuickBooks app created
- [ ] QuickBooks client ID and secret obtained

## Database Setup

- [ ] Docker Compose started (`docker-compose up -d`)
- [ ] PostgreSQL running (check with `docker ps`)
- [ ] Redis running (check with `docker ps`)

## Backend Setup

- [ ] Virtual environment created
- [ ] Virtual environment activated (see `(venv)` in terminal)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created from `env.example`
- [ ] API keys added to `.env`
- [ ] Backend starts without errors (`uvicorn app.main:app --reload`)
- [ ] Can access http://localhost:8000
- [ ] Can access API docs at http://localhost:8000/docs

## Frontend Setup

- [ ] Node modules installed (`npm install`)
- [ ] `.env.local` file created from `env.example`
- [ ] Frontend starts without errors (`npm run dev`)
- [ ] Can access http://localhost:3000
- [ ] Landing page loads correctly

## Testing

- [ ] Can sign up for new account
- [ ] Can log in
- [ ] Dashboard loads
- [ ] Can see user email in header
- [ ] Can log out
- [ ] Can log back in

## Common Issues Fixed

- [ ] No CORS errors in browser console
- [ ] No database connection errors
- [ ] Backend and frontend can communicate
- [ ] File upload area appears on dashboard

## Optional But Recommended

- [ ] Database GUI installed (pgAdmin or TablePlus)
- [ ] Can connect to database
- [ ] Can see `users`, `documents`, `transactions` tables
- [ ] VS Code installed with Python and TypeScript extensions
- [ ] Postman or Insomnia installed for API testing

---

## ✅ All Done?

If you checked everything above, you're ready to start building features!

**Next: Follow QUICKSTART.md to run the application**

---

## 🆘 Need Help?

### Backend won't start
1. Check Python version: `python --version`
2. Check venv is activated: Look for `(venv)` in terminal
3. Check database is running: `docker ps`
4. Check port 8000 is free

### Frontend won't start
1. Check Node version: `node --version`
2. Delete node_modules and reinstall: `rm -rf node_modules && npm install`
3. Check port 3000 is free

### Database connection failed
1. Check Docker is running: `docker ps`
2. Restart: `docker-compose down && docker-compose up -d`
3. Wait 10 seconds for startup
4. Check logs: `docker logs finflow-postgres`

### CORS errors
1. Make sure backend URL in frontend `.env.local` is `http://localhost:8000`
2. Make sure frontend URL in backend `.env` is `http://localhost:3000`
3. Restart both services

---

**Time to complete: 10-15 minutes** ⏱️
