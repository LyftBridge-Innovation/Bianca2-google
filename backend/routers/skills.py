"""Skills CRUD router — per-user skill upload/list/delete + marketplace."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from models import FirestoreCollections
from skill_matcher import extract_title
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])
fs = FirestoreCollections()

# ── Request/Response models ──────────────────────────────────────────────────


class SkillUploadRequest(BaseModel):
    filename: str
    content: str
    user_id: str


class SkillResponse(BaseModel):
    skill_id: str
    filename: str
    title: str
    created_at: str
    size_bytes: int


# ── CRUD endpoints ───────────────────────────────────────────────────────────

@router.get("/")
def list_skills(user_id: str):
    """List all skills for a user."""
    skills = fs.list_user_skills(user_id)
    return [
        {
            "skill_id": s["skill_id"],
            "filename": s["filename"],
            "title": s["title"],
            "created_at": s["created_at"],
            "size_bytes": s["size_bytes"],
        }
        for s in skills
    ]


@router.post("/upload", response_model=SkillResponse)
def upload_skill(request: SkillUploadRequest):
    """Upload a new skill markdown file."""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Skill content cannot be empty")

    if not request.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are supported")

    title = extract_title(request.content) or request.filename.replace(".md", "")

    skill_data = {
        "skill_id": str(uuid.uuid4()),
        "filename": request.filename,
        "title": title,
        "content": request.content,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": len(request.content.encode("utf-8")),
    }

    fs.create_user_skill(request.user_id, skill_data)

    return SkillResponse(
        skill_id=skill_data["skill_id"],
        filename=skill_data["filename"],
        title=skill_data["title"],
        created_at=skill_data["created_at"],
        size_bytes=skill_data["size_bytes"],
    )


@router.delete("/{skill_id}")
def delete_skill(skill_id: str, user_id: str):
    """Delete a skill by ID."""
    success = fs.delete_user_skill(user_id, skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "deleted", "skill_id": skill_id}


# ── Marketplace endpoints ────────────────────────────────────────────────────

@router.post("/publish")
def publish_skill(user_id: str, skill_id: str):
    """Publish a user's skill to the marketplace."""
    # Get the user's skill
    user_skills = fs.list_user_skills(user_id)
    skill = next((s for s in user_skills if s["skill_id"] == skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Get user info
    user = fs.get_user(user_id)

    # Extract description (first non-title paragraph)
    lines = skill["content"].split("\n")
    description = ""
    for line in lines[1:]:  # Skip title line
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            description = stripped
            break

    # Publish to marketplace
    public_skill = {
        "title": skill["title"],
        "description": description[:200],  # Limit to 200 chars
        "content": skill["content"],
        "author_user_id": user_id,
        "author_name": user.full_name or user.email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    public_id = fs.create_public_skill(public_skill)

    logger.info(f"User {user_id} published skill '{skill['title']}' to marketplace")

    return {"public_skill_id": public_id, "title": skill["title"]}


@router.get("/marketplace")
def get_marketplace_skills():
    """List all published skills from the marketplace."""
    skills = fs.list_public_skills(limit=100)
    return {"skills": skills}


@router.post("/install-from-marketplace")
def install_from_marketplace(user_id: str, public_skill_id: str):
    """Install a marketplace skill to user's collection."""
    # Get marketplace skill
    public_skill = fs.get_public_skill(public_skill_id)
    if not public_skill:
        raise HTTPException(status_code=404, detail="Marketplace skill not found")

    # Create user skill copy
    user_skill = {
        "skill_id": str(uuid.uuid4()),
        "filename": f"{public_skill['title'].lower().replace(' ', '-')}.md",
        "title": public_skill["title"],
        "content": public_skill["content"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": len(public_skill["content"].encode("utf-8")),
        "source": "marketplace",
    }
    fs.create_user_skill(user_id, user_skill)

    # Increment install counter
    fs.increment_install_count(public_skill_id)

    logger.info(f"User {user_id} installed skill '{public_skill['title']}' from marketplace")

    return {"skill_id": user_skill["skill_id"], "title": public_skill["title"]}


@router.delete("/unpublish/{public_skill_id}")
def unpublish_skill(public_skill_id: str, user_id: str):
    """Remove a skill from marketplace (author only)."""
    public_skill = fs.get_public_skill(public_skill_id)
    if not public_skill:
        raise HTTPException(status_code=404, detail="Marketplace skill not found")

    if public_skill["author_user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the author can unpublish this skill")

    fs.delete_public_skill(public_skill_id)
    logger.info(f"User {user_id} unpublished skill '{public_skill['title']}' from marketplace")

    return {"message": "Skill unpublished"}
