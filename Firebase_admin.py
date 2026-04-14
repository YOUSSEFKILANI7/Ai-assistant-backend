import firebase_admin
from firebase_admin import credentials, firestore, auth
from app.Config import settings
import logging
import json
import smtplib
from email.message import EmailMessage

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


def get_firebase_user_by_email(email: str):
    """Get Firebase user info by email"""
    try:
        user = auth.get_user_by_email(email)
        return {
            "uid": user.uid,
            "email": user.email,
            "display_name": user.display_name,
            "email_verified": user.email_verified,
        }
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        logger.error(f"Get user by email failed: {e}")
        return None


def create_or_update_guardian_auth_user(email: str, password: str):
    """Create guardian Firebase Auth user, or refresh password if they already exist."""
    existing_user = get_firebase_user_by_email(email)

    try:
        if existing_user:
            user = auth.update_user(existing_user["uid"], password=password)
        else:
            user = auth.create_user(email=email, password=password, email_verified=False)

        return {
            "uid": user.uid,
            "email": user.email,
            "display_name": user.display_name,
            "email_verified": user.email_verified,
        }
    except Exception as e:
        logger.error(f"Create/update guardian auth user failed: {e}")
        raise


def create_or_update_blind_user_auth_user(email: str, password: str):
    """Create blind user Firebase Auth user, or refresh password if they already exist."""
    existing_user = get_firebase_user_by_email(email)

    try:
        if existing_user:
            user = auth.update_user(existing_user["uid"], password=password)
        else:
            user = auth.create_user(email=email, password=password, email_verified=False)

        return {
            "uid": user.uid,
            "email": user.email,
            "display_name": user.display_name,
            "email_verified": user.email_verified,
        }
    except Exception as e:
        logger.error(f"Create/update blind user auth user failed: {e}")
        raise


def send_guardian_credentials_email(
    recipient_email: str,
    blind_user_name: str,
    login_email: str,
    temporary_password: str,
):
    """Send guardian credentials email if SMTP is configured."""
    if not all(
        [
            settings.SMTP_HOST,
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
            settings.SMTP_FROM_EMAIL,
        ]
    ):
        logger.warning("SMTP is not configured; skipping guardian credentials email")
        return False

    message = EmailMessage()
    message["Subject"] = f"Guardian access for {blind_user_name}"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient_email
    message.set_content(
        "\n".join(
            [
                f"You have been added as a guardian for {blind_user_name}.",
                "",
                "Use these credentials to sign in:",
                f"Email: {login_email}",
                f"Password: {temporary_password}",
            ]
        )
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
        return True
    except Exception as e:
        logger.error(f"Send guardian credentials email failed: {e}")
        return False
