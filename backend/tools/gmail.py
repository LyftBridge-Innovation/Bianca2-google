"""Gmail tools — read, send, and draft emails via gws CLI.

Function signatures are identical to the original google-api-python-client
implementation so langchain_tools.py and voice_pipeline/tool_dispatcher.py
work without any changes.
"""
import base64
import json
import logging
from fastapi import HTTPException
from tools.gws_client import execute, GWSError
from token_manager import get_access_token

logger = logging.getLogger(__name__)


def list_emails(user_id: str, max_results: int = 10) -> list[dict]:
    """Returns recent emails: id, subject, sender, date, snippet."""
    try:
        token = get_access_token(user_id)
        result = execute([
            "gmail", "users", "messages", "list",
            "--params", json.dumps({"userId": "me", "maxResults": max_results}),
        ], access_token=token)
        messages = result.get("messages", [])

        emails = []
        for msg in messages:
            m = execute([
                "gmail", "users", "messages", "get",
                "--params", json.dumps({
                    "userId": "me",
                    "id": msg["id"],
                    "format": "metadata",
                }),
            ], access_token=token)
            headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
            emails.append({
                "id": m["id"],
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": m.get("snippet", ""),
            })
        return emails
    except GWSError as e:
        logger.error("list_emails failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def get_email(user_id: str, email_id: str) -> dict:
    """Returns full email body and metadata for a given email ID."""
    try:
        token = get_access_token(user_id)
        m = execute([
            "gmail", "users", "messages", "get",
            "--params", json.dumps({"userId": "me", "id": email_id, "format": "full"}),
        ], access_token=token)
        headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}

        body = ""
        payload = m["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
        elif "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        return {
            "id": m["id"],
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body,
        }
    except GWSError as e:
        logger.error("get_email failed: %s", e)
        status = 404 if "not found" in str(e).lower() else 500
        raise HTTPException(status_code=status, detail=str(e))


def send_email(user_id: str, to: str, subject: str, body: str) -> dict:
    """Sends an email on behalf of the user. Only call when user explicitly confirms."""
    try:
        token = get_access_token(user_id)
        result = execute([
            "gmail", "+send",
            "--to", to,
            "--subject", subject,
            "--body", body,
        ], access_token=token)
        return {"id": result.get("id", ""), "status": "sent"}
    except GWSError as e:
        logger.error("send_email failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def draft_email(user_id: str, to: str, subject: str, body: str) -> dict:
    """Saves an email as a draft. Default action — does NOT send."""
    try:
        token = get_access_token(user_id)
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        result = execute([
            "gmail", "users", "drafts", "create",
            "--params", json.dumps({"userId": "me"}),
            "--json", json.dumps({"message": {"raw": raw}}),
        ], access_token=token)
        return {"id": result.get("id", ""), "status": "drafted"}
    except GWSError as e:
        logger.error("draft_email failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
