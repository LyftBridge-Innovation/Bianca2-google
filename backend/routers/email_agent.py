"""
Email Agent router — autonomous Gmail reply agent.

Flow:
  User enables agent in Neural Config
    → backend calls gmail.users.watch() on the specified label
    → Gmail publishes to Pub/Sub when a new email lands in that label
    → POST /gmail/webhook receives the Pub/Sub push
    → backend fetches the email, generates a reply via LLM, sends it

Endpoints:
  POST /email-agent/enable          — enable agent for a user
  POST /email-agent/disable         — disable agent for a user
  GET  /email-agent/status          — current agent status
  POST /gmail/webhook               — Pub/Sub push receiver (public)
"""
import base64
import json
import logging
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from firestore_client import get_firestore_client
from tools.gmail import (
    get_label_id,
    watch_gmail,
    stop_gmail_watch,
    list_history,
    get_email_full,
    reply_to_email,
)
from tools.email_agent_engine import generate_reply

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email-agent"])

# Pub/Sub topic name — set GMAIL_PUBSUB_TOPIC in environment
# Format: projects/{project_id}/topics/{topic_name}
_PUBSUB_TOPIC = os.environ.get(
    "GMAIL_PUBSUB_TOPIC",
    f"projects/{os.environ.get('GCP_PROJECT_ID', 'your-project')}/topics/gmail-push",
)

# ── Request models ────────────────────────────────────────────────────────────


class EnableRequest(BaseModel):
    user_id: str
    label_name: str


class DisableRequest(BaseModel):
    user_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _user_ref(user_id: str):
    return get_firestore_client().collection("users").document(user_id)


def _processed_ref(user_id: str, message_id: str):
    key = f"{user_id}_{message_id}"
    return get_firestore_client().collection("email_agent_processed").document(key)


def _is_processed(user_id: str, message_id: str) -> bool:
    return _processed_ref(user_id, message_id).get().exists


def _mark_processed(user_id: str, message_id: str) -> None:
    _processed_ref(user_id, message_id).set({
        "user_id": user_id,
        "message_id": message_id,
        "processed_at": datetime.now(timezone.utc),
    })


def _maybe_renew_watch(user_id: str, label_id: str) -> None:
    """Renew the Gmail watch if it expires within 24 hours."""
    doc = _user_ref(user_id).get()
    if not doc.exists:
        return
    data = doc.to_dict()
    expiry_ms = data.get("email_agent_watch_expiry", 0)
    now_ms = int(time.time() * 1000)
    hours_left = (expiry_ms - now_ms) / (1000 * 3600)

    if hours_left < 24:
        logger.info("Renewing Gmail watch for user %s (%.1f h left)", user_id, hours_left)
        try:
            watch_result = watch_gmail(user_id, label_id, _PUBSUB_TOPIC)
            _user_ref(user_id).update({
                "email_agent_history_id": watch_result["history_id"],
                "email_agent_watch_expiry": watch_result["expiration_ms"],
            })
        except Exception as e:
            logger.error("Watch renewal failed for user %s: %s", user_id, e)


# ── Config endpoints ──────────────────────────────────────────────────────────


@router.post("/email-agent/enable")
def enable_email_agent(body: EnableRequest):
    """
    Enable the email agent for a user.
    Resolves the Gmail label ID, sets up a Gmail watch, and persists config.
    """
    user_id = body.user_id
    label_name = body.label_name.strip()

    if not label_name:
        raise HTTPException(status_code=400, detail="label_name is required")

    # Resolve label name → ID
    label_id = get_label_id(user_id, label_name)
    if not label_id:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Gmail label '{label_name}' not found. "
                "Create it in Gmail first, then try again."
            ),
        )

    # Set up Gmail watch (push notifications via Pub/Sub)
    try:
        watch_result = watch_gmail(user_id, label_id, _PUBSUB_TOPIC)
    except Exception as e:
        logger.error("watch_gmail failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to set up Gmail watch: {e}")

    # Persist agent config on the user document
    _user_ref(user_id).update({
        "email_agent_enabled": True,
        "email_agent_label_name": label_name,
        "email_agent_label_id": label_id,
        "email_agent_history_id": watch_result["history_id"],
        "email_agent_watch_expiry": watch_result["expiration_ms"],
        "email_agent_replied_count": 0,
    })

    expiry_dt = datetime.fromtimestamp(
        watch_result["expiration_ms"] / 1000, tz=timezone.utc
    ).isoformat()
    logger.info("Email agent enabled for user %s (label: %s)", user_id, label_name)

    return {
        "ok": True,
        "label_name": label_name,
        "label_id": label_id,
        "watch_expiry": expiry_dt,
    }


@router.post("/email-agent/disable")
def disable_email_agent(body: DisableRequest):
    """Disable the email agent and stop the Gmail watch."""
    user_id = body.user_id

    try:
        stop_gmail_watch(user_id)
    except Exception as e:
        # Log but don't block — the user doc should still be updated
        logger.warning("stop_gmail_watch failed for user %s: %s", user_id, e)

    _user_ref(user_id).update({
        "email_agent_enabled": False,
        "email_agent_watch_expiry": 0,
    })
    logger.info("Email agent disabled for user %s", user_id)
    return {"ok": True}


@router.get("/email-agent/status")
def get_email_agent_status(user_id: str):
    """Return current email agent status for the given user."""
    doc = _user_ref(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    data = doc.to_dict()
    enabled = data.get("email_agent_enabled", False)
    expiry_ms = data.get("email_agent_watch_expiry", 0)
    now_ms = int(time.time() * 1000)

    expiry_iso = None
    if expiry_ms:
        expiry_iso = datetime.fromtimestamp(
            expiry_ms / 1000, tz=timezone.utc
        ).isoformat()

    return {
        "enabled": enabled,
        "label_name": data.get("email_agent_label_name", ""),
        "watch_expiry": expiry_iso,
        "watch_active": enabled and expiry_ms > now_ms,
        "replied_count": data.get("email_agent_replied_count", 0),
    }


# ── Pub/Sub webhook ───────────────────────────────────────────────────────────


@router.post("/gmail/webhook", include_in_schema=False)
async def gmail_webhook(request: Request):
    """
    Pub/Sub push endpoint — called by Google when new mail arrives in the
    watched label.

    Pub/Sub expects a 2xx response. If we return non-2xx it will retry.
    We always return 200 even on processing errors to avoid retry storms;
    errors are logged instead.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=200, content={"ok": False, "error": "bad json"})

    # Decode Pub/Sub message
    message = payload.get("message", {})
    raw_data = message.get("data", "")
    if not raw_data:
        return JSONResponse(status_code=200, content={"ok": True, "skipped": "no data"})

    try:
        notification = json.loads(base64.b64decode(raw_data).decode("utf-8"))
    except Exception as e:
        logger.error("Failed to decode Pub/Sub message: %s", e)
        return JSONResponse(status_code=200, content={"ok": False, "error": "decode failed"})

    email_address = notification.get("emailAddress")
    new_history_id = str(notification.get("historyId", ""))

    if not email_address or not new_history_id:
        return JSONResponse(status_code=200, content={"ok": True, "skipped": "incomplete notification"})

    # Find user by email address
    db = get_firestore_client()
    users = db.collection("users").where("email", "==", email_address).limit(1).stream()
    user_doc = next(users, None)

    if not user_doc:
        logger.warning("No user found for email %s", email_address)
        return JSONResponse(status_code=200, content={"ok": True, "skipped": "unknown user"})

    user_id = user_doc.id
    user_data = user_doc.to_dict()

    if not user_data.get("email_agent_enabled"):
        return JSONResponse(status_code=200, content={"ok": True, "skipped": "agent disabled"})

    label_id = user_data.get("email_agent_label_id", "")
    stored_history_id = user_data.get("email_agent_history_id", "")

    if not label_id or not stored_history_id:
        return JSONResponse(status_code=200, content={"ok": True, "skipped": "no watch config"})

    # Auto-renew watch if close to expiry
    _maybe_renew_watch(user_id, label_id)

    # Get new message IDs since last processed historyId
    try:
        message_ids = list_history(user_id, stored_history_id, label_id)
    except Exception as e:
        logger.error("list_history failed for user %s: %s", user_id, e)
        # Update historyId anyway to avoid infinite retries on stale ID
        _user_ref(user_id).update({"email_agent_history_id": new_history_id})
        return JSONResponse(status_code=200, content={"ok": False, "error": "history failed"})

    # Update stored historyId immediately (before processing)
    _user_ref(user_id).update({"email_agent_history_id": new_history_id})

    replied = 0
    for msg_id in message_ids:
        if _is_processed(user_id, msg_id):
            logger.debug("Skipping already-processed message %s", msg_id)
            continue

        try:
            email = get_email_full(user_id, msg_id)
        except Exception as e:
            logger.error("get_email_full failed for %s: %s", msg_id, e)
            continue

        # Skip emails sent by the user themselves (avoid loops)
        sender = email.get("from", "")
        if email_address.lower() in sender.lower():
            logger.debug("Skipping self-sent email %s", msg_id)
            _mark_processed(user_id, msg_id)
            continue

        try:
            reply_text = generate_reply(user_id, email)
        except Exception as e:
            logger.error("generate_reply failed for message %s: %s", msg_id, e)
            continue

        try:
            reply_to_email(
                user_id=user_id,
                to=sender,
                subject=email.get("subject", ""),
                body=reply_text,
                thread_id=email.get("thread_id", ""),
                in_reply_to=email.get("message_id_header", ""),
            )
        except Exception as e:
            logger.error("reply_to_email failed for message %s: %s", msg_id, e)
            continue

        _mark_processed(user_id, msg_id)
        replied += 1
        logger.info("Replied to email %s for user %s", msg_id, user_id)

    # Increment lifetime reply counter
    if replied > 0:
        from google.cloud import firestore as _fs
        _user_ref(user_id).update({
            "email_agent_replied_count": _fs.Increment(replied),
        })

    return JSONResponse(status_code=200, content={"ok": True, "replied": replied})
