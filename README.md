# ⛰️ Project Chiang M-AI

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://github.com/nakmuaycoder/where-to-run-today/actions/workflows/ci.yml/badge.svg)


> [!TIP]
> **Technical Deep Dives:**
> - **Episode 4**: [The "Zero-UI" Warehouse: Shipping AI Plans to Production](https://nakmuaycoder.github.io/nakmuaycoder-r-d-lab/posts/project-chiang-m-ai/04-the-automation-warehouse/)
> - **Episode 5**: [Full Auto Mode (Wellness-Based Adaptation)](https://nakmuaycoder.github.io/nakmuaycoder-r-d-lab/posts/project-chiang-m-ai/05-wellness-based-adaptation/)
>
> 🔖 **Version Control**: Use Git tags (e.g., `git checkout episode-5-v1.1.0`) to access the specific code state discussed in each post.

**Project Chiang M-AI** syncs AI-generated training plans (from Gemini/ChatGPT) to your training devices (Garmin, Wahoo, smart trainers) via **Intervals.icu** or **TrainingPeaks**.

## ⛰️ Project Chiang M-AI

This project is the technical implementation of **Project Chiang M-AI**, a personal R&D initiative documenting the use of LLMs, Python automation, and system engineering to prepare for the **Hoka Chiang Mai 160km** (100 miles) ultra-trail.

Full story, technical deep dives, and ongoing architectural logs are available at:
👉 **[Project Chiang M-AI: Fine-Tuning the Fighter](https://nakmuaycoder.github.io/nakmuaycoder-r-d-lab/posts/project-chiang-m-ai/)**

### 📚 Series Overview & Releases

| Episode | Blog Post | Git Tag | Focus |
| :--- | :--- | :--- | :--- |
| **Ep. 5** | [Full Auto Mode (Wellness-Based Adaptation)](https://nakmuaycoder.github.io/nakmuaycoder-r-d-lab/posts/project-chiang-m-ai/05-wellness-based-adaptation/) | `episode-5-v1.1.0` | Modular Brains, LLM Adaptation, Testing |
| **Ep. 4** | [The Zero-UI Warehouse](https://nakmuaycoder.github.io/nakmuaycoder-r-d-lab/posts/project-chiang-m-ai/04-the-automation-warehouse/) | `episode-4 v1.0.0` | Google Calendar API + Intervals.icu Sync |

## 🏗️ Architecture & Workflow

<img src="assets/workflow.png" alt="Gemini Coach Workflow" width="800">

### Wellness-Based Adaptive Workflow (Full Auto)

<img src="assets/full_auto_workflow.png" alt="Full Auto Workflow" width="800">

### Modular Design: Brain vs. Platform

As of Episode 5, the project has been refactored for maximum modularity using a **Brain vs. Sport Platform** architecture.

- **The Brain (`IBrain`)**: The "Decision Maker". It decides what the final workout should be.
    - `GoogleCalendarBrain`: Blindly trusts the manual plans in your calendar.
    - `AutoAdaptiveBrain`: Uses an LLM to adapt plans based on your wellness data.
    - `MockFileBrain`: Reads from a local JSON for testing.
- **The Sport Platform (`ISportPlatform`)**: The "Executioner". It handles data I/O and display.
    - `IntervalicuClient`: Pushes workouts to the real Intervals.icu platform.
    - `TrainingPeaksClient`: Syncs structured workouts directly to TrainingPeaks.
    - `LocalArchivePlatform`: Saves workouts as local JSON files (perfect for comparing AI outputs safely).

### The Workflow

```
Google Calendar (Manual Plan)
    ↓
Brain (Decides: Keep, Adapt, or Mock)
    ↓
Sport Platform (Sync to Intervals.icu or TrainingPeaks)
    ↓
Devices (Garmin, Wahoo, etc.)
```

**Intervals.icu** or **TrainingPeaks** act as the primary middleware for wellness data and syncing workouts to all major platforms.

## 🚀 Quick Start

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nakmuaycoder/project-chiang-m-ai.git
   cd project-chiang-m-ai
   ```

2. **Install uv (if needed):**
   - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - Mac/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

3. **Run installation:**
   ```bash
   make install
   ```

### Configuration

1. **Environment Variables**: Create a `.env` file for credentials:
```bash
INTERVALS_ATHLETE_ID=i12345
INTERVALS_API_KEY=your_intervals_key_here
TP_AUTH_COOKIE=your_tp_cookie_here  # TrainingPeaks auth cookie
GOOGLE_CALENDAR_CREDENTIALS_FILE=path/to/credentials.json
GEMINI_API_KEY=your_gemini_api_key_here
```

2. **App Configuration**: Customize the modular behavior in `coach_config.yaml`:
```yaml
coach:
  brain:
    type: "auto"      # "manual", "auto", or "mock"
    sync_mode: "today" # "today" or "all"
  destination:
    type: "training_peaks" # "intervals_icu", "training_peaks" or "local_storage"
```

**Get your credentials:**
- **Intervals.icu**: Settings → Developer Settings
- **Google Calendar**: [Google Cloud Console](https://console.cloud.google.com)

**Quick setup with script:**
```bash
uv run setup_keys.py --intervals_id="i12345" \
                      --intervals_key="YOUR_KEY" \
                      --calendar_creds="path/to/credentials.json" \
                      --periodization="3:1"
```

**Or copy `.env.example` to `.env` and fill in your values.**

### Google Calendar Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable **Google Calendar API**
4. Create OAuth 2.0 credentials (Desktop app)
5. Download `credentials.json`
6. Set path in `.env`: `GOOGLE_CALENDAR_CREDENTIALS_FILE=path/to/credentials.json`
7. First run will open browser for authorization

## 📖 Usage

### Sync Workouts to Devices

**Sync current training block:**
```bash
python -m project_chiang_m_ai sync --block
```
Syncs 28 days (3:1 periodization) or 21 days (2:1 periodization) based on your `.env` config.

**Other sync options:**
```bash
# This week (7 days)
python -m project_chiang_m_ai sync --week

# Today only
python -m project_chiang_m_ai sync --today

# Custom number of days
python -m project_chiang_m_ai sync --days 14

# Dry run (parse but don't upload)
python -m project_chiang_m_ai sync --block --dry-run
```

### Wellness Adaptation

**Let the LLM dynamically adjust your daily training based on Heart Rate Variability (HRV) and Resting Heart Rate (RHR) tracked in Intervals.icu or TrainingPeaks.**

```bash
# Adapt today's planned workouts based on fatigue trends
python -m project_chiang_m_ai adapt
```
If your readiness is low, the LLM will automatically replace intense VO2 max intervals with easy Z1/Z2 recovery or a rest day within your Google Calendar before syncing!

### Check Status

```bash
# Show sync statistics
python -m project_chiang_m_ai status

# List all synced workouts
python -m project_chiang_m_ai status --list
```

### Clean Up

```bash
# Delete all synced workouts from the Sport Platform
python -m project_chiang_m_ai clean

# Skip confirmation prompt
python -m project_chiang_m_ai clean -y

# Also clear sync database
python -m project_chiang_m_ai clean --clear-db
```

### Fetch & Export TrainingPeaks Data

**Fetch and export TrainingPeaks workouts and daily health metrics to CSV files:**
```bash
uv run python -m project_chiang_m_ai tp-fetch --start 2026-01-01 --end 2026-07-25
```

**Options:**
- `--start`: Start date in `YYYY-MM-DD` format (required, inclusive).
- `--end`: End date in `YYYY-MM-DD` format (required, inclusive).
- `--out-workouts`: Destination file path for the workouts CSV (default: `workouts.csv`).
- `--out-metrics`: Destination file path for the wellness metrics CSV (default: `metrics.csv`).

**Example:**
```bash
uv run python -m project_chiang_m_ai tp-fetch --start 2026-01-01 --end 2026-02-31 --out-workouts test-workouts.csv --out-metrics test-metrics.csv
```

### Help

```bash
# Show all commands
python -m project_chiang_m_ai --help

# Command-specific help
python -m project_chiang_m_ai sync --help
```

## 🍚 Daily Nutrition Plan & Free Mobile SMS Notifier

Automated daily nutrition calculation (Cooked Hom Mali Jasmine Rice, 16h Banana snack, Oats, and intra-workout carbs) with Free Mobile SMS delivery and TrainingPeaks Day Notes sync.

### 1. Setup & Credentials

You can set credentials in `.env` or pass them directly via command-line arguments:

#### Option A: Local `.env` file (Multi-Recipient or Single User)
```env
# Multi-recipient mode (Free Mobile credentials and language per user):
FREE_MOBILE_RECIPIENTS="USER1_ID:PASS1:fr,USER2_ID:PASS2:th"

# Or single user mode:
FREE_MOBILE_USER="YOUR_FREE_MOBILE_USER"
FREE_MOBILE_PASS="your_free_mobile_pass_key"
SMS_LANG="fr"  # fr (French), en (English), th (Thai)

TRAININGPEAKS_COOKIE="your_tp_auth_cookie"
TRAININGPEAKS_ATHLETE_ID="your_tp_athlete_id"
```

#### Option B: Pass Multi-Recipient Secrets directly via CLI
Pass multiple recipients directly as CLI arguments (pings TrainingPeaks only once):
```bash
uv run python scripts/notify_daily_rice.py -r "USER1_ID:PASS1:fr" -r "USER2_ID:PASS2:th" --date 2026-10-06
```

#### Option C: Set Secrets on GitHub via `gh` CLI
Set GitHub Repository Secrets directly from your terminal using the GitHub CLI (`gh`):
```bash
# Multi-recipient secret:
gh secret set FREE_MOBILE_RECIPIENTS --body "USER1_ID:PASS1:fr,USER2_ID:PASS2:th"

# TrainingPeaks credentials:
gh secret set TRAININGPEAKS_COOKIE --body "your_tp_auth_cookie"
gh secret set TRAININGPEAKS_ATHLETE_ID --body "your_tp_athlete_id"
```

---

### 2. Activating & Disabling SMS Notifications

#### A. Command Line (CLI)
- **Dry-run mode (print without sending SMS):**
  ```bash
  uv run python scripts/notify_daily_rice.py --dry-run
  ```
- **Disable SMS via Environment Variable:**
  ```bash
  SMS_DISABLED=true uv run python scripts/notify_daily_rice.py
  ```
- **Enable & Send SMS:**
  ```bash
  uv run python scripts/notify_daily_rice.py --date 2026-10-06 --lang fr
  ```

#### B. GitHub Actions
- **Enable / Disable Automated Daily Cron (20:00 CEST / 18:00 UTC):**
  - To **Disable**: Go to **GitHub Repository** -> **Actions** -> **Daily Rice Nutrition SMS Notifier** -> Click `...` -> **Disable workflow**.
  - To **Enable**: Click **Enable workflow**.
  - To **Trigger Manually**: Click **Run workflow** (`workflow_dispatch`).

---

### 3. Generate Calendar Day Notes on TrainingPeaks

Regenerate all 65 Day Notes on your TrainingPeaks calendar through the Chiang Mai 160k race:
```bash
uv run python scripts/generate_all_rice_notes.py
```

---


## 🔄 Workflow

1. **Generate your training plan** using Gemini 2.0 or ChatGPT o1
2. **Copy workout JSON** to Google Calendar event descriptions
3. **Sync to devices**: `python -m project_chiang_m_ai sync --block`
4. **Your workouts appear** on Garmin/Wahoo/trainer apps automatically!

## 🛠️ Tech Stack

- **Language:** Python 3.12+
- **Package Manager:** [uv](https://github.com/astral-sh/uv)
- **Linters:** Ruff, Pre-commit, Detect-secrets
- **APIs:** Intervals.icu, Google Calendar
- **Architecture:** Provider-agnostic interfaces (swap Google Calendar → Outlook, etc.)

## 📂 Project Structure

```
project-chiang-m-ai/
├── src/project_chiang_m_ai/
│   ├── __main__.py          # Entry point
│   ├── cli.py               # CLI Commands (sync, adapt, status)
│   ├── factory.py           # Dependency Injection (injects Brain/Platform)
│   │
│   ├── brains/              # Workout Logic
│   │   ├── base_calendar_brain.py
│   │   ├── auto_brain.py    # LLM adaptation
│   │   └── calendar_brain.py # Manual focus
│   │
│   ├── clients/             # API & Platform Clients
│   │   ├── intervalicu.py
│   │   ├── trainingpeaks.py
│   │   ├── google_calendar.py
│   │   └── local_platform.py # For local testing
│   │
│   ├── interfaces/          # Abstractions (IBrain, ISportPlatform)
│   │
│   ├── services/            # Orchestration
│   │   ├── coach.py         # The Conductor
│   │   └── workout_tracker.py
│   │
│   └── models/              # Pydantic Models (Workout, Step)
│
├── coach_config.yaml        # Main modular config
├── .env                     # Private secrets
├── data/                    # Sync history & Local archives
└── tests/                   # Test suite
```

## 🎯 Periodization

The CLI supports training periodization patterns:

-   **3:1** (default): 28-day blocks (3 weeks load + 1 week recovery)
-   **2:1**: 21-day blocks (2 weeks load + 1 week recovery)

Set in `.env`:
```env
PERIODIZATION=3:1
```

Then sync your entire block:
```bash
python -m project_chiang_m_ai sync --block  # Auto-calculates 21 or 28 days
```

## 📝 License

MIT License - see LICENSE file for details.
