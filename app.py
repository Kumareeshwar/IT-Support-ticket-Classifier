import os
from typing import TypedDict
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from langgraph.graph import END, START, StateGraph

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from pipeline.logger import get_logger
from pipeline.classifier import classify_prompt
from pipeline.injection_checker import injection_checker
from pipeline.pii_detection import pii_reduct

MODEL_NAME = os.getenv("GROQ_MODEL", "llama3-8b-8192")
logger = get_logger(__name__)


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing. Add it to .env at project root.")
    return Groq(api_key=api_key)


class TicketState(TypedDict, total=False):
    user_prompt: str
    redacted_text: str
    injection_status: str
    is_safe: bool
    classification: dict
    final_response: str


def pii_node(state: TicketState) -> TicketState:
    logger.info("graph: pii_node start")
    logger.debug("graph: user_prompt=%r", state.get("user_prompt"))
    pii_result = pii_reduct(state["user_prompt"])
    logger.info("graph: pii_node pii_reduction=%s entities=%s",
                pii_result.get("pii_reduction") or pii_result.get("pii_detection"),
                pii_result.get("entities_found") or pii_result.get("entitites_found"))
    return {"redacted_text": pii_result["redacted_text"]}


def injection_node(state: TicketState) -> TicketState:
    logger.info("graph: injection_node start")
    result = injection_checker(state["redacted_text"])
    logger.info("graph: injection_node result=%s", result)
    return {
        "injection_status": result.get("injection_status", "error"),
        "is_safe": result.get("is_safe", False),
    }


def classifier_node(state: TicketState) -> TicketState:
    logger.info("graph: classifier_node start")
    if not state.get("is_safe", False):
        logger.info("graph: classifier_node skipped (unsafe)")
        return {}
    classification = classify_prompt(state["redacted_text"])
    logger.info("graph: classifier_node result=%s", classification)
    return {"classification": classification}


def route_after_injection(state: TicketState) -> str:
    route = "classifier_node" if state.get("is_safe", False) else "response_node"
    logger.info("graph: route_after_injection -> %s", route)
    return route


def response_node(state: TicketState) -> TicketState:
    logger.info("graph: response_node start")
    if not state.get("is_safe", False):
        return {
            "final_response": "Your request was blocked because it appears to contain a prompt injection attempt."
        }

    classification = state.get("classification", {})
    sentiment = classification.get("sentiment", "neutral")
    escalation_team = classification.get("escalation_team", "support")
    query_type = classification.get("query_type", "general_support")
    priority = classification.get("priority", "medium")

    system_prompt = """
You are an IT support assistant.
Reply in 2-4 sentences with:
1) A concise acknowledgement.
2) The likely team for escalation.
3) A practical next step.
Keep the tone professional and clear.
"""

    user_context = (
        f"User prompt: {state['redacted_text']}\n"
        f"Sentiment: {sentiment}\n"
        f"Query Type: {query_type}\n"
        f"Escalation Team: {escalation_team}\n"
        f"Priority: {priority}"
    )

    response = _get_client().chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_context},
        ],
        temperature=0.2,
        max_tokens=180,
    )

    final_response = response.choices[0].message.content.strip()
    logger.info("graph: response_node done")
    return {"final_response": final_response}


def build_graph():
    graph = StateGraph(TicketState)
    graph.add_node("pii_node", pii_node)
    graph.add_node("injection_node", injection_node)
    graph.add_node("classifier_node", classifier_node)
    graph.add_node("response_node", response_node)

    graph.add_edge(START, "pii_node")
    graph.add_edge("pii_node", "injection_node")
    graph.add_conditional_edges(
        "injection_node",
        route_after_injection,
        {"classifier_node": "classifier_node", "response_node": "response_node"},
    )
    graph.add_edge("classifier_node", "response_node")
    graph.add_edge("response_node", END)
    return graph.compile()


ticket_graph = build_graph()

st.title("IT Support Agent")
prompt = st.text_area("Enter your prompt")

if st.button("Submit") and prompt.strip():
    result = ticket_graph.invoke({"user_prompt": prompt.strip()})
    st.write(result.get("final_response", "Unable to generate a response."))
