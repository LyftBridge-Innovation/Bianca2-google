"""Skills CRUD router — per-user skill upload/list/delete."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from models import FirestoreCollections
from skill_matcher import extract_title
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/skills", tags=["skills"])
fs = FirestoreCollections()


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


# ── Endpoints ────────────────────────────────────────────────────────────────

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
