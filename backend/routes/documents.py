"""Document and File Upload/Download routes"""
from fastapi import Depends, HTTPException, UploadFile, File, Form, Response
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import logging
import os

from database import db, api_router
from models import UserRole, DocumentCreate, DocumentResponse
from permissions import get_current_user, require_role
from file_storage import put_object, get_object

logger = logging.getLogger(__name__)
APP_NAME = os.environ.get("APP_NAME", "cadre-hub")

# ================= DOCUMENT ROUTES =================

# Document categories
DOCUMENT_CATEGORIES = [
    "tlp",           # Training Lesson Plans
    "pocket_class",  # Pocket Classes
    "handbook",      # Handbooks
    "sop",           # Standard Operating Procedures
    "form",          # Forms
    "checklist",     # Checklists
    "reference",     # Reference Materials
    "other"          # Other
]

def can_access_document(user: dict, doc: dict) -> bool:
    """Check if user can access a document based on scope"""
    # Commanders and Exec Cadre can access everything
    if user["role"] in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE]:
        return True
    
    # Global documents are accessible to everyone
    if doc.get("scope") == "global" or (not doc.get("flight") and not doc.get("squadron")):
        return True
    
    # Squadron-scoped documents
    if doc.get("scope") == "squadron" and doc.get("squadron"):
        # Check if user's flight is in this squadron
        user_flight = user.get("flight", "").lower()
        doc_squadron = doc.get("squadron")
        flight_to_squadron = {
            "alpha": "6th_cts", "bravo": "6th_cts",
            "charlie": "21st_cts", "delta": "21st_cts",
            "echo": "22nd_cts", "foxtrot": "22nd_cts"
        }
        if flight_to_squadron.get(user_flight) == doc_squadron:
            return True
        # Staff assigned to squadron level
        if user.get("squadron") == doc_squadron:
            return True
    
    # Flight-scoped documents
    if doc.get("scope") == "flight" and doc.get("flight"):
        if user.get("flight", "").lower() == doc.get("flight").lower():
            return True
    
    return False

@api_router.get("/documents/categories")
async def get_document_categories(user: dict = Depends(get_current_user)):
    """Get available document categories"""
    return DOCUMENT_CATEGORIES

@api_router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    doc_type: Optional[str] = None,
    category: Optional[str] = None,
    flight: Optional[str] = None,
    squadron: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get documents filtered by type, category, and flight/squadron access"""
    query = {}
    if doc_type:
        query["doc_type"] = doc_type
    if category:
        query["category"] = category
    
    docs = await db.documents.find(query, {"_id": 0}).to_list(1000)
    
    # Filter by access permissions
    accessible_docs = [d for d in docs if can_access_document(user, d)]
    
    # Additional filtering by specific flight/squadron if requested
    if flight:
        accessible_docs = [d for d in accessible_docs if d.get("flight") == flight or d.get("scope") == "global"]
    if squadron:
        accessible_docs = [d for d in accessible_docs if d.get("squadron") == squadron or d.get("scope") == "global"]
    
    return [DocumentResponse(**d) for d in accessible_docs]

@api_router.get("/documents/by-flight/{flight}")
async def get_flight_documents(
    flight: str,
    user: dict = Depends(get_current_user)
):
    """Get all documents accessible to a specific flight"""
    # Get flight-specific and global documents
    flight_lower = flight.lower()
    flight_to_squadron = {
        "alpha": "6th_cts", "bravo": "6th_cts",
        "charlie": "21st_cts", "delta": "21st_cts",
        "echo": "22nd_cts", "foxtrot": "22nd_cts"
    }
    squadron = flight_to_squadron.get(flight_lower)
    
    query = {
        "$or": [
            {"scope": "global"},
            {"flight": flight_lower},
            {"squadron": squadron, "scope": "squadron"}
        ]
    }
    
    docs = await db.documents.find(query, {"_id": 0}).to_list(1000)
    
    # Group by category
    categorized = {}
    for doc in docs:
        cat = doc.get("category") or doc.get("doc_type") or "other"
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(DocumentResponse(**doc))
    
    return {
        "flight": flight,
        "squadron": squadron,
        "documents": categorized,
        "total": len(docs)
    }

@api_router.get("/documents/by-squadron/{squadron}")
async def get_squadron_documents(
    squadron: str,
    user: dict = Depends(get_current_user)
):
    """Get all documents accessible to a specific squadron"""
    query = {
        "$or": [
            {"scope": "global"},
            {"squadron": squadron},
            {"squadron": squadron, "scope": "squadron"}
        ]
    }
    
    docs = await db.documents.find(query, {"_id": 0}).to_list(1000)
    
    # Group by category
    categorized = {}
    for doc in docs:
        cat = doc.get("category") or doc.get("doc_type") or "other"
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(DocumentResponse(**doc))
    
    return {
        "squadron": squadron,
        "documents": categorized,
        "total": len(docs)
    }

@api_router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not can_access_document(user, doc):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    
    return DocumentResponse(**doc)

DOCUMENT_UPLOAD_ROLES = [
    UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
    UserRole.STAFF, UserRole.EXEC_CADRE, UserRole.TRAINING_OFFICER,
    UserRole.HEALTH_SERVICES, UserRole.PLANS_PROGRAMS, UserRole.LOGISTICS,
    UserRole.FINANCE, UserRole.DINING_FACILITY
]

@api_router.post("/documents", response_model=DocumentResponse)
async def create_document(
    data: DocumentCreate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
        UserRole.STAFF, UserRole.EXEC_CADRE, UserRole.TRAINING_OFFICER,
        UserRole.HEALTH_SERVICES, UserRole.PLANS_PROGRAMS, UserRole.LOGISTICS, UserRole.FINANCE]))
):
    """Create a new document (Commander only)"""
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": doc_id,
        **data.model_dump(),
        "uploaded_by": user["name"],
        "version": 1,
        "version_history": [],
        "created_at": now,
        "updated_at": now
    }
    await db.documents.insert_one(doc)
    doc.pop("_id", None)
    return DocumentResponse(**doc)

@api_router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    data: DocumentCreate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
        UserRole.STAFF, UserRole.EXEC_CADRE, UserRole.TRAINING_OFFICER,
        UserRole.HEALTH_SERVICES, UserRole.PLANS_PROGRAMS, UserRole.LOGISTICS, UserRole.FINANCE]))
):
    """Update a document with version tracking"""
    existing = await db.documents.find_one({"id": doc_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    current_version = existing.get("version", 1)
    
    # Store current version in history
    version_history = existing.get("version_history", [])
    version_history.append({
        "version": current_version,
        "title": existing.get("title"),
        "content": existing.get("content"),
        "file_url": existing.get("file_url"),
        "updated_by": existing.get("uploaded_by"),
        "updated_at": existing.get("updated_at")
    })
    
    update_data = {
        **data.model_dump(),
        "uploaded_by": user["name"],
        "version": current_version + 1,
        "version_history": version_history,
        "updated_at": now
    }
    
    await db.documents.update_one({"id": doc_id}, {"$set": update_data})
    
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    return DocumentResponse(**doc)

@api_router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
        UserRole.STAFF, UserRole.EXEC_CADRE, UserRole.TRAINING_OFFICER,
        UserRole.HEALTH_SERVICES, UserRole.PLANS_PROGRAMS, UserRole.LOGISTICS, UserRole.FINANCE]))
):
    result = await db.documents.delete_one({"id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}


# ================= FILE UPLOAD/DOWNLOAD ROUTES =================

@api_router.post("/documents/upload")
async def upload_document_with_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    doc_type: str = Form("handbook"),
    category: str = Form(""),
    scope: str = Form("global"),
    flight: str = Form(""),
    squadron: str = Form(""),
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
        UserRole.STAFF, UserRole.EXEC_CADRE, UserRole.TRAINING_OFFICER,
        UserRole.HEALTH_SERVICES, UserRole.PLANS_PROGRAMS, UserRole.LOGISTICS, UserRole.FINANCE]))
):
    """Upload a document with file attachment to object storage"""
    file_data = await file.read()
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    storage_path = f"{APP_NAME}/documents/{user['id']}/{uuid.uuid4()}.{ext}"

    result = put_object(storage_path, file_data, file.content_type or "application/octet-stream")

    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": doc_id,
        "title": title,
        "description": description or None,
        "doc_type": doc_type,
        "category": category or None,
        "content": None,
        "file_url": None,
        "storage_path": result["path"],
        "file_name": file.filename,
        "file_size": result.get("size", len(file_data)),
        "file_type": file.content_type or "application/octet-stream",
        "flight": flight or None,
        "squadron": squadron or None,
        "scope": scope,
        "uploaded_by": user["name"],
        "uploaded_by_role": user["role"],
        "version": 1,
        "version_history": [],
        "created_at": now,
        "updated_at": now
    }
    await db.documents.insert_one(doc)
    doc.pop("_id", None)
    return DocumentResponse(**doc)


@api_router.get("/documents/{doc_id}/download")
async def download_document_file(
    doc_id: str,
    user: dict = Depends(get_current_user)
):
    """Download a document's attached file"""
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not can_access_document(user, doc):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")

    if not doc.get("storage_path"):
        raise HTTPException(status_code=404, detail="No file attached to this document")

    try:
        file_data, content_type = get_object(doc["storage_path"])
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")

    file_name = doc.get("file_name", "download")
    return Response(
        content=file_data,
        media_type=doc.get("file_type", content_type),
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'}
    )


@api_router.get("/documents/{doc_id}/preview")
async def preview_document_file(
    doc_id: str,
    user: dict = Depends(get_current_user)
):
    """Serve a document file inline for browser preview"""
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not can_access_document(user, doc):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")

    if not doc.get("storage_path"):
        raise HTTPException(status_code=404, detail="No file attached to this document")

    try:
        file_data, content_type = get_object(doc["storage_path"])
    except Exception as e:
        logger.error(f"Failed to preview file: {e}")
        raise HTTPException(status_code=500, detail="Failed to load file")

    file_name = doc.get("file_name", "preview")
    return Response(
        content=file_data,
        media_type=doc.get("file_type", content_type),
        headers={"Content-Disposition": f'inline; filename="{file_name}"'}
    )


@api_router.post("/documents/{doc_id}/replace-file")
async def replace_document_file(
    doc_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
        UserRole.STAFF, UserRole.EXEC_CADRE, UserRole.TRAINING_OFFICER,
        UserRole.HEALTH_SERVICES, UserRole.PLANS_PROGRAMS, UserRole.LOGISTICS, UserRole.FINANCE]))
):
    """Replace the file attachment on an existing document"""
    existing = await db.documents.find_one({"id": doc_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found")

    file_data = await file.read()
    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    storage_path = f"{APP_NAME}/documents/{user['id']}/{uuid.uuid4()}.{ext}"

    result = put_object(storage_path, file_data, file.content_type or "application/octet-stream")
    now = datetime.now(timezone.utc).isoformat()

    await db.documents.update_one({"id": doc_id}, {"$set": {
        "storage_path": result["path"],
        "file_name": file.filename,
        "file_size": result.get("size", len(file_data)),
        "file_type": file.content_type or "application/octet-stream",
        "updated_at": now,
        "uploaded_by": user["name"]
    }})

    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    return DocumentResponse(**doc)



