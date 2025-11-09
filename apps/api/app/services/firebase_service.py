"""
Firebase Admin SDK initialization and Firestore service
Manages Firebase authentication and Firestore database operations
"""
import logging
import firebase_admin
from firebase_admin import credentials, firestore, auth
from typing import Optional
import os

logger = logging.getLogger(__name__)

class FirebaseService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialize_firebase()
            FirebaseService._initialized = True

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # When running on Cloud Run, use Application Default Credentials
                # Firebase will automatically use the service account
                logger.info("Initializing Firebase Admin SDK...")
                firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK initialized successfully")
            else:
                logger.info("Firebase Admin SDK already initialized")

            # Get Firestore client
            self.db = firestore.client()
            logger.info("Firestore client initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise

    def verify_id_token(self, id_token: str) -> dict:
        """
        Verify Firebase ID token and return decoded token

        Args:
            id_token: Firebase ID token from client

        Returns:
            Decoded token containing user info (uid, email, etc.)

        Raises:
            ValueError: If token is invalid
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise ValueError(f"Invalid authentication token: {str(e)}")

    def get_user_ref(self, user_id: str):
        """Get Firestore reference to user document"""
        return self.db.collection('users').document(user_id)

    def get_user(self, user_id: str) -> Optional[dict]:
        """
        Get user data from Firestore

        Args:
            user_id: Firebase user ID (uid)

        Returns:
            User data dict or None if not found
        """
        try:
            user_ref = self.get_user_ref(user_id)
            user_doc = user_ref.get()

            if user_doc.exists:
                return user_doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            return None

    def create_or_update_user(self, user_id: str, email: str, name: Optional[str] = None, db_session=None) -> dict:
        """
        Create or update user in both Firestore and Cloud SQL

        Args:
            user_id: Firebase user ID (uid)
            email: User email
            name: User display name
            db_session: Optional SQLAlchemy database session for Cloud SQL

        Returns:
            Updated user data
        """
        try:
            user_ref = self.get_user_ref(user_id)
            user_doc = user_ref.get()

            from datetime import datetime
            now = datetime.utcnow()

            if user_doc.exists:
                # Update existing user in Firestore
                user_data = user_doc.to_dict()
                user_ref.update({
                    'email': email,
                    'name': name or user_data.get('name'),
                    'last_login': now,
                    'updated_at': now
                })
                logger.info(f"Updated user {user_id} in Firestore")
            else:
                # Create new user in Firestore
                user_data = {
                    'uid': user_id,
                    'email': email,
                    'name': name or email.split('@')[0],
                    'created_at': now,
                    'last_login': now,
                    'updated_at': now,
                    'last_podcast_generated_at': None,
                    'podcast_count_today': 0
                }
                user_ref.set(user_data)
                logger.info(f"Created new user {user_id} in Firestore")

            # Also create/update user in Cloud SQL if db_session provided
            if db_session is not None:
                from app.models.user import User
                sql_user = db_session.query(User).filter(User.id == user_id).first()
                if not sql_user:
                    # Create new user with display_name
                    sql_user = User(id=user_id, email=email, display_name=name)
                    db_session.add(sql_user)
                    db_session.commit()
                    logger.info(f"Created user {user_id} in Cloud SQL with display_name: {name}")
                else:
                    # Update display_name if provided and different
                    if name and sql_user.display_name != name:
                        sql_user.display_name = name
                        db_session.commit()
                        logger.info(f"Updated user {user_id} display_name in Cloud SQL: {name}")
                    else:
                        logger.info(f"User {user_id} already exists in Cloud SQL")

            # Return updated user data
            return self.get_user(user_id)

        except Exception as e:
            logger.error(f"Error creating/updating user {user_id}: {str(e)}")
            if db_session is not None:
                db_session.rollback()
            raise

    def can_generate_podcast_today(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if user can generate a podcast today

        Args:
            user_id: Firebase user ID

        Returns:
            Tuple of (can_generate: bool, error_message: Optional[str])
        """
        try:
            user_data = self.get_user(user_id)
            if not user_data:
                return False, "User not found"

            from datetime import datetime, date
            today = date.today()

            last_generated = user_data.get('last_podcast_generated_at')

            # If never generated, or generated on a different day, allow
            if not last_generated:
                return True, None

            # Convert Firestore timestamp to date
            last_generated_date = last_generated.date() if hasattr(last_generated, 'date') else last_generated

            if last_generated_date < today:
                return True, None

            # Already generated today
            return False, "You can only generate one podcast per day. Please try again tomorrow!"

        except Exception as e:
            logger.error(f"Error checking podcast limit for user {user_id}: {str(e)}")
            return False, f"Error checking podcast limit: {str(e)}"

    def record_podcast_generation(self, user_id: str):
        """
        Record that user generated a podcast today

        Args:
            user_id: Firebase user ID
        """
        try:
            from datetime import datetime
            user_ref = self.get_user_ref(user_id)
            user_ref.update({
                'last_podcast_generated_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            logger.info(f"Recorded podcast generation for user {user_id}")
        except Exception as e:
            logger.error(f"Error recording podcast generation for user {user_id}: {str(e)}")
            raise


# Singleton instance
firebase_service = FirebaseService()
