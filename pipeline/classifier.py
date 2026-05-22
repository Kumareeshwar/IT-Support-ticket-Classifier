import json
import os
from typing import Dict
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from pipeline.logger import get_logger

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

MODEL_NAME = os.getenv("GROQ_MODEL", "llama3-8b-8192")
logger = get_logger(__name__)


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing. Add it to .env at project root.")
    return Groq(api_key=api_key)


TEAM_KEYWORDS = {
    "distribution": [
        "delivery",
        "shipment",
        "dispatch",
        "courier",
        "tracking",
        "distribution",
    ],
    "support": [
        "error",
        "issue",
        "not working",
        "unable",
        "help",
        "support",
        "bug",
        "fail",
    ],
    "billing": [
        "invoice",
        "refund",
        "charged",
        "payment",
        "billing",
        "price",
        "subscription",
    ],
    "access_management": [
        "password",
        "login",
        "signin",
        "sign in",
        "access",
        "permission",
        "account locked",
    ],
}


def _fallback_sentiment(text: str) -> str:
    lower_text = text.lower()

    negative_words = [
        "angry",
        "frustrated",
        "bad",
        "worst",
        "terrible",
        "urgent",
        "issue",
        "error",
        "failed",
    ]
    positive_words = ["great", "good", "thanks", "awesome", "happy", "excellent"]

    negative_hits = sum(word in lower_text for word in negative_words)
    positive_hits = sum(word in lower_text for word in positive_words)

    if negative_hits > positive_hits:
        return "negative"
    if positive_hits > negative_hits:
        return "positive"
    return "neutral"


def _fallback_team(text: str) -> str:
    lower_text = text.lower()

    for team, keywords in TEAM_KEYWORDS.items():
        if any(keyword in lower_text for keyword in keywords):
            return team
    return "support"


def classify_prompt(safe_redacted_text: str) -> Dict[str, str]:
    """
    Classify a prompt after it has passed:
    1) injection_checker
    2) pii_detection

    Returns:
    {
      "sentiment": "positive|neutral|negative",
      "query_type": "<short label>",
      "escalation_team": "support|distribution|billing|access_management",
      "priority": "low|medium|high"
    }
    """
    system_prompt = """
You are an IT support triage classifier.
Given one user prompt that is already security-checked and PII-redacted, return ONLY valid JSON.

Rules:
- sentiment must be one of: positive, neutral, negative
- query_type should be a short snake_case label
- escalation_team must be one of: support, distribution, billing, access_management
- priority must be one of: low, medium, high
- Output strict JSON only (no markdown, no extra text).
"""

    try:
        logger.info("classifier: start")
        logger.debug("classifier: safe_redacted_text=%r", safe_redacted_text)
        client = _get_client()
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": safe_redacted_text},
            ],
            temperature=0,
            max_tokens=140,
        )

        raw_output = response.choices[0].message.content.strip()
        logger.info("classifier: raw_model_output=%r", raw_output)
        parsed = json.loads(raw_output)

        sentiment = parsed.get("sentiment", "neutral").lower()
        if sentiment not in {"positive", "neutral", "negative"}:
            sentiment = _fallback_sentiment(safe_redacted_text)

        escalation_team = parsed.get("escalation_team", "support").lower()
        if escalation_team not in {
            "support",
            "distribution",
            "billing",
            "access_management",
        }:
            escalation_team = _fallback_team(safe_redacted_text)

        query_type = parsed.get("query_type", "general_support")
        if not isinstance(query_type, str) or not query_type.strip():
            query_type = "general_support"

        priority = parsed.get("priority", "medium").lower()
        if priority not in {"low", "medium", "high"}:
            priority = "medium"

        payload = {
            "sentiment": sentiment,
            "query_type": query_type,
            "escalation_team": escalation_team,
            "priority": priority,
        }
        logger.info("classifier: result=%s", payload)
        return payload

    except Exception as error:
        logger.exception("classifier: error")
        return {
            "sentiment": _fallback_sentiment(safe_redacted_text),
            "query_type": "general_support",
            "escalation_team": _fallback_team(safe_redacted_text),
            "priority": "medium",
            "error": str(error),
        }


if __name__ == "__main__":
    sample = "I am very frustrated because my shipment is delayed and nobody is helping."
    print(classify_prompt(sample))
