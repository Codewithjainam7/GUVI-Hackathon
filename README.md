# 🍯 Agentic Honeypot for Scam Detection & Intelligence Extraction

> **Production-Ready Autonomous AI Honeypot with Hybrid LLM Architecture**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

---

## 📋 Problem Statement

Online scams are increasingly sophisticated, targeting vulnerable populations through messaging platforms, emails, and social media. Traditional detection methods are reactive and fail to:

- **Engage scammers** to waste their time and resources
- **Extract intelligence** (UPI IDs, bank accounts, phone numbers)
- **Build scammer profiles** for law enforcement
- **Explain decisions** for legal proceedings

This project creates an **autonomous AI honeypot** that actively engages scammers, gathers evidence, and protects potential victims.

---

## 🏗️ System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AGENTIC HONEYPOT SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐    ┌─────────────────────────────────────────────────────┐   │
│  │   Incoming   │    │                 DETECTION ENGINE                     │   │
│  │   Message    │───▶│  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │   │
│  └──────────────┘    │  │Rule-Based │  │  Gemini   │  │   Ensemble    │   │   │
│                      │  │  Layer 1  │─▶│  Layer 2  │─▶│ Risk Scoring  │   │   │
│                      │  └───────────┘  └───────────┘  └───────────────┘   │   │
│                      └─────────────────────────┬───────────────────────────┘   │
│                                                │                                │
│                                                ▼                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         AGENTIC ORCHESTRATOR                             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   Planner   │  │ Conversation│  │ Extraction  │  │  Evaluator  │    │   │
│  │  │   Agent     │  │   Agent     │  │   Agent     │  │   Agent     │    │   │
│  │  │  (Gemini)   │  │  (Gemini)   │  │(Local LLaMA)│  │  (Gemini)   │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                │                                │
│                    ┌───────────────────────────┼───────────────────────────┐   │
│                    ▼                           ▼                           ▼   │
│  ┌─────────────────────┐  ┌─────────────────────────┐  ┌─────────────────┐    │
│  │    PERSONA ENGINE   │  │   INTELLIGENCE STORE    │  │  SAFETY LAYER   │    │
│  │  • Senior Citizen   │  │  • Scammer Profiles     │  │  • Kill Switch  │    │
│  │  • Student          │  │  • UPI/Bank Accounts    │  │  • Ethics Guard │    │
│  │  • Business Owner   │  │  • Network Analysis     │  │  • Auto-Stop    │    │
│  └─────────────────────┘  └─────────────────────────┘  └─────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Hybrid LLM Architecture

This system uses a **dual-LLM approach** for optimal performance, privacy, and cost:

### ☁️ Gemini API (Cloud) — *The Reasoning Brain*

| Responsibility | Why Gemini? |
|---------------|-------------|
| Scam Classification | Superior reasoning capabilities |
| Risk Analysis | Complex multi-factor evaluation |
| Agent Planning | Strategic decision making |
| Persona Selection | Nuanced behavioral matching |
| Response Generation | Natural, convincing dialogue |
| Explainability | Clear reasoning chains |

### 🏠 Local LLaMA (On-Premise) — *The Execution Hands*

| Responsibility | Why Local? |
|---------------|------------|
| Entity Extraction | Privacy — raw data never leaves |
| NER Processing | No API costs for bulk processing |
| Summarization | Fast, repeated operations |
| Deduplication | Consistent, deterministic output |
| PII Handling | Compliance & security |

### 🔀 Model Router

```python
# Intelligent routing based on task type
ROUTING_CONFIG = {
    "scam_classification": {"primary": "gemini", "fallback": None},
    "entity_extraction":   {"primary": "local_llama", "fallback": "gemini"},
    "response_generation": {"primary": "gemini", "fallback": "local_llama"},
    "summarization":       {"primary": "local_llama", "fallback": "gemini"},
}
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Gemini API Key
- Ollama (for local LLaMA)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/agentic-honeypot.git
cd agentic-honeypot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start local LLaMA (using Ollama)
ollama pull llama3.1:8b
ollama serve

# Run the application
uvicorn app.main:app --reload
```

### Docker Deployment

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
honeypot/
├── app/
│   ├── api/              # FastAPI routes (thin layer)
│   ├── orchestrator/     # Model routing & flow control
│   ├── agents/           # Planner / Conversation / Extraction / Evaluator
│   ├── personas/         # Persona configurations & prompts
│   ├── detectors/        # Scam detection (rule-based + ML)
│   ├── extractors/       # Entity extraction (Local LLaMA)
│   ├── llm/              # Gemini + Local LLaMA clients
│   ├── memory/           # Short-term & long-term memory
│   ├── scoring/          # Risk & confidence scoring
│   ├── safety/           # Ethics guardrails & kill-switches
│   ├── schemas/          # Pydantic models
│   ├── utils/            # Helper functions
│   └── main.py           # Application entry point
├── tests/                # Test suite
├── docker-compose.yml    # Container orchestration
├── Dockerfile            # Application container
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/analyze-message` | POST | Analyze a message for scam detection |
| `/api/v1/continue-conversation` | POST | Continue honeypot conversation |
| `/api/v1/intelligence` | GET | Retrieve extracted intelligence |
| `/api/v1/scammer-profile/{id}` | GET | Get scammer profile |

### Example Response

```json
{
  "scam_detected": true,
  "risk_score": 0.94,
  "persona_used": "senior_citizen",
  "models_used": ["gemini", "local_llama"],
  "extracted_intel": {
    "upi_ids": ["scammer@upi"],
    "phone_numbers": ["+91-9876543210"],
    "bank_accounts": []
  },
  "why_flagged": [
    "Urgency language detected: 'act now or lose'",
    "Payment request identified",
    "Impersonation of authority figure"
  ],
  "conversation_state": "intelligence_extraction",
  "response": "Oh dear, I'm not very good with these online things..."
}
```

---

## ⚖️ Ethical & Legal Disclaimer

> [!CAUTION]
> **This software is designed for research, education, and authorized security testing only.**

### ⚠️ Important Guidelines

1. **Authorization Required**: Only use this system with explicit authorization from relevant parties
2. **No Real Payments**: The system is designed to NEVER make or facilitate real payments
3. **Data Protection**: All extracted intelligence must be handled according to applicable privacy laws
4. **Law Enforcement**: Coordinate with appropriate authorities when dealing with criminal activity
5. **Victim Protection**: Never use this system in ways that could harm potential scam victims

### Legal Compliance

- This tool does NOT encourage or facilitate illegal activity
- Users are responsible for ensuring compliance with local laws
- The developers assume no liability for misuse of this software

---

## 🛡️ Safety Features

- **Automatic Kill-Switch**: Terminates engagement if safety thresholds are breached
- **Max Engagement Depth**: Configurable limit on conversation length
- **Prompt Injection Detection**: Protects against adversarial inputs
- **PII Redaction**: Automatic masking of sensitive information
- **Audit Logging**: Complete trail of all system decisions

---

## 📊 Metrics & Observability

- Structured JSON logging
- Prometheus metrics endpoint
- Model latency tracking
- Token usage & cost tracking
- Scam detection accuracy metrics

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting PRs.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Google Gemini API for advanced reasoning capabilities
- Meta LLaMA for local inference
- The open-source security research community

---

**Built with ❤️ to make the internet safer**
