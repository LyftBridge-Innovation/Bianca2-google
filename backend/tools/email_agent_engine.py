"""
LLM pipeline for generating autonomous email replies.

Loads Bianca's full system prompt (identity + knowledge + values) and
generates a professional plain-text reply to an incoming email.
Supports both Claude (Anthropic) and Gemini (Vertex AI) based on settings.
"""
import os
import logging

logger = logging.getLogger(__name__)


def generate_reply(user_id: str, email: dict) -> str:
    """
    Generate a professional reply to an incoming email.

    Args:
        user_id: The user on whose behalf the reply is written.
        email:   Dict with keys: from, subject, date, body (from get_email_full).

    Returns:
        Plain text reply string ready to send.
    """
    from request_context import current_user_id
    from prompts import _build_identity_block
    from knowledge_loader import build_knowledge_block
    from values import build_values_block
    from settings_loader import load_settings
    from models import FirestoreCollections

    current_user_id.set(user_id)
    settings = load_settings()

    # Resolve the user's display name for the sign-off
    try:
        db = FirestoreCollections()
        user = db.get_user(user_id)
        user_name = user.full_name if user and user.full_name else "Bianca"
    except Exception:
        user_name = "Bianca"

    ai_name = settings.get("ai_name", "Bianca")

    # Build the full system prompt: identity + knowledge + values
    system_prompt = "\n\n".join(
        block for block in [
            _build_identity_block(),
            build_knowledge_block(),
            build_values_block(),
        ] if block and block.strip()
    )

    # Build the email context block
    sender = email.get("from", "")
    subject = email.get("subject", "(no subject)")
    date = email.get("date", "")
    body = (email.get("body") or "").strip()

    user_message = (
        f"You have received an email on behalf of {user_name}. "
        f"Read it carefully and write a professional reply.\n\n"
        f"--- INCOMING EMAIL ---\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Date: {date}\n\n"
        f"{body}\n"
        f"--- END EMAIL ---\n\n"
        f"Write a reply now. Rules:\n"
        f"- Plain text only — no markdown, no bullet points, no bold\n"
        f"- No subject line — start directly with the reply body\n"
        f"- Keep it concise and professional\n"
        f"- Sign off naturally as {ai_name}"
    )

    model: str = settings.get("model", "claude-sonnet-4-5-20250929")

    if model.startswith("claude"):
        return _reply_via_claude(model, system_prompt, user_message, settings)
    else:
        return _reply_via_gemini(model, system_prompt, user_message, settings)


def _reply_via_claude(
    model: str, system_prompt: str, user_message: str, settings: dict
) -> str:
    import anthropic
    api_key = settings.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("No Anthropic API key configured")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


def _reply_via_gemini(
    model: str, system_prompt: str, user_message: str, settings: dict
) -> str:
    from langchain_google_vertexai import ChatVertexAI
    from langchain_core.messages import SystemMessage, HumanMessage
    from config import GCP_PROJECT_ID, GCP_LOCATION

    llm = ChatVertexAI(
        model=model or "gemini-2.5-flash",
        project=GCP_PROJECT_ID,
        location=GCP_LOCATION,
        temperature=float(settings.get("temperature", 0.7)),
    )
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])
    return response.content.strip()
