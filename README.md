IT Support Ticket Classifier
An AI-powered support ticket classification system built with LangGraph, Groq, and Streamlit. Implements a multi-stage pipeline with security, safety, and observability layers — designed to reflect production-grade AI system design.

What It Does
Takes a raw user support ticket and runs it through a series of intelligent stages:

PII Redaction — Detects and masks sensitive information (credit cards, emails, phone numbers, names) before any LLM sees the data
Prompt Injection Detection — Checks if the user is attempting to manipulate the AI
Ticket Classification — Classifies the ticket across 4 dimensions using an LLM
Cost Tracking — Calculates token usage and estimated cost per request


Classification Output
Each ticket is classified across:
DimensionOptionsSentimentAngry, Neutral, HappyPriorityLow, Medium, High, CriticalCategoryBilling, Technical, Account, Delivery, OtherAssigned TeamFinance, IT Support, Logistics, Customer Care

Pipeline Architecture
User Input
    ↓
PII Redaction (presidio-analyzer)
    ↓
Prompt Injection Check (Groq LLM)
    ↓ safe              ↓ injection detected
Ticket Classification   Fallback Handler
    ↓
Cost Calculation
    ↓
Streamlit UI
Built using LangGraph for stateful graph-based orchestration — each stage is a node, data flows through a shared state dictionary, and routing is handled via conditional edges.

Tech Stack

LangGraph — multi-stage pipeline orchestration
Groq (LLaMA3) — LLM inference for injection detection and classification
Presidio Analyzer/Anonymizer — PII detection and masking
Streamlit — frontend UI
Python — core language
Pydantic — structured output validation
python-dotenv — environment variable management


Project Structure
IT Support Agent/
├── app.py                      # Streamlit UI entry point
├── pipeline/
│   ├── graph.py                # LangGraph pipeline definition
│   ├── pii_detection.py        # PII redaction node
│   ├── injection_checker.py    # Prompt injection check node
│   ├── classifier.py           # Ticket classification node
│   ├── cost_calculator.py      # Token cost tracking
│   └── logger.py               # Pipeline logging
├── .env                        # API keys (not committed)
├── requirements.txt
└── README.md


Key Design Decisions

PII redacted before LLM — sensitive data never reaches the model
Temperature set to 0 — deterministic outputs for classification tasks
JSON output validation — all 4 classification keys verified before passing forward
Fallback on injection — pipeline stops cleanly instead of crashing
Token cost tracked per request — production observability habit
