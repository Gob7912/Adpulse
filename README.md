# AdPulse 📊

**English** | [Русский](README.ru.md)

> **AdPulse** is a self-hosted web platform designed for automated daily delivery of **Meta (Facebook & Instagram) Ads** performance reports directly to **Telegram** (private chats, group channels, forum topics) and **Google Sheets**.
>
> A completely free, open-source alternative to proprietary SaaS reporting tools with no third-party branding or "Sent via..." footers.

---

## ⚡ Key Features

- **Derived metrics (CPC, CPM, CTR, cost per result) are computed from summed spend and counts, not averaged across campaigns; period deltas are computed from the underlying components.**
  - Additive metrics are summed across campaigns (`spend`, `impressions`, `clicks`, `leads`, `messages`, `calls`...).
  - Efficiency ratios (`CTR`, `CPC`, `CPM`, `CPP`, `CPL`, `Cost per DM`, `ROAS`) are calculated from totals without ratio averaging.
  - Deduplicated `reach` is fetched at the ad-account level with campaign filtering.
  - Unrecorded or unsupported metrics display localized `"N/A"` instead of zero values.
- **Period-over-Period Comparison**:
  - Sends a separate, beautifully structured Telegram message comparing current vs. previous period grouped by blocks (*General*, *Efficiency*, *Conversions & Cost*).
  - Clear delta badges with polarity indicators (green for positive conversion / lower cost, red for decreased results, neutral for spend/impressions).
  - Rounding rule: `.5` rounds away from zero (`−12.5% → −13%`, `+12.5% → +13%`), sub-1% deltas show one decimal place (`+0.3%`, `−0.5%`), `= 0%` strictly on exact equality.
  - Rows with missing data in both periods are automatically suppressed.
- **Snapshot Retention & Concurrency Protection**:
  - Raw Meta API snapshots are stored with `fetched_at` and attribution settings, automatically pruned after 90 days by daily worker cleanup while preserving historical metrics and message IDs.
  - PostgreSQL partial unique index prevents concurrent duplicate runs for the same period.
- **Final Data Delay Buffer**:
  - Meta recalculates conversion attribution and late impressions for several hours after midnight. AdPulse enforces a configurable delay buffer (default 6 hours) past the period end in the account's timezone before sending scheduled runs.
- **5-Step Report Wizard**:
  1. **Platform & Destinations**: Meta Ads source with multi-select delivery (Telegram, Google Sheets, or both).
  2. **Campaign Scope**: Ad account selection, flexible campaign targeting (all campaigns, filter by objectives/names, or specific campaigns).
  3. **Metrics Selection**: 4 curated templates (*Daily Pulse*, *Lead Generation*, *Direct Messages*, *Brand Awareness*) with custom icons, 24 selectable metrics, custom aliases, and real-time live preview.
  4. **Schedule & Timezones**: Daily, weekly, or monthly delivery with timezone conversion (account timezone vs. sender timezone).
  5. **Connection & Testing**: Deep-link one-click Telegram bot binding, Google Sheets verification with dynamic tab discovery, and instant test report trigger.
- **Multi-Tenant Security & Isolation**:
  - User registration & authentication with Argon2id password hashing and brute-force rate limiting.
  - Strict data isolation: every query is scoped by `user_id`.
  - Meta access tokens are encrypted at rest using AES-128/256 (Fernet). Tokens are never logged or exposed to the frontend.
  - Full "Delete Account and Data" cascade cleanup.
- **Modern UI & Localization**:
  - English, Russian (default), and Uzbek localization.
  - Dark mode by default with light mode toggle.
  - Monospace JetBrains Mono font styling and clean Lucide iconography.

---

## 🛠 Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 16.
- **Scheduler & Worker**: Background worker with persistent DB-backed job scheduling, preventing duplicate runs upon restart.
- **Telegram Bot**: `aiogram 3` (long-polling by default, optional webhook).
- **Google Sheets**: Google API Client v4 with Google Service Account support.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide icons.
- **Deployment**: Docker Compose (`api`, `worker`, `db`, `web`).

---

## 🚀 Quick Start (One-Command Deploy)

**Requirements**: Docker and Docker Compose (Linux / Debian VM, 2 vCPU, 4–8 GB RAM).

```bash
# 1. Clone the repository
git clone https://github.com/Gob7912/Adpulse.git adpulse
cd adpulse

# 2. Copy and configure environment variables
cp .env.example .env

# 3. Launch all containers
docker compose up -d --build
```

Once started, the application is accessible at:
- **Web Interface**: `http://<your-server-ip>/` (port 80)
- **Interactive API Docs (Swagger)**: `http://<your-server-ip>:8000/docs`

---

## 🔑 Setup & Configuration Guide

### 1. Telegram Bot Setup (@BotFather)
1. In Telegram, open a chat with [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow instructions:
   - Enter a display name (e.g. `AdPulse Reporter`).
   - Choose a username ending in `bot` (e.g. `MyCompanyAdPulseBot`).
3. Copy the HTTP API token provided by BotFather.
4. Add to your `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   TELEGRAM_BOT_USERNAME=MyCompanyAdPulseBot
   ```
5. *(Recommended)* In `@BotFather`, enable group support: send `/setprivacy` → select your bot → choose `Disable` (so the bot can receive `/link` commands in group chats).

### 2. Google Sheets Setup (Service Account)
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (e.g. `adpulse-reports`).
3. Under **APIs & Services → Library**, search for and enable **Google Sheets API**.
4. Navigate to **IAM & Admin → Service Accounts** and click **Create Service Account**.
5. Select the created account → open **Keys** tab → **Add Key** → **Create new key** (JSON).
6. In your `.env`, set:
   ```env
   GOOGLE_SERVICE_ACCOUNT_EMAIL=adpulse-service@adpulse-reports.iam.gserviceaccount.com
   GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
   ```
7. When connecting Google Sheets in Step 5 of the wizard, share your spreadsheet with the service account email and grant **Editor** permissions.

### 3. Meta Marketing API Token (System User Token)
1. Open [Meta Business Settings](https://business.facebook.com/settings).
2. Go to **Users → System Users** and click **Add**.
3. Name the user (e.g. `AdPulse System`) and set the role to **Admin**.
4. Click **Assign Assets**, select your **Ad Account**, and enable **View Performance (`ads_read`)** or **Manage Campaigns**.
5. Click **Generate New Token**:
   - Select your Meta App.
   - Token expiration: **Never**.
   - Check permission: `ads_read`.
6. Copy the token and paste it into Step 2 of the AdPulse wizard.

---

## 🧪 Testing & Linting

Production Docker images for `api` and `worker` install runtime dependencies from `requirements.txt`. Test and developer dependencies (`aiosqlite`, `ruff`) are isolated in `backend/requirements-dev.txt`.

### Local Execution:

```bash
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -v
ruff check .
```

### Docker Execution:

```bash
docker compose run --rm -v "$(pwd)/backend":/app -w /app api sh -c "pip install -r requirements-dev.txt && PYTHONPATH=. pytest -v && ruff check ."
```

Automated test suite covers:
- Metric math and zero-division resilience without ratio averaging.
- Final data delay buffer (6h) with account timezone handling.
- Meta API client mocking, pagination, and Error 190 (Token Expired) handling.
- Frozen Ads Manager golden fixtures and attribution parity verification.
- PostgreSQL partial unique index concurrency protection and duplicate defense.
- Sub-1% delta formatting, exact zero rules, and round-away-from-zero logic.
- Telegram deep-link sanitization, topic/thread delivery, and error alerts.
- Dynamic Google Sheets tab discovery and numeric cell formatting.
- User data isolation and end-to-end report wizard workflows.
- Report editing, account switching, and destination restoration edge cases.

---

## 📁 Repository Structure

```
adpulse/
├── DECISIONS.md              # Architectural decisions & Meta API mappings
├── docker-compose.yml        # Docker compose configuration (4 containers)
├── .env.example              # Environment variables template
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers (auth, meta, reports, destinations, history)
│   │   ├── models/           # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/          # Pydantic v2 schemas
│   │   ├── services/         # MetaClient, ReportEngine, TelegramBot, SheetsService, Scheduler
│   │   ├── config.py         # App configuration & Graph API versioning
│   │   ├── database.py       # Async engine & session factories
│   │   └── security.py       # Argon2id, JWT, Fernet AES token encryption
│   ├── alembic/              # Database migrations
│   ├── worker.py             # Scheduler & bot polling daemon
│   └── tests/                # Automated unit & integration tests
└── frontend/
    ├── src/
    │   ├── components/       # TopBar, WizardStepper, PreviewBubble
    │   ├── context/          # AuthContext, ThemeContext, LanguageContext
    │   ├── i18n/             # Translations (ru, uz, en)
    │   ├── pages/            # WizardPage, DashboardPage, HistoryPage, LandingPage
    │   ├── utils/            # Report icon helpers
    │   └── services/         # ApiClient
    └── package.json
```

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
