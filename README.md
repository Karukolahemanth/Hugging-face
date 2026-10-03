# 🤖 GAIA Agent — General-Purpose AI Agent & Benchmark Evaluator

A production-oriented, modular, and extensible General-Purpose AI Agent built to solve complex real-world tasks through iterative planning, tool execution, multi-modal reasoning, and self-correction. 

> **Designed for local execution & GAIA Benchmark Evaluation** — supports evaluating on the GAIA (General AI Assistants) dataset and submitting directly to the Hugging Face GAIA Leaderboard.

---

## 📌 Table of Contents
- [🎯 Overview](#-overview)
- [🏗️ Architecture](#️-architecture)
- [✨ Key Features](#-key-features)
- [🚀 Quick Start Guide](#-quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#1-backend-setup)
  - [Frontend Setup](#2-frontend-setup)
- [🔑 Environment Configuration](#-environment-configuration)
- [🛠️ Tool Ecosystem](#️-tool-ecosystem)
- [📊 GAIA Benchmark & Leaderboard Submission](#-gaia-benchmark--leaderboard-submission)
- [🔒 Security & Sandboxing](#-security--sandboxing)
- [🧪 Testing](#-testing)
- [💡 Quota & Rate Limit Management](#-quota--rate-limit-management)
- [📄 License](#-license)

---

## 🎯 Overview

Unlike traditional chatbots that simply answer prompt-by-prompt, **GAIA Agent** operates as an autonomous agentic loop:

```
User Task → Understand & Plan → Tool Selection → Sandboxed Execution → Observe Result → Verify & Re-plan → Final Answer
```

### Core Capabilities:
- **Multi-step Autonomous Reasoning**: Iteratively plans and executes multi-tool workflows until the task is complete.
- **Rich Tool Ecosystem**: Includes sandboxed Python execution, safe math calculation, multi-provider web search, webpage scraping, multi-format file parsing (PDF, DOCX, XLSX, CSV, JSON, TXT), and vision image analysis.
- **GAIA Benchmark Suite**: Native evaluation scripts for running against GAIA Level 1, 2, and 3 tasks with direct JSONL export formatted for the Hugging Face Leaderboard.
- **Modern Streaming UI**: React + Vite frontend with Server-Sent Events (SSE) for real-time visualization of agent steps and observations.

---

## 🏗️ Architecture

```
gaia-agent/
├── backend/
│   ├── main.py               # FastAPI application entry point
│   ├── agent/
│   │   ├── agent.py          # Core agent reasoning & execution loop
│   │   ├── planner.py        # LLM plan interpreter & decision parser
│   │   ├── executor.py       # Tool execution dispatcher
│   │   ├── state.py          # Agent state management (Pydantic models)
│   │   ├── memory.py         # Conversation state & SQLite persistence
│   │   └── prompts.py        # System instructions & tool schemas
│   ├── llm/
│   │   ├── base.py           # Abstract Base LLM Provider interface
│   │   ├── gemini.py         # Google Gemini LLM & Vision integration
│   │   └── openai_compatible.py # OpenAI / Ollama compatible provider
│   ├── tools/
│   │   ├── registry.py       # Centralized Tool Registry
│   │   ├── calculator.py     # Safe math evaluator (simpleeval)
│   │   ├── python_executor.py# Sandboxed Python code execution
│   │   ├── web_search.py     # Multi-provider web search (Tavily/Serper/DuckDuckGo)
│   │   ├── webpage_reader.py # HTML fetching & cleaning engine
│   │   ├── file_reader.py    # Document reader (PDF, DOCX, Excel, CSV, TXT)
│   │   └── image_analyzer.py # Vision AI image interpretation tool
│   ├── api/
│   │   ├── chat.py           # Synchronous & SSE Streaming Chat Endpoints
│   │   ├── files.py          # File Upload API handler
│   │   └── health.py         # System Health API endpoint
│   ├── database/             # SQLAlchemy ORM + SQLite database layer
│   └── security/             # Security filter & input safety layer
├── evaluation/
│   ├── gaia_submit.py        # GAIA benchmark evaluation & leaderboard generator
│   └── sample_tasks.json     # Sample evaluation benchmark dataset
└── frontend/                 # Modern React + Vite Dashboard
    └── src/
        ├── components/       # ChatWindow, MessageList, AgentSteps, Sidebar, FileUpload
        └── api/client.js     # SSE streaming client
```

---

## ✨ Key Features

| Component | Description | Status |
|---|---|---|
| **Agent Reasoning Engine** | Autonomous multi-step decision loop with error recovery | ✅ Active |
| **Sandboxed Code Execution** | Isolated Python subprocess execution with blocked forbidden modules | ✅ Active |
| **Multi-Provider Web Search** | Automatic fallback between Tavily, Serper, and DuckDuckGo | ✅ Active |
| **Document Intelligence** | Parses PDF, DOCX, XLSX, CSV, JSON, TXT with table extractions | ✅ Active |
| **Vision AI Integration** | Analyzes charts, images, diagrams, and OCR using Gemini Vision | ✅ Active |
| **GAIA Leaderboard Script** | Evaluation script generating `.jsonl` submissions for Hugging Face | ✅ Active |
| **Real-Time Streaming UI** | Reactive frontend displaying live tool executions and thought steps | ✅ Active |

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.11+
- **Node.js**: v18+
- **Git**

### 1. Backend Setup

```powershell
# Navigate to project directory
cd gaia-agent

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.venv\Scripts\activate

# Install backend dependencies
pip install -r backend\requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file inside the `backend/` directory:

```powershell
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env`:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key_here
GEMINI_MODEL=gemini-2.0-flash
SEARCH_PROVIDER=duckduckgo
DATABASE_URL=sqlite:///./gaia.db
MAX_AGENT_STEPS=15
```

### 3. Start Backend Server

```powershell
uvicorn backend.main:app --reload --port 8000
```
Backend API will be live at: `http://localhost:8000`

### 4. Frontend Setup

In a new terminal window:

```powershell
cd gaia-agent\frontend
npm install
npm run dev
```
Frontend UI will be live at: `http://localhost:5173`

---

## 🛠️ Tool Ecosystem

The agent dynamically selects tools based on task demands:

1. **Calculator (`calculator.py`)**: Safe evaluation of mathematical formulas using AST parsing via `simpleeval`.
2. **Python Executor (`python_executor.py`)**: Executes code in an isolated subprocess with explicit timeout limits and module restrictions (`os`, `sys`, `subprocess` blocked).
3. **Web Search (`web_search.py`)**: Fetches search results with title, URL, and snippet citations across Tavily, Serper, or DuckDuckGo.
4. **Webpage Reader (`webpage_reader.py`)**: Extracts, strips, and cleans text content from target URLs.
5. **File Reader (`file_reader.py`)**: Reads structured data from PDFs (`PyMuPDF`), Word documents (`python-docx`), Excel sheets (`openpyxl`), CSVs, and plain text.
6. **Image Analyzer (`image_analyzer.py`)**: Performs visual inspection, OCR, and chart analysis using Gemini Vision model capabilities.

---

## 📊 GAIA Benchmark & Leaderboard Submission

To evaluate the agent against the official [GAIA Benchmark](https://huggingface.co/datasets/gaia-benchmark/GAIA) and submit results to the Hugging Face Leaderboard:

### Run Evaluation Script

```powershell
# Run GAIA Validation set (Level 1 tasks)
python evaluation/gaia_submit.py --split validation --level 1 --delay 5
```

### Submit to Leaderboard

1. The script automatically generates a submission file under:
   `evaluation/submissions/submission_validation_level1.jsonl`
2. Navigate to the official [Hugging Face GAIA Leaderboard](https://huggingface.co/spaces/gaia-benchmark/leaderboard).
3. Fill out the submission form:
   - **Submission Name**: `GAIA Agent (Gemini)`
   - **Model / Method Description**: `General-purpose multi-step tool-use agent`
   - **Submission File**: Select `evaluation/submissions/submission_validation_level1.jsonl`
4. Click **Submit**!

---

## 💡 Quota & Rate Limit Management

When evaluating large benchmark splits (such as GAIA 53-task validation), free-tier API keys may hit rate limits (RPM or RPD).

### Strategies to Manage Quota:
1. **Increase Request Delay**: Use `--delay 10` or `--delay 15` in `gaia_submit.py` to space out requests and respect RPM limits.
2. **Use Pay-As-You-Go Key**: Billing-enabled Google AI Studio API keys have significantly higher quota (up to 1,000 RPM).
3. **Switch Model**: Configure `GEMINI_MODEL=gemini-1.5-flash` or `gemini-2.0-flash` which have separate quota pools.
4. **Daily Quota Reset**: Gemini Free Tier daily quota resets every 24 hours at **00:00 UTC** (5:30 AM IST).
5. **Resume Partial Runs**: The generated `.jsonl` submission file retains all completed task results even if interrupted.

---

## 🔒 Security & Sandboxing

- **Input Sanitization**: Rejects prompt injection and dangerous pattern attempts.
- **Python Subprocess Isolation**: Blocks system access modules (`os`, `sys`, `subprocess`, `socket`, `shutil`).
- **File System Protection**: Uses UUID-keyed file paths and strictly restricts path traversal outside designated upload directories.

---

## 🧪 Testing

Run automated unit and tool tests:

```powershell
# Run backend test suite
pytest tests/ -v
```

---

## 📄 License

This project is licensed under the **MIT License**.
