"""Gmail tools — read, send, and draft emails via gws CLI.

Function signatures are identical to the original google-api-python-client
implementation so langchain_tools.py and voice_pipeline/tool_dispatcher.py
work without any changes.

The lower section adds agent-only helpers that use googleapiclient directly
because gws CLI doesn't expose watch / history / label APIs:
  get_label_id, watch_gmail, stop_gmail_watch, list_history,
  get_email_full, reply_to_email
"""
import base64
import json
import logging
from email.mime.text import MIMEText
from fastapi import HTTPException
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from tools.gws_client import execute, GWSError
from token_manager import get_access_token

logger = logging.getLogger(__name__)


def _gmail_service(user_id: str):
    """Return an authenticated Gmail API service for the given user."""
    token = get_access_token(user_id)
    creds = Credentials(token=token)
    return build("gmail", "v1", credentials=creds)


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


# ── Email Agent helpers (use googleapiclient directly) ────────────────────────


def get_label_id(user_id: str, label_name: str) -> str | None:
    """Resolve a Gmail label name to its ID. Returns None if not found."""
    service = _gmail_service(user_id)
    result = service.users().labels().list(userId="me").execute()
    for label in result.get("labels", []):
        if label.get("name", "").lower() == label_name.lower():
            return label["id"]
    return None


def watch_gmail(user_id: str, label_id: str, pubsub_topic: str) -> dict:
    """
    Set up Gmail push notifications via Pub/Sub for a specific label.
    Returns {"history_id": str, "expiration_ms": int}.
    Watch expires after 7 days — call again to renew.
    """
    service = _gmail_service(user_id)
    result = service.users().watch(
        userId="me",
        body={
            "topicName": pubsub_topic,
            "labelIds": [label_id],
            "labelFilterBehavior": "INCLUDE",
        },
    ).execute()
    return {
        "history_id": str(result["historyId"]),
        "expiration_ms": int(result["expiration"]),
    }


def stop_gmail_watch(user_id: str) -> None:
    """Stop Gmail push notifications for this user."""
    service = _gmail_service(user_id)
    service.users().stop(userId="me").execute()


def list_history(user_id: str, start_history_id: str, label_id: str) -> list[str]:
    """
    Return message IDs added to label_id since start_history_id.
    Uses gmail.users.history.list — handles pagination automatically.
    """
    service = _gmail_service(user_id)
    message_ids: list[str] = []
    page_token = None

    while True:
        kwargs: dict = {
            "userId": "me",
            "startHistoryId": start_history_id,
            "labelId": label_id,
            "historyTypes": ["messageAdded"],
        }
        if page_token:
            kwargs["pageToken"] = page_token

        try:
            result = service.users().history().list(**kwargs).execute()
        except Exception as e:
            # historyId too old → 404; caller should treat as no new messages
            logger.warning("list_history error (may be stale historyId): %s", e)
            break

        for history in result.get("history", []):
            for added in history.get("messagesAdded", []):
                msg = added.get("message", {})
                if label_id in msg.get("labelIds", []):
                    msg_id = msg["id"]
                    if msg_id not in message_ids:
                        message_ids.append(msg_id)

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return message_ids


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text from a Gmail message payload."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        # Recurse into nested multipart
        for part in payload["parts"]:
            text = _extract_body(part)
            if text:
                return text
    elif payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def get_email_full(user_id: str, message_id: str) -> dict:
    """
    Fetch a full email with all headers needed for threading.
    Returns: id, thread_id, subject, from, to, date, message_id_header,
             references, body.
    """
    service = _gmail_service(user_id)
    m = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    headers = {
        h["name"]: h["value"]
        for h in m.get("payload", {}).get("headers", [])
    }
    body = _extract_body(m.get("payload", {}))

    return {
        "id": m["id"],
        "thread_id": m.get("threadId", ""),
        "subject": headers.get("Subject", ""),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "message_id_header": headers.get("Message-ID", ""),
        "references": headers.get("References", ""),
        "body": body,
    }


def reply_to_email(
    user_id: str,
    to: str,
    subject: str,
    body: str,
    thread_id: str,
    in_reply_to: str,
) -> dict:
    """
    Send a reply that stays in the same Gmail thread.
    Sets In-Reply-To and References headers so the reply threads correctly.
    """
    service = _gmail_service(user_id)

    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to
    message["subject"] = reply_subject
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    result = service.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": thread_id},
    ).execute()

    return {
        "id": result.get("id", ""),
        "thread_id": result.get("threadId", ""),
        "status": "sent",
    }
