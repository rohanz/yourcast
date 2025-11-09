"""
Authentication middleware for FastAPI
Verifies Firebase ID tokens and manages user authentication
"""
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.orm import Session
from app.services.firebase_service import firebase_service
from app.database.connection import get_db

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    FastAPI dependency that verifies Firebase ID token and returns user info

    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user_id": user["uid"]}

    Returns:
        Decoded token with user info (uid, email, name, etc.)

    Raises:
        HTTPException: 401 if token is invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Extract token from Authorization header
        token = credentials.credentials

        # Verify token with Firebase Admin SDK
        decoded_token = firebase_service.verify_id_token(token)

        # Create or update user in both Firestore and Cloud SQL
        user_id = decoded_token.get("uid")
        email = decoded_token.get("email")
        name = decoded_token.get("name")

        # Ensure user exists in both Firestore and Cloud SQL
        firebase_service.create_or_update_user(user_id, email, name, db_session=db)

        logger.info(f"User authenticated: {user_id}")

        return decoded_token

    except ValueError as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    Optional authentication - returns None if no token provided

    Usage:
        @app.get("/maybe-protected")
        async def route(user: Optional[dict] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello {user['email']}"}
            return {"message": "Hello guest"}
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        decoded_token = firebase_service.verify_id_token(token)

        # Create or update user
        user_id = decoded_token.get("uid")
        email = decoded_token.get("email")
        name = decoded_token.get("name")
        firebase_service.create_or_update_user(user_id, email, name)

        return decoded_token
    except Exception as e:
        logger.warning(f"Optional auth failed: {str(e)}")
        return None
