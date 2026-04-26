"""User data router — Firestore-backed CRUD for contacts, world model, and access control."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/user-data", tags=["user-data"])


def _db():
    from firestore_client import get_firestore_client
    return get_firestore_client()


# ── Pydantic models ───────────────────────────────────────────────────────────

class ContactItem(BaseModel):
    firstName: str
    lastName: str = ""
    email: str = ""
    phone: str = ""
    title: str = ""


class ContactRequest(ContactItem):
    user_id: str


class WorldModelEntry(BaseModel):
    category: str
    title: str
    content: str = ""
    dataType: str = "fact"
    enabled: bool = True


class WorldModelRequest(WorldModelEntry):
    user_id: str


class AccessControlPayload(BaseModel):
    user_id: str
    authorizations: list[str] = []
    constraints: list[str] = []


# ── Contacts ─────────────────────────────────────────────────────────────────

@router.get("/contacts")
def list_contacts(user_id: str = Query(...)):
    """Return all contacts for a user."""
    try:
        docs = (
            _db()
            .collection("users")
            .document(user_id)
            .collection("contacts")
            .stream()
        )
        return {"contacts": [{"id": d.id, **d.to_dict()} for d in docs]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/contacts")
def add_contact(body: ContactRequest):
    """Add a contact for a user."""
    contact_id = str(uuid.uuid4())
    data = body.model_dump(exclude={"user_id"})
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    try:
        (
            _db()
            .collection("users")
            .document(body.user_id)
            .collection("contacts")
            .document(contact_id)
            .set(data)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "id": contact_id}


@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: str, user_id: str = Query(...)):
    """Delete a contact by ID."""
    try:
        (
            _db()
            .collection("users")
            .document(user_id)
            .collection("contacts")
            .document(contact_id)
            .delete()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


# ── World Model ───────────────────────────────────────────────────────────────

@router.get("/world-model")
def list_world_model(user_id: str = Query(...)):
    """Return all world model entries for a user."""
    try:
        docs = (
            _db()
            .collection("users")
            .document(user_id)
            .collection("world_model")
            .stream()
        )
        return {"entries": [{"id": d.id, **d.to_dict()} for d in docs]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/world-model")
def add_world_model_entry(body: WorldModelRequest):
    """Add a world model entry for a user."""
    entry_id = str(uuid.uuid4())
    data = body.model_dump(exclude={"user_id"})
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    try:
        (
            _db()
            .collection("users")
            .document(body.user_id)
            .collection("world_model")
            .document(entry_id)
            .set(data)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "id": entry_id}


@router.delete("/world-model/{entry_id}")
def delete_world_model_entry(entry_id: str, user_id: str = Query(...)):
    """Delete a world model entry by ID."""
    try:
        (
            _db()
            .collection("users")
            .document(user_id)
            .collection("world_model")
            .document(entry_id)
            .delete()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


@router.patch("/world-model/{entry_id}")
def toggle_world_model_entry(entry_id: str, user_id: str = Query(...), enabled: bool = Query(...)):
    """Toggle the enabled flag on a world model entry."""
    try:
        (
            _db()
            .collection("users")
            .document(user_id)
            .collection("world_model")
            .document(entry_id)
            .update({"enabled": enabled})
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


# ── Access Control ────────────────────────────────────────────────────────────

@router.get("/access-control")
def get_access_control(user_id: str = Query(...)):
    """Return the access control lists (authorizations + constraints) for a user."""
    try:
        doc = (
            _db()
            .collection("users")
            .document(user_id)
            .collection("access_control")
            .document("config")
            .get()
        )
        if doc.exists:
            data = doc.to_dict()
            return {
                "authorizations": data.get("authorizations", []),
                "constraints": data.get("constraints", []),
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"authorizations": [], "constraints": []}


@router.put("/access-control")
def save_access_control(body: AccessControlPayload):
    """Persist the full access control config for a user (replaces previous)."""
    try:
        (
            _db()
            .collection("users")
            .document(body.user_id)
            .collection("access_control")
            .document("config")
            .set({
                "authorizations": body.authorizations,
                "constraints": body.constraints,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}
