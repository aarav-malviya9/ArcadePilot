# ArcadePilot

AI-powered assistant for Google Cloud Skills Boost and Arcade labs.

## Features

- Parse lab instructions into structured tasks
- Generate safe shell/gcloud commands with risk classification
- Persistent Chromium browser profile for page inspection
- SQLite-tracked progress and history
- Dark-themed Streamlit dashboard

## Installation

```bash
# Windows
.\install.bat

# Or manually
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
.\start.bat
```

Then open http://localhost:8501

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
copy .env.example .env
```

## Safety

- Commands are classified as safe/review/dangerous before execution
- Destructive commands require explicit approval
- No credentials are persisted by the app
- gcloud operations are read-only by default

## Project Structure

```
ArcadePilot/
  app.py                  # Entry point
  core/                   # Business logic
  browser/                # Playwright automation
  cloud/                  # gcloud integration
  ui/                     # Streamlit pages
  storage/                # SQLite database + logs
  tests/                  # Unit tests
```
