"""Cadet photo upload, retrieval, and deletion routes."""
from fastapi import Depends, HTTPException, UploadFile, File, Query, Header
from fastapi.responses import Response
from typing import Optional
from datetime import datetime, timezone
import uuid
import logging

from database import db, api_router
from permissions import get_current_user
from file_storage import put_object, get_object

logger = logging.getLogger(__name__)

APP_NAME = "cap-encampment"
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


@api_router.post("/participants/{participant_id}/photo")
async def upload_cadet_photo(
    participant_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """Upload a photo for a cadet. Accessible to parents (for their own cadet) and roster editors."""
    # Verify participant exists
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Check permissions
    user_role = user.get("role", "")
    is_parent = user_role == "parent"
    can_edit_roster = user_role in [
        "commander", "dcp", "executive_staff", "exec_cadre",
        "staff", "plans_programs", "cadre", "finance",
        "squadron_commander", "training_officer"
    ]

    if is_parent:
        # Parents can only upload for their linked cadet
        linked_capid = user.get("linked_capid", "")
        if participant.get("capid") != linked_capid:
            raise HTTPException(status_code=403, detail="You can only upload a photo for your cadet")
    elif not can_edit_roster:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: JPEG, PNG, WEBP"
        )

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail="Photo must be under 5MB")

    # Determine extension
    ext_map = {
        "image/jpeg": "jpg", "image/png": "png",
        "image/webp": "webp", "image/heic": "heic", "image/heif": "heif"
    }
    ext = ext_map.get(content_type, "jpg")
    photo_id = str(uuid.uuid4())
    storage_path = f"{APP_NAME}/cadet-photos/{participant_id}/{photo_id}.{ext}"

    # Upload to object storage
    result = put_object(storage_path, data, content_type)
    actual_path = result.get("path", storage_path)

    # Update participant with photo path
    await db.participants.update_one(
        {"id": participant_id},
        {"$set": {
            "photo_path": actual_path,
            "photo_content_type": content_type,
            "photo_uploaded_at": datetime.now(timezone.utc).isoformat(),
            "photo_uploaded_by": user.get("id", "")
        }}
    )

    logger.info(f"Photo uploaded for participant {participant_id} by {user.get('name', 'unknown')}")
    return {
        "message": "Photo uploaded successfully",
        "photo_path": actual_path,
        "participant_id": participant_id
    }


@api_router.get("/participants/{participant_id}/photo")
async def get_cadet_photo(
    participant_id: str,
    auth: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """Serve a cadet's photo. Supports both header and query param auth for <img> tags."""
    # Auth check - support both Authorization header and ?auth= query param
    from permissions import get_current_user_from_token
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif auth:
        token = auth

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate token
    try:
        await get_current_user_from_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get participant
    participant = await db.participants.find_one(
        {"id": participant_id},
        {"_id": 0, "photo_path": 1, "photo_content_type": 1}
    )
    if not participant or not participant.get("photo_path"):
        raise HTTPException(status_code=404, detail="No photo found")

    # Fetch from storage
    try:
        photo_data, _ = get_object(participant["photo_path"])
    except Exception as e:
        logger.error(f"Failed to retrieve photo: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve photo")

    content_type = participant.get("photo_content_type", "image/jpeg")
    return Response(
        content=photo_data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"}
    )


@api_router.delete("/participants/{participant_id}/photo")
async def delete_cadet_photo(
    participant_id: str,
    user=Depends(get_current_user)
):
    """Soft-delete a cadet's photo. Accessible to parents (own cadet) and roster editors."""
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    user_role = user.get("role", "")
    is_parent = user_role == "parent"
    can_edit_roster = user_role in [
        "commander", "dcp", "executive_staff", "exec_cadre",
        "staff", "plans_programs", "cadre", "finance",
        "squadron_commander", "training_officer"
    ]

    if is_parent:
        linked_capid = user.get("linked_capid", "")
        if participant.get("capid") != linked_capid:
            raise HTTPException(status_code=403, detail="You can only manage your cadet's photo")
    elif not can_edit_roster:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Soft-delete: clear photo fields from participant
    await db.participants.update_one(
        {"id": participant_id},
        {"$unset": {
            "photo_path": "",
            "photo_content_type": "",
            "photo_uploaded_at": "",
            "photo_uploaded_by": ""
        }}
    )

    return {"message": "Photo removed"}
