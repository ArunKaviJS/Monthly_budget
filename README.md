# Monthly Budget Calculator

**Offline, rule-based, zero-cost** monthly expense tracker.
No AI/LLM/ML APIs. No paid services. Everything is free and open-source.

## 📋 What It Does

Type one natural line about money spent:
```
tea 20
morning coffee and bajji 45
petrol 500
lunch meals hotel 120
movie ticket 250 with friends
apple grapes 180
bought a phone charger 399
paid 200                        ← goes to OTHERS (unclear)
```

The Python backend parses each line into **amount, intent, description, date** using a deterministic keyword + fuzzy matching engine. The app shows **intent-wise totals** for the month.

## 🏗 Architecture

```
┌─────────────────────────┐     HTTP/JSON     ┌──────────────────┐
│   React Native (Expo)   │ ◄──────────────► │  FastAPI Backend  │
│   Mobile App (Android)  │                   │  + MongoDB Atlas  │
└─────────────────────────┘                   └──────────────────┘
```

**Backend**: Python FastAPI + MongoDB (Atlas), JWT sign-in, hosted on Vercel  
**Frontend**: React Native + Expo SDK 57 + expo-router  
**Intent Engine**: Keyword dictionary + regex + difflib fuzzy matching  
**Currency**: INR (₹), Indian number formatting  
**Database**: MongoDB Atlas — every document carries a `user_id`, so each person's books, expenses, budgets and learned keywords are private to their account

## 🗂 File Tree

```
Monthly_budget/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point
│   │   ├── database.py          # MongoDB connection + indexes
│   │   ├── security.py          # password hashing, JWT, current-user check
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── crud.py              # Database operations
│   │   ├── intent_config.py     # Intent definitions, keywords, thresholds
│   │   ├── intent_engine.py     # Deterministic NLP pipeline
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── expenses.py      # CRUD endpoints
│   │       ├── summary.py       # Monthly/daily summaries
│   │       ├── budgets.py       # Budget limits
│   │       ├── intents.py       # Intent metadata + learned keywords
│   │       ├── preview.py       # Live classification preview
│   │       └── export.py        # CSV/JSON export
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_intent_engine.py  # 121 test cases
│   ├── requirements.txt
│   └── Dockerfile
├── mobile/
│   ├── app/
│   │   ├── _layout.tsx          # Root stack layout
│   │   ├── (tabs)/
│   │   │   ├── _layout.tsx      # Tab navigator
│   │   │   ├── index.tsx        # Home screen
│   │   │   ├── summary.tsx      # Summary screen
│   │   │   └── settings.tsx     # Settings screen
│   │   └── detail/
│   │       └── [intent].tsx     # Intent detail screen
│   ├── src/
│   │   ├── api.ts               # API client with offline queue
│   │   ├── types.ts             # TypeScript types
│   │   ├── helpers.ts           # Formatting utilities
│   │   └── theme.ts             # Design tokens
│   ├── assets/                  # App icons
│   ├── app.json                 # Expo config
│   ├── eas.json                 # EAS Build config
│   ├── package.json
│   ├── tsconfig.json
│   └── index.ts                 # Entry point
└── README.md
```

## 📦 Intents (13 + others)

| Intent | Emoji | Example Keywords |
|--------|-------|-----------------|
| food | 🍛 | meals, lunch, biryani, swiggy, saapadu, thali |
| tea_snacks | ☕ | tea, coffee, bajji, samosa, cool drink, ice cream |
| petrol | ⛽ | petrol, diesel, fuel, bunk, full tank, adichen |
| movie | 🎬 | movie, cinema, ticket, pvr, netflix, padam |
| fruits_diet | 🍎 | fruits, apple, banana, protein, dry fruits, oats |
| transport | 🚗 | uber, ola, auto, bus, train, metro, parking |
| bills_recharge | 📱 | bill, recharge, electricity, wifi, jio, emi |
| medical | 💊 | medicine, doctor, hospital, pharmacy, tablet |
| grooming | 💈 | haircut, salon, spa, barber, laundry |
| rent | 🏠 | rent, hostel, pg, lodge, deposit |
| education | 📚 | book, course, tuition, fees, coaching |
| grocery | 🛒 | grocery, vegetables, onion, milk, bigbasket |
| purchase | 🛍️ | bought, buy, amazon, flipkart, shopping |
| others | 📦 | *Fallback for unclear/low-confidence inputs* |

## 🚀 Setup & Run

### Prerequisites
- Python 3.10+
- Node.js 18+
- Android phone with USB debugging (for testing) or Android Studio emulator

### A) Backend (Local Dev)

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements-dev.txt

# Create backend/.env (never commit it):
#   MONGO_URI=mongodb+srv://...      (your Atlas connection string)
#   MONGO_DB=budget_dev              (use a separate DB for local work)
#   JWT_SECRET=<long random string>

# Run tests (in-memory fake MongoDB — never touches Atlas)
python -m pytest tests/ -v

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is now at `http://YOUR_LAN_IP:8000`.
API docs at `http://YOUR_LAN_IP:8000/docs`.

**⚠️ Windows Firewall**: Allow Python through the firewall for port 8000.
1. Open **Windows Defender Firewall** → **Advanced Settings**
2. **Inbound Rules** → **New Rule** → **Port** → TCP 8000 → Allow

Find your LAN IP:
```bash
ipconfig    # Look for IPv4 Address under Wi-Fi adapter (e.g. 192.168.1.5)
```

### B) Mobile App (Local Dev)

```bash
cd mobile

# Install dependencies
npm install

# Start Expo dev server
npx expo start
```

Scan the QR code with Expo Go on your phone, or press `a` for Android emulator.

**Set the API URL** in the app:
- Go to **Settings** tab → Set API URL to `http://YOUR_LAN_IP:8000`

### C) Free Cloud Hosting (so APK works anywhere)

#### Deploy Backend to Render.com (Free Tier)

1. Push the `backend/` folder to a GitHub repo
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Settings:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Deploy!
6. Copy the URL (e.g., `https://your-app.onrender.com`)

#### Set the API URL in the app:
Update the default in `mobile/src/api.ts`:
```typescript
const DEFAULT_API_URL = "https://your-app.onrender.com";
```

Or set it in the Settings screen after installing.

### D) Build APK

#### Option 1: EAS Build (Cloud, Free with Expo account)

```bash
cd mobile

# Install EAS CLI
npm install -g eas-cli

# Login to Expo
eas login

# Build APK
eas build -p android --profile preview
```

After the build completes, download the `.apk` from the link EAS provides.
Transfer it to your phone and install (enable "Install from unknown sources").

#### Option 2: Local Build (Fully Free, No Account)

```bash
cd mobile

# Generate native Android project
npx expo prebuild

# Build the APK
cd android
./gradlew assembleRelease
```

The APK will be at:
```
android/app/build/outputs/apk/release/app-release.apk
```

**Requirements for local build:**
- JDK 17+ installed
- Android SDK installed (via Android Studio)
- `ANDROID_HOME` environment variable set

## 🧪 Testing

```bash
cd backend
python -m pytest tests/test_intent_engine.py -v
```

Covers:
- All 13 intents + others fallback
- Tamil-English mixed input ("tea kadai la 20", "petrol adichen 500", "saapadu 80")
- Typos with fuzzy matching ("petrl", "cofee", "biriyni")
- Amount formats: plain number, rs, ₹, /-, k multiplier
- Date extraction: today, yesterday, ystd, DD/MM/YYYY
- Learned keywords override
- Priority order tie-breaking
- Description building

## 🧠 Self-Learning (No AI!)

When an entry lands in "others" or the user corrects an intent:
1. The app calls `PATCH /api/expenses/{id}` with the correct intent
2. The backend extracts meaningful tokens from the description
3. Tokens are saved to `learned_keywords` table with the correct intent
4. `classify()` loads learned keywords **FIRST** and scores them at **weight 2.0**
5. The user's own vocabulary always wins over built-in keywords

View learned keywords: `GET /api/keywords`  
Delete a keyword: `DELETE /api/keywords/{keyword}`  
Clear all: `DELETE /api/keywords`

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/expenses | Add expense (raw_text or manual) |
| GET | /api/expenses | List expenses (filter by month/intent) |
| GET | /api/expenses/{id} | Get single expense |
| PATCH | /api/expenses/{id} | Edit expense (triggers learning) |
| DELETE | /api/expenses/{id} | Delete expense |
| GET | /api/summary | Monthly intent-wise summary |
| GET | /api/summary/daily | Per-day totals |
| POST | /api/preview | Classify without saving |
| GET | /api/intents | Intent metadata |
| GET | /api/budgets | Budget limits |
| POST | /api/budgets | Set budget limit |
| GET | /api/keywords | Learned keywords |
| DELETE | /api/keywords/{kw} | Delete keyword |
| DELETE | /api/keywords | Clear all keywords |
| GET | /api/export/json | Export as JSON |
| GET | /api/export/csv | Export as CSV |
| GET | /api/health | Health check |

---

**No AI/LLM/paid service is used anywhere in this project.**
