import firebase_admin
from firebase_admin import credentials, firestore, auth
from app.Config import settings
import logging
import json

logger = logging.getLogger(__name__)

# Global Firestore client
db = None

def initialize_firebase():
    """Initialize Firebase Admin SDK with Firestore"""
    global db
    
    if not firebase_admin._apps:
        try:
            if settings.FIREBASE_CREDENTIALS_JSON:
                cred_info = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                cred = credentials.Certificate(cred_info)
            else:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            
            # Initialize Firestore client
            db = firestore.client()
            
            logger.info("✅ Firebase & Firestore initialized")
            print("✅ Firebase & Firestore initialized successfully!")
        except Exception as e:
            logger.error(f"❌ Firebase initialization failed: {e}")
            print(f"❌ Firebase initialization failed: {e}")
            raise
    else:
        logger.info("✅ Firebase already initialized")
        if db is None:
            db = firestore.client()

def get_firestore_db():
    """Get Firestore database client"""
    global db
    if db is None:
        db = firestore.client()
    return db

def verify_firebase_token(token: str):
    """Verify Firebase Auth token and return user data"""
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except auth.InvalidIdTokenError:
        logger.error("Invalid token")
        return None
    except auth.ExpiredIdTokenError:
        logger.error("Expired token")
        return None
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None

def get_firebase_user(uid: str):
    """Get user info from Firebase Auth by UID"""
    try:
        user = auth.get_user(uid)
        return {
            'uid': user.uid,
            'email': user.email,
            'display_name': user.display_name,
            'email_verified': user.email_verified
        }
    except Exception as e:
        logger.error(f"Get user failed: {e}")
        return None
