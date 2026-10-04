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
- **Pinned Graph API Version**: `v21.0` (`https://graph.facebook.com/v21.0`), officially supported by Meta and dynamically constructed from `settings.META_GRAPH_API_VERSION`.
- **Token Verification**: Calls `GET /me` (retrieves name and id) and `GET /me/adaccounts?fields=id,name,account_id,currency,timezone_name,account_status`.
- **Deduplication of Reach & Frequency**:
  - Reach cannot be summed across campaigns without overcounting unique users.
  - When querying Meta API, AdPulse requests account-level insights filtered by campaign IDs:
    `level=account&filtering=[{"field":"campaign.id","operator":"IN","value":[<campaign_ids>]}]`.
    This delegates cross-campaign reach deduplication to Meta's data engine.
- **Strict Ratio Calculation (No Averaging)**:
  - Additive metrics (`spend`, `impressions`, `clicks`, `inline_link_clicks`, `leads`, `messages`, `calls`, `purchases`) are summed from raw actions.
  - All rates and costs are calculated strictly from the aggregate totals:
    - `CTR` = $\frac{\text{clicks}}{\text{impressions}} \times 100\%$
    - `CTR (link)` = $\frac{\text{inline\_link\_clicks}}{\text{impressions}} \times 100\%$
    - `CPC` = $\frac{\text{spend}}{\text{clicks}}$ (or `None` if clicks = 0)
    - `CPM` = $\frac{\text{spend}}{\text{impressions}} \times 1000$ (or `None` if impressions = 0)
    - `CPP` = $\frac{\text{spend}}{\text{reach}} \times 1000$ (or `None` if reach = 0)
    - `CPL` = $\frac{\text{spend}}{\text{leads}}$ (or `None` if leads = 0 or absent)
    - `Cost per DM` = $\frac{\text{spend}}{\text{messages}}$ (or `None` if messages = 0 or absent)
    - `Cost per call` = $\frac{\text{spend}}{\text{calls}}$ (or `None` if calls = 0 or absent)
    - `Cost per install` = $\frac{\text{spend}}{\text{app\_installs}}$ (or `None` if app_installs = 0 or absent)
    - `ROAS` = $\frac{\text{purchase\_value}}{\text{spend}}$ (or `None` if spend = 0 or purchase_value = 0)
- **Corrected Action Type Mappings**:
  - **Messages / DM**: Strictly mapped to `onsite_conversion.messaging_conversation_started_7d`. Never sum with `onsite_conversion.total_messaging_connection` (which represents connection interactions that overcounted lead forms to ~119). In non-messaging campaigns (e.g. Lead Forms), if no conversation started is recorded, `messages` and `cost_per_dm` correctly evaluate to `None` -> displayed as localized "н/д" / "N/A", never a fake cost like $0.22.
  - **Leads**: Mapped to `lead` (which in Meta Marketing API is already the aggregate of onsite instant forms and website pixel leads). If `lead` is absent, falls back to `onsite_conversion.lead_grouped + offsite_conversion.fb_pixel_lead` or `leadgen.other`. Never sums `lead` and `lead_grouped` together, avoiding double-counting.
  - **New Followers**: Mapped to `like` (Page Likes) or `follow`. Meta Ads Insights does not provide Instagram follower acquisition metrics. Never maps to `page_engagement` (which caused 9,236 by summing all post reactions, video views, and comments). If no follower action is tracked, it renders as "н/д" / "N/A", never a fake number or 0.
  - **Calls**: Mapped primarily to `click_to_call_native_call_placed` (which corresponds 1:1 with Ads Manager's "Calls placed" column), followed by `phone_call`, `call_confirm`, `onsite_conversion.call_attempt`, or fallback to `onsite_conversion.lead_grouped`.
  - **App Installs**: Mapped to `mobile_app_install` or `omni_app_install`.
- **Handling of Unavailable / Non-Applicable Metrics**:
  - Any metric not recorded or not reliably available evaluates to `None` and is rendered in Telegram and UI as localized `"н/д"` (RU), `"mavjud emas"` (UZ), or `"N/A"` (EN).
  - In Google Sheets, `None` metrics are written as empty cells (`""`), and valid numbers are written strictly as numeric floats/ints.
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

---

## 7. Fallback Metrics & Approximation Marking (Item 3)
- **Problem**: Meta Marketing API action types vs Ads Manager reporting:
  - **Calls placed**: In Ads Manager, "Calls placed" corresponds to `click_to_call_native_call_placed` (native phone dialer placed call). Prioritizing this action type yields exact parity with Ads Manager (e.g. 19 calls vs previous 16 from `call_confirm`). Fallback to `onsite_conversion.lead_grouped` with `≈` is used only when direct call action keys are absent.
  - **Profile visits**: In Meta Marketing API, there is NO `profile_visit` or `instagram_profile_visit` action type in the `actions` array. The true count is reported only in the `results` array with `indicator: "total_profile_visits"` (when querying single-objective campaigns or with campaign filtering). When querying account-level insights across mixed objectives (e.g. Call + Traffic campaigns), Meta returns `results: [{"indicator": "mixed"}]`. In that scenario, `results` does not contain profile visits, so the engine falls back to `link_click` / `inline_link_clicks` marked with `≈` (`is_approximate = True`) to indicate an estimate.
  - Simply returning `None` blinds the marketing team, displaying "mavjud emas" despite active conversions in Ads Manager. Conversely, reporting them as exact without indicators conceals the underlying estimation.
- **Architectural Decision**:
  - `ReportEngine.compute_aggregated_metrics` checks `results` for `total_profile_visits` first. If present, it records exact profile visits (`is_approximate = False`).
  - We retain smart fallbacks (`onsite_conversion.lead_grouped` for `calls`, and `link_click` / `inline_link_clicks` for `profile_visits`) when primary direct action keys or results indicators are absent.
  - When a fallback is applied, the metric is marked as approximate:
    1. In `metrics_data`, an array `approximate_metrics: list[str]` (e.g. `["calls", "cost_per_call"]`, `["profile_visits"]`) is persisted in the database run history.
    2. In Telegram messages, the formatted value is automatically prefixed with an approximation sign: `≈ $3.05` or `≈ 416`.
    3. In Google Sheets, numeric values remain pure integers/floats without string prefixes to protect sheet formulas and analytical charting.

---

## 8. Period Comparison & Deltas Architecture
- **Attribution Lag for Recent Conversions**:
  - Conversions (`leads`, `calls`, `messages`, `roas`) for the most recently closed period (e.g., yesterday or last week) may still experience attribution lag/delayed updates over subsequent hours or days in Meta's attribution window (e.g., 7-day click / 1-day view).
  - Consequently, deltas comparing the newest period to an older, fully settled period may appear slightly lower initially. This is an inherent characteristic of Meta's retrospective attribution pipeline, not an application bug.
- **Monthly Comparison Strategy**:
  - For monthly reports, AdPulse compares absolute calendar month totals (e.g., full September vs full August) and includes an explanatory date note indicating the number of days in each month (e.g., `30 дн. против 31 дн.`).
  - This preserves exact 1:1 numerical parity with Meta Ads Manager reported figures without artificially distorting metric values.
- **Mixed Fallback Attribution Rule**:
  - If a metric (`profile_visits` or `calls`) was resolved via direct action types in one period but via fallback (`link_click` or `lead_grouped`) in the other, delta calculation for that metric is suppressed. Comparing disparate tracking methodologies would produce misleading growth or decline rates.
- **Metric Polarity & Visual Indicators**:
  - **Neutral**: `spend`, `impressions`, `reach`, `clicks` are informational volume indicators; they display change arrows (`▲ +X%`, `▼ -X%`, `= 0%`) without judgmental color badges (`🟢`/`🔴`).
  - **Lower is Better**: Efficiency costs (`cpc`, `cpm`, `cpp`, `cpl`, `cost_per_dm`, `cost_per_call`, `cost_per_install`) show `🟢 ▼ -X%` for cost reductions and `🔴 ▲ +X%` for cost increases.
  - **Higher is Better**: Conversions, rates, and returns (`leads`, `messages`, `calls`, `link_clicks`, `landing_page_views`, `ctr`, `ctr_link`, `roas`, `video_views`, `new_followers`, `post_engagement`, `app_installs`) show `🟢 ▲ +X%` for growth and `🔴 ▼ -X%` for decline.
- **Edge Cases & Division by Zero**:
  - If the previous period value was 0 or `None` and the current value is $> 0$, the metric is badged as `🆕 new` (never false `0%`).
  - If both periods have 0 or `None`, no delta is displayed (`—`).
- **Google Sheets Integration**:
  - Each metric receives a dedicated delta column `Δ {Metric} (%)`.
  - Values are formatted strictly as numeric floats (e.g., `12.5` or `-4.0`), allowing spreadsheet formulas, charting, and conditional formatting to work seamlessly.
  - For existing spreadsheets with established headers, `sheets_service` dynamically appends delta columns to the right without modifying or displacing preexisting columns.

---

## 9. Two-Phase Execution & Worker Crash Deduplication
- **Delivery Semantics: At-Most-Once**:
  - Duplicate reporting messages sent to client Telegram channels or duplicated rows in Google Sheets create severe confusion for end-users and client management. Therefore, AdPulse adopts **at-most-once** delivery semantics for automated periodic reports.
- **Two-Phase Database State Lifecycle**:
  - Before querying external APIs and dispatching messages, the scheduler worker writes a `RunHistory` record with `status = "sending"`, timestamps, and the exact `(report_id, period_start, period_end)` scope.
  - The partial unique index `uq_run_history_report_period` on `(report_id, period_start, period_end)` covers `status IN ('success', 'no_data', 'sending') WHERE is_test = FALSE`.
  - Any concurrent or duplicate worker pickup for the same period will immediately violate the unique constraint and abort gracefully without double-dispatching messages.
  - Once delivery succeeds, the record is transitioned to `status = "success"` or `"no_data"`. If dispatch fails with an unrecoverable error, it is transitioned to `status = "failed"`.
- **Stalled "Sending" Recovery (Timeout Threshold)**:
  - If a worker crashes or gets killed (e.g., OOM, node reboot) mid-flight, a record may remain in `status = "sending"`.
  - On the next cycle, the scheduler checks for orphaned runs with `status = "sending"` whose `created_at` exceeds a 15-minute threshold (`STALLED_RUN_TIMEOUT_MINUTES = 15`).
  - Stalled runs are marked as `status = "failed"` with `error_message = "Execution timed out or worker crashed during dispatch (marked failed to avoid duplicate delivery)"`.
  - This clears the unique constraint for manual retry while preventing unexpected automated bursts of duplicate messages.

---

## 10. Telegram Delivery Formatting & Accurate Ratio Deltas
- **Clean Primary Report + Dedicated Comparison Report (Two Messages)**:
  - **Message 1 (Primary)**: Displays the current period's key metrics cleanly and legibly without inline delta percentages, emojis, or clutter.
  - **Message 2 (Comparison)**: Sent as a follow-up reply in the same chat/topic thread only when `show_comparison=True` and prior period data exists (omitted for live `is_test=True` runs).
  - Grouped into structured thematic blocks:
    1. *Общие показатели* (Общий бюджет, Показы, Охват, Клики)
    2. *Эффективность* (CPC, CPM, CPP, CTR)
    3. *Конверсии и стоимость* (Лиды, Переписки, Звонки, Заказы/Покупки, Приложения, ROAS)
  - Clear "was → became" format: e.g., `CPC: $0.09 → $0.08 (🟢 ▼ -7.2%)`.
- **Accurate Unrounded Ratio Deltas**:
  - Calculating percentage changes between pre-rounded values (e.g., `$0.08` vs `$0.09`) causes significant mathematical distortion (e.g., `-11.1%` reported vs `-5.6%` actual).
  - Delta computations for ratio metrics (`cpc`, `cpm`, `cpp`, `ctr`, `ctr_link`, `cpl`, `cost_per_dm`, `cost_per_call`, `roas`) compute changes directly from the exact underlying component sums (`spend / clicks`, etc.) when available.
  - Metrics marked with fallback approximation (`≈`) or missing current data suppress percentage deltas to prevent displaying false or misleading variances (e.g., never output `-100%` when a metric is merely uncollected or `None`).

---

## 11. Hybrid Metric Extraction, Snapshot Persistence & Telegram Audit Artifacts
- **Hybrid Two-Layer Extraction for Instagram Profile Visits**:
  - Meta Graph API at `level=account` returns `results: null` or `results: [{indicator: "mixed"}]`, omitting `total_profile_visits`.
  - When `profile_visits` is among selected metrics, AdPulse executes a campaign-level query (`level=campaign` with `spend > 0`).
  - Total profile visits is calculated strictly by summing campaigns that report `indicator == "total_profile_visits"`. No link clicks are substituted for other campaigns in this mode, eliminating the `≈` marker and providing exact 1:1 parity with Ads Manager.
  - If no campaigns report `total_profile_visits`, the system falls back to link clicks marked with `≈`.
- **Strict Account-Level Reach**:
  - `reach` is non-additive across campaigns due to Meta's statistical estimation and user deduplication.
  - Reach is always taken strictly from the `level=account` insight response.
- **Cursor Pagination for Campaign Insights**:
  - `MetaClient.get_campaign_insights` supports cursor pagination (`paging.cursors.after`) to retrieve all active campaigns when an account has more than 25 campaigns.
- **Raw Meta Snapshot & Dispatch Traceability**:
  - `RunHistory` stores `raw_meta_snapshot` (including `fetched_at` ISO timestamp, `attribution_mode`, account insights, and campaign insights for both current and prior comparison periods) for dispute resolution and auditing.
  - `RunHistory` records `telegram_message_id` immediately upon successful Telegram dispatch to link database run records directly to sent chat messages.


