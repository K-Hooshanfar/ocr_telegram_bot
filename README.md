<div align="center">

# AI OCR Telegram Bot

**Gemini-powered document OCR exposed as a REST API and Telegram bot**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [API](#-api-reference) · [Author](#-author)

</div>

---

## Overview

This is a production-style OCR service that turns document photos into structured text using **Google Gemini 2.0 Flash**. Users interact through a **Telegram bot** — send a photo, get Markdown text back. A **FastAPI** backend handles authentication, credit management, OCR history, and DOCX export.

Built to demonstrate full-stack backend skills: async APIs, JWT auth, PostgreSQL, Docker orchestration, and third-party AI integration.

## Features

| Area | Details |
|------|---------|
| **OCR Engine** | Google Gemini 2.0 Flash — handwriting, math, tables, 100+ languages |
| **Telegram Bot** | Photo upload → OCR → text reply with `/start` and `/help` commands |
| **REST API** | FastAPI with OpenAPI docs at `/docs` |
| **Auth** | JWT tokens, bcrypt password hashing, per-user credit system |
| **RTL Support** | Automatic Hebrew/Arabic direction detection |
| **Export** | Markdown → DOCX conversion with RTL layout |
| **History** | Per-user OCR job storage with image and text retrieval |
| **Deploy** | Docker Compose stack: PostgreSQL + API + Bot |

## Architecture

```
┌─────────────┐     photo      ┌──────────────┐    REST/JWT    ┌─────────────┐
│  Telegram   │ ─────────────► │  Telegram    │ ─────────────► │  FastAPI    │
│  User       │ ◄───────────── │  (aiohttp)   │ ◄───────────── │  Backend    │
└─────────────┘   OCR text     └──────────────┘   JSON response  └──────┬──────┘
                                                                        │
                                        ┌───────────────────────────────┼────────────────┐
                                        ▼                               ▼                ▼
                                 ┌─────────────┐                ┌─────────────┐  ┌──────────┐
                                 │ PostgreSQL  │                │ Gemini API  │  │  Static  │
                                 │ (users,     │                │ (OCR)       │  │  uploads │
                                 │  history)   │                └─────────────┘  └──────────┘
                                 └─────────────┘
```

## Project Structure

```
ocr_telegram_bot/
├── app/                    # FastAPI backend
│   ├── main.py             # App entry, middleware, startup
│   ├── auth.py             # JWT & password utilities
│   ├── config.py           # Pydantic settings (.env)
│   ├── database.py         # SQLAlchemy + PostgreSQL
│   ├── models.py           # User & OCRRequest models
│   ├── ocr_utils.py        # Gemini OCR wrapper
│   ├── util_convert.py     # Markdown → DOCX
│   ├── routes/
│   │   ├── ocr.py          # Upload, history, delete
│   │   └── user.py         # Login, profile
│   └── static/upload/      # Stored images & DOCX files
├── telegram/
│   └── bot.py              # Telegram bot client
├── scripts/
│   └── get_token.py        # Helper to obtain JWT for the bot
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.bot
├── requirements.txt
├── .env.example
└── LICENSE
```

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- [Google AI API key](https://aistudio.google.com/apikey) (Gemini)
- [Telegram bot token](https://t.me/BotFather) from BotFather

### 1. Clone & configure

```bash
git clone https://github.com/arhosseini77/ocr_telegram_bot.git
cd ocr_telegram_bot
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
GOOGLE_API_KEY=your-gemini-api-key
TELEGRAM_BOT_TOKEN=your-bot-token
JWT_SECRET_KEY=a-long-random-secret
ADMIN_PASS=a-strong-password
```

### 2. Start the stack

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| API | http://localhost:8067 |
| API Docs | http://localhost:8067/docs |
| Health | http://localhost:8067/health |

### 3. Get a JWT for the bot

```bash
python scripts/get_token.py --username admin --password your-admin-password
```

Copy the printed token into `.env` as `OCR_API_KEY`, then restart the bot:

```bash
docker compose restart bot
```

### 4. Use the bot

Open your bot in Telegram and send a photo of any document.

---

## Local Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in your keys

# Terminal 1 — PostgreSQL must be running locally
uvicorn app.main:app --reload --port 8067

# Terminal 2 — after getting OCR_API_KEY
python telegram/bot.py
```

## API Reference

Interactive docs: **http://localhost:8067/docs**

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/user/login` | Form: `username`, `password` → JWT |
| `GET` | `/user/me` | Current user info & credits |

### OCR

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ocr/upload?format_type=markdown\|latex` | Upload image, run OCR |
| `GET` | `/ocr/history` | List past OCR jobs |
| `GET` | `/ocr/history/{hash}` | Get job by hash |
| `DELETE` | `/ocr/history/{id}` | Delete job and files |

### Example — upload via curl

```bash
TOKEN=$(python scripts/get_token.py --username admin --password changeme)

curl -X POST "http://localhost:8067/ocr/upload?format_type=markdown" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.jpg"
```

## Tech Stack

- **API:** FastAPI, Uvicorn, Pydantic Settings
- **Database:** PostgreSQL 15, SQLAlchemy
- **Auth:** JWT (python-jose), bcrypt (passlib)
- **OCR:** Google Gemini 2.0 Flash (`google-genai`)
- **Bot:** python-telegram-bot, aiohttp
- **Export:** python-docx, Markdown, BeautifulSoup
- **Infra:** Docker Compose

## Environment Variables

See [`.env.example`](.env.example) for the full list.

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
| `OCR_API_KEY` | Yes | JWT from `/user/login` |
| `JWT_SECRET_KEY` | Yes | Secret for signing tokens |
| `ADMIN_USER` / `ADMIN_PASS` | Yes | Seeded admin account |
| `POSTGRES_*` | No | Database credentials (defaults in compose) |


## License

This project is licensed under the [MIT License](LICENSE).
