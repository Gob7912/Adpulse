# DECISIONS.md - Architectural & Design Decisions for AdPulse

This document records sensible defaults, design decisions, and Meta Marketing API mappings chosen for **AdPulse** (self-hosted automated Meta Ads reporting SaaS alternative).

---

## 1. Application Name & Identity
- **Working Name**: `AdPulse` (configured in a single constant `APP_NAME = "AdPulse"` across backend and frontend).
- **Branding**: No third-party "Sent via ..." footers. All reports generated cleanly and autonomously.

---

## 2. Authentication & Security
- **Password Hashing**: Argon2id via `passlib[argon2]`.
- **Session / Token Handling**: Dual support for HTTP-only cookies (`adpulse_token`) and `Authorization: Bearer <token>` headers.
- **Login Rate Limiting**: In-memory token bucket rate limiter (5 failed attempts per 5 minutes per IP/email) with standard `429 Too Many Requests`.
- **Meta Token Encryption**: AES-128/256 symmetric encryption via `cryptography.fernet.Fernet` at rest. The key is supplied via `ENCRYPTION_KEY`. Tokens are never logged and never sent back to the frontend (only profile metadata like name, ID, and connection status).
- **Registration Toggle**: `ALLOW_REGISTRATION=true|false` to control self-service registration.
- **Account Deletion**: Complete cascade deletion of all user data, reports, run histories, and stored Meta connections.

---

## 3. Database & Persistence
- **ORM & Migrations**: SQLAlchemy 2.0 (async + sync compatible) and Alembic migrations.
- **DBMS**: PostgreSQL 16 (production) with SQLite support for lightweight unit testing.
- **Job Scheduling**: Stored in PostgreSQL with `next_run_at`, run state, and optimistic locking to prevent duplicate runs across container restarts or multiple worker instances.

---

## 4. Meta Marketing API & Metrics Mapping
- **Pinned Graph API Version**: `v21.0` (`https://graph.facebook.com/v21.0`).
- **Token Verification**: Calls `GET /me` (retrieves name and id) and `GET /me/adaccounts?fields=id,name,account_id,currency,timezone_name,account_status`.
- **Deduplication of Reach & Frequency**:
  - Reach cannot be summed across campaigns without overcounting unique users.
  - When querying Meta API, AdPulse requests account-level insights filtered by campaign IDs:
    `level=account&filtering=[{"field":"campaign.id","operator":"IN","value":[<campaign_ids>]}]`.
    This delegates cross-campaign reach deduplication to Meta's data engine.
- **Strict Ratio Calculation (No Averaging)**:
  - Additive metrics (`spend`, `impressions`, `clicks`, `inline_link_clicks`, `leads`, `messages`, `calls`, `purchases`) are summed.
  - All rates and costs are calculated strictly from the aggregate sums:
    - `CTR` = $\frac{\text{clicks}}{\text{impressions}} \times 100\%$
    - `CTR (link)` = $\frac{\text{inline\_link\_clicks}}{\text{impressions}} \times 100\%$
    - `CPC` = $\frac{\text{spend}}{\text{clicks}}$
    - `CPM` = $\frac{\text{spend}}{\text{impressions}} \times 1000$
    - `CPP` = $\frac{\text{spend}}{\text{reach}} \times 1000$
    - `CPL` = $\frac{\text{spend}}{\text{leads}}$
    - `Cost per DM` = $\frac{\text{spend}}{\text{messages}}$
    - `Cost per call` = $\frac{\text{spend}}{\text{calls}}$
    - `Cost per install` = $\frac{\text{spend}}{\text{app\_installs}}$
    - `ROAS` = $\frac{\text{purchase\_value}}{\text{spend}}$
- **Reliability of Profile Visits & Followers**:
  - *Decision*: In Meta Graph API v21.0, organic Instagram profile visits and new followers are not standard fields on ad account insights without direct Instagram Graph API account link permissions. We map them where available via `actions[onsite_conversion.messaging_user_profile_click]` / `actions[page_engagement]`, but explicitly label them in the UI and documentation as "(Meta API: subject to ad format support)" and default to 0 if not reported by Meta, avoiding runtime exceptions.
- **Final Data Delay**:
  - Meta revises attribution data for recent conversions.
  - AdPulse enforces `FINAL_DATA_DELAY_HOURS` (default: 6 hours). If a report is scheduled earlier than 6 hours after the period ended in the ad account's timezone, the job runner defers execution to the first valid timestamp.

---

## 5. Delivery Channels
- **Telegram (aiogram 3)**:
  - Support for direct chat linking via deep-link `t.me/<bot>?start=<token>`.
  - Support for groups and supergroup forum topics via `/link <token>` (storing `chat_id` and `message_thread_id`).
  - Formatting with UTF-8 emojis, monospace numbers, and currency formatting.
  - Alert on Token Expiration (Error 190): automatically dispatches an alert message to linked Telegram destinations.
- **Google Sheets**:
  - Service account with Google Sheets API v4.
  - Users enter the sheet URL and tab name.
  - The worker verifies write access, creates header row if empty, dynamically adds missing metric columns, and appends a formatted row on every run.
  - Tab names with single quotes are escaped using A1 notation rules (`'` -> `''`), and missing tabs are automatically created.

---

## 6. Telegram Deep Linking & Robustness Fixes
- **Unified Deep Link Helper**: `build_telegram_deep_link` strips whitespace and leading `@`, validates bot usernames against `^[A-Za-z][A-Za-z0-9_]{4,31}$`, and validates start codes against `^[A-Za-z0-9_-]{1,64}$`.
- **Runtime Bot Username Resolution**: The backend queries Telegram's `getMe` at runtime (caching the result) and serves it via `GET /api/destinations/telegram/bot-info`. The frontend never relies on build-time environment variables.
- **UI Error State**: If username or start code is invalid, the frontend disables the connection buttons and renders an alert banner rather than navigating to a broken `t.me` link that redirects to `telegram.org`.
- **Dual Binding**: Reports support simultaneous binding of both personal chats (`/start`) and team group/forum topics (`/link` with `message_thread_id`) without overwriting each other.
- **Scheduler Alert Loop Prevention**: On Error 190 (expired token) or missing credentials, `RunHistory` is recorded and `next_run_at` is rescheduled to the next normal period (or paused), preventing the worker from spamming token-expired alerts every 10 minutes. Transient Meta API errors are retried up to 3 times with exponential backoff.

