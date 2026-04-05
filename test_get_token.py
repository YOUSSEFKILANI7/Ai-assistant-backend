"""
Get a real Firebase ID token using email/password sign-in.

Use this token with FastAPI protected endpoints:
Authorization: Bearer <id_token>
"""
import requests

FIREBASE_API_KEY = "AIzaSyCWWppvCqqA7CtpDNfPtDCOEbuq8Lsw5Uk"


def get_firebase_id_token(email: str, password: str):
    """Sign in with email/password and return a Firebase ID token."""
    url = (
        "https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    )

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    response = requests.post(url, json=payload, timeout=30)

    if response.status_code == 200:
        return response.json()["idToken"]

    print(f"Error: {response.json()}")
    return None


email = input("Enter Firebase email: ").strip()
password = input(f"Enter password for {email}: ")

print("=" * 60)
print("Firebase ID Token Generator")
print("=" * 60)

token = get_firebase_id_token(email, password)

if token:
    print("\nSUCCESS: Firebase ID token generated.")
    print("\nToken (use this in Swagger/Postman):")
    print(token)
    print("\n" + "=" * 60)
    print("Use exactly this header format:")
    print("Authorization: Bearer <paste token here>")
    print("=" * 60)
else:
    print("\nFAILED: Could not generate Firebase ID token.")
