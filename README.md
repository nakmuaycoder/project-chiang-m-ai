# 🤖 Gemini Coach

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![License](https://img.shields.io/badge/license-MIT-green)

**Gemini Coach** is a Python-based automation tool that bridges the gap between AI-driven coaching (**Google Gemini**) and your physical training hardware (**Garmin/Wahoo**), using **Intervals.icu** as a strategic middleware.

## 🏗️ Architecture & Workflow

![Gemini Coach Workflow](assets/workflow.png)

### The Problem
I use **TrainingPeaks Virtual** to control my smart trainer. However, TPV **does not offer a public API** for individual users to push custom workouts programmatically. This breaks the automation chain.

### The Solution
**Intervals.icu** acts as the bridge. It offers a robust API and automatically syncs workouts to all major platforms.

### The Feedback Loop (The "Coach" Part)
As illustrated above, this is not just a one-way street. The system is designed to be a **closed loop**:
1.  **Analyze:** The script retrieves physiological data (HRV, Resting Heart Rate) to assess readiness.
2.  **Generate:** Gemini creates a specific training session adapted to this state.
3.  **Execute:** The workout is synced to Garmin/Wahoo/TPV for execution.

## 🛠️ Tech Stack

* **Language:** Python 3.12+
* **Manager:** [uv](https://github.com/astral-sh/uv) (Blazing fast dependency management)
* **Linters:** Ruff, Pre-commit, Detect-secrets
* **APIs:** Intervals.icu, Google Gemini

## 🚀 Installation

```
gemini-coach/
├── assets/
│   └── workflow.png
├── .env
├── .gitignore
├── .pre-commit-config.yaml
├── .secrets.baseline
├── LICENSE
├── Makefile
├── README.md
├── main.py
├── pyproject.toml
└── setup_keys.py
```

This project uses a **Makefile** and **uv** to automate the setup.

1.  **Clone the repository:**

    ```bash
    git clone [https://github.com/nakmuaycoder/gemini-coach.git](https://github.com/nakmuaycoder/gemini-coach.git)
    cd gemini-coach
    ```

2.  **Install uv (if needed):**
    * *Windows:* `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
    * *Mac/Linux:* `curl -LsSf https://astral.sh/uv/install.sh | sh`

3.  **Run the installation:**
    This command will install dependencies, setup the virtual environment, and configure git hooks (pre-commit) automatically.
    
    ```bash
    make install
    ```

## 🔑 Configuration

Security is paramount. We use a .env file to store credentials locally. This file is ignored by Git to prevent accidental leaks.
1. Gather your Credentials

    Intervals API Key: Go to Settings → Developer Settings on Intervals.icu.

    Athlete ID: Look at the URL of your calendar page (e.g., intervals.icu/athlete/i12345).

    Google API Key: Generate it at Google AI Studio.

2. Run the Setup Script (Recommended)

We provide a utility script to securely generate the configuration file. Run the following command in your terminal (replace the values with your actual keys):
Bash

```bash
uv run setup_keys.py --intervals_id="i12345" --intervals_key="YOUR_INTERVALS_KEY" --google_key="YOUR_GOOGLE_KEY"
```

Note: After running this command, it is good practice to clear your terminal history (history -c or Clear-History).
3. Manual Method (Alternative)

If you prefer not to use the script, simply create a file named .env in the root directory and paste your credentials:
Ini, TOML

INTERVALS_ATHLETE_ID=i12345
INTERVALS_API_KEY=your_intervals_key_here
GOOGLE_API_KEY=your_google_key_here