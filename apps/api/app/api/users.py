from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class UserPreferences(BaseModel):
    subcategories: List[str]
    custom_tags: Optional[List[str]] = []

class UserPreferencesResponse(BaseModel):
    preferences: Optional[dict]

@router.get("/preferences", response_model=UserPreferencesResponse)
def get_user_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the authenticated user's saved preferences
    """
    user = db.query(User).filter(User.id == current_user["uid"]).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"preferences": user.preferences}

@router.put("/preferences")
def update_user_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the authenticated user's preferences
    """
    user = db.query(User).filter(User.id == current_user["uid"]).first()

    if not user:
        # Create user if doesn't exist
        user = User(
            id=current_user["uid"],
            email=current_user["email"],
            preferences={
                "subcategories": preferences.subcategories,
                "custom_tags": preferences.custom_tags or []
            }
        )
        db.add(user)
    else:
        # Update existing user preferences
        user.preferences = {
            "subcategories": preferences.subcategories,
            "custom_tags": preferences.custom_tags or []
        }

    db.commit()
    db.refresh(user)

    return {
        "message": "Preferences updated successfully",
        "preferences": user.preferences
    }
