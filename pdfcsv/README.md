# FinFlow AI - Automated Bank Statement Processing

Upload bank statements → Extract transactions → Sync to QuickBooks automatically.

## 🚀 Tech Stack

### Backend
- **FastAPI** (Python 3.12)
- **PostgreSQL** (Database)
- **Redis** (Job queue)
- **Celery** (Background workers)
- **Tesseract** (Free OCR)
- **OpenAI GPT-4** (AI extraction)

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **Axios** (API client)

## 📋 Prerequisites

Install these before starting:

- **Python 3.12+**
- **Node.js 18+**
- **Docker Desktop** (for PostgreSQL & Redis)
- **Git**

## 🔧 Setup Instructions

### 1. Clone Repository

```bash
cd pdfcsv
```

### 2. Start Database (Docker)

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify they're running
docker ps
```

### 3. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env file
copy env.example .env  # Windows
# OR
cp env.example .env    # Mac/Linux

# Edit .env and add your API keys:
# - OPENAI_API_KEY
# - STRIPE_SECRET_KEY
# - QUICKBOOKS_CLIENT_ID
# - QUICKBOOKS_CLIENT_SECRET
```

### 4. Run Backend

```bash
# Make sure you're in /backend and venv is activated
uvicorn app.main:app --reload --port 8000
```

Backend will run at: **http://localhost:8000**

### 5. Setup Frontend

Open a **NEW terminal** (keep backend running):

```bash
cd frontend

# Install dependencies
npm install

# Copy env file
copy .env.example .env.local  # Windows
# OR
cp .env.example .env.local    # Mac/Linux
```

### 6. Run Frontend

```bash
# Make sure you're in /frontend
npm run dev
```

Frontend will run at: **http://localhost:3000**

## 🎯 Test the Application

1. **Open browser**: http://localhost:3000
2. **Click "Sign Up"**
3. **Create account** (use any email/password)
4. **You're in!** Try uploading a PDF

## 📂 Project Structure

```
pdfcsv/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── models/           # Database models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── core/             # Config, security, database
│   │   └── main.py           # FastAPI app
│   ├── requirements.txt
│   └── env.example
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Landing page
│   │   ├── login/            # Login page
│   │   ├── signup/           # Signup page
│   │   └── dashboard/        # Dashboard
│   ├── lib/
│   │   ├── api.ts            # API client
│   │   └── store.ts          # State management
│   └── package.json
│
└── docker-compose.yml        # PostgreSQL + Redis
```

## 🔑 Required API Keys

### OpenAI (Required)
1. Go to: https://platform.openai.com/api-keys
2. Create key
3. Add $20 credit
4. Add to `.env`: `OPENAI_API_KEY=sk-...`

### Stripe (Required)
1. Go to: https://stripe.com
2. Get test keys
3. Add to `.env`:
   - `STRIPE_SECRET_KEY=sk_test_...`
   - `STRIPE_PUBLISHABLE_KEY=pk_test_...`

### QuickBooks (Required)
1. Go to: https://developer.intuit.com
2. Create app
3. Add to `.env`:
   - `QUICKBOOKS_CLIENT_ID=...`
   - `QUICKBOOKS_CLIENT_SECRET=...`

## 🐛 Troubleshooting

### Database connection error
```bash
# Make sure Docker is running
docker ps

# Restart containers
docker-compose down
docker-compose up -d
```

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.12+

# Reinstall dependencies
pip install -r requirements.txt

# Check if port 8000 is free
# Windows: netstat -ano | findstr :8000
# Mac/Linux: lsof -i :8000
```

### Frontend won't start
```bash
# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check if port 3000 is free
```

### CORS errors
Make sure:
- Backend is running on port 8000
- Frontend is running on port 3000
- Both are running (check terminals)

## 📝 Next Steps

After basic setup works:

1. **Add OCR processing** (Week 2)
2. **Add GPT-4 extraction** (Week 3)
3. **Build transaction table** (Week 4)
4. **Integrate QuickBooks** (Week 5)
5. **Add Stripe billing** (Week 6)

## 🚀 Deployment

Coming soon! Will add instructions for:
- Vercel (Frontend)
- Railway (Backend)
- Production database

## 📖 Documentation

- Backend API: http://localhost:8000/docs (automatic FastAPI docs)
- Database models: See `/backend/app/models/`
- API endpoints: See `/backend/app/api/`

## 💰 Costs

**Development (local):**
- $0 - Everything runs locally

**Production:**
- OpenAI: ~$10-50/month
- Hosting: ~$10/month
- Database: ~$10/month
- **Total: $30-70/month**

## 🤝 Support

Having issues? Check:
1. All services are running (Docker, Backend, Frontend)
2. API keys are set in `.env` files
3. Ports 3000, 5432, 6379, 8000 are available

## 📄 License

MIT

---

**Built with ❤️ to automate bookkeeping**
