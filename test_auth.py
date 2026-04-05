"""
Create a Firebase custom token using the Admin SDK.

Important:
- This is NOT the token your FastAPI backend expects directly.
- Your backend verifies Firebase ID tokens, not custom tokens.
- Use test_get_token.py for backend/Swagger testing.
"""
import firebase_admin
from firebase_admin import auth, credentials


cred = credentials.Certificate("firebase-credentials.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)


email = input("Enter Firebase email to create a custom token for: ").strip()

print("=" * 60)
print("Firebase Custom Token Generator")
print("=" * 60)

try:
    user = auth.get_user_by_email(email)
    uid = user.uid
    custom_token = auth.create_custom_token(uid).decode("utf-8")

    print(f"\nSUCCESS: Custom token generated for {email}")
    print(f"UID: {uid}")
    print("\nCustom token:")
    print(custom_token)
    print("\n" + "=" * 60)
    print("Do not use this token directly in FastAPI Swagger.")
    print("Use test_get_token.py to generate a Firebase ID token instead.")
    print("=" * 60)
except Exception as e:
    print(f"\nFAILED: {e}")
