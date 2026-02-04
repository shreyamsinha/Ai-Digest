# 🧠 AI Intel Digest

**AI Intel Digest** is a privacy-first, fully local AI system that automatically collects, evaluates, summarizes, and delivers **daily AI / GenAI news and product ideas** directly to Telegram.

No cloud LLM APIs.  
No tracking.  
Runs entirely on your machine using **Ollama + local models**.

---

## ✨ What It Does

AI Intel Digest runs as a daily pipeline:

1. Collects fresh AI-related content (currently Hacker News)
2. Filters low-signal items
3. Deduplicates similar stories using embeddings + FAISS
4. Evaluates relevance using a local LLM
5. Builds structured digests (JSON + Markdown)
6. Sends a clean, engaging summary to Telegram

You open Telegram → you get the signal → no scrolling required.

---

## 🧩 Features

### 🏠 Fully Local AI
- Uses **Ollama** (Gemma, LLaMA, etc.)
- No OpenAI / Anthropic / external APIs
- All processing happens on your machine

### 🧠 Multi-Persona Intelligence
Supported personas:
- **GENAI_NEWS** – AI / GenAI engineering updates
- **PRODUCT_IDEAS** – reusable product & startup ideas

Each persona has:
- Custom LLM prompts
- Structured JSON schema validation
- Independent scoring & filtering

### 🔍 Smart Filtering & Deduplication
- Time-window based “true daily” digests
- Vector embeddings with **FAISS**
- Prevents repeated or near-duplicate items

### 📊 Signal-Aware Ranking
- Includes **Hacker News upvotes & comment counts**
- Sorts by relevance + engagement
- Highlights top picks first

### 🧾 Digest Outputs
- JSON (machine-readable)
- Markdown (human-readable)
- Stored locally for history & auditing

### 📬 Telegram Delivery
- MarkdownV2-safe formatting
- “Why it matters” summaries
- Tags, audience hints, and engagement signals
- Single combined daily message


## 🏗️ Architecture

Ingestion → Prefilter → Dedup (FAISS)
→ LLM Evaluation (Ollama)
→ Digest Builder (JSON/MD)
→ Telegram Delivery

## 🧠 Models

- **LLM**: `gemma3:12b` (default, configurable)
- **Embeddings**: `nomic-embed-text`
- Easily switchable via `.env`

## 📁 Project Structure

ai-intel-digest/
├── src/
│ ├── cli/ # CLI entrypoints
│ ├── config/ # Pydantic settings
│ ├── db/ # SQLAlchemy models
│ ├── services/
│ │ ├── hn_ingest.py # Hacker News ingestion
│ │ ├── evaluator.py # LLM evaluators
│ │ ├── dedup.py # FAISS deduplication
│ │ └── telegram_delivery.py
│ └── workflows/
│ ├── run_digest.py
│ └── build_digest.py
├── out/ # Generated digests
├── data/ # SQLite DB
├── .env.example
├── requirements.txt
└── README.md


---

## ⚙️ Setup

### 1️⃣ Requirements
- Python **3.11+**
- Ollama installed and running
- Telegram bot token

### 2️⃣ Install
```bash
git clone https://github.com/yourusername/ai-intel-digest.git
cd ai-intel-digest
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

3️⃣ Pull Models
ollama pull gemma3:12b
ollama pull nomic-embed-text

4️⃣ Configure Environment
cp .env.example .env


Example .env:

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:12b

PERSONA_GENAI_NEWS_ENABLED=true
PERSONA_PRODUCT_IDEAS_ENABLED=true

TIME_WINDOW_HOURS=24
EVAL_MAX_ITEMS=10

OLLAMA_EMBED_MODEL=nomic-embed-text
DEDUP_SIM_THRESHOLD=0.86

TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_CHAT_ID
TELEGRAM_PARSE_MODE=MarkdownV2
TELEGRAM_MAX_ITEMS=6

▶️ Usage
Run Manually
python -m src.cli.main run

Health Check
python -m src.cli.main doctor

⏰ Automation
Windows (Task Scheduler)

Trigger: Daily

Action:

Program: powershell.exe
Arguments:
  -Command "cd C:\path\to\ai-intel-digest; .\.venv\Scripts\Activate.ps1; python -m src.cli.main run"

