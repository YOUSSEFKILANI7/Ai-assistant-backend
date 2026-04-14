from datetime import datetime
from secrets import choice
from string import ascii_letters, digits

from fastapi import APIRouter, Depends, HTTPException, status

from app.Config import settings
from app.Firebase_admin import (
    create_or_update_blind_user_auth_user,
    create_or_update_guardian_auth_user,
    get_firestore_db,
    get_firebase_user,
    send_guardian_credentials_email,
)
from app.models.auth import (
    BlindUserAdminCreateRequest,
    BlindUserProfileResponse,
    BlindUserRegisterRequest,
    GuardianInviteRequest,
    GuardianInviteResponse,
    GuardianProfileResponse,
    GuardianRegisterRequest,
)
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


def generate_temporary_password(length: int = 12) -> str:
    alphabet = ascii_letters + digits
    return "".join(choice(alphabet) for _ in range(length))


def get_blind_user_document_by_auth_uid(db, auth_uid: str):
    query = (
        db.collection("blind_users")
        .where("auth_uid", "==", auth_uid)
        .limit(1)
    )
    docs = list(query.stream())
    if not docs:
        return None, None
    return docs[0].reference, docs[0].to_dict()


@router.post("/guardian/create-profile", response_model=GuardianProfileResponse)
async def create_guardian_profile(
    profile: GuardianRegisterRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create guardian profile after Firebase Auth registration.
    Only guardians register - blind users are created manually by admin.
    """
    try:
        guardian_id = current_user["uid"]
        email = current_user["email"]
        
        # Get Firestore database
        db = get_firestore_db()
        
        guardian_ref = db.collection('guardians').document(guardian_id)
        guardian_doc = guardian_ref.get()

        guardian_data = {
            "guardian_id": guardian_id,
            "email": email,
            "name": profile.name,
            "phone": profile.phone,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "monitored_users": guardian_doc.to_dict().get("monitored_users", []) if guardian_doc.exists else [],
            "notification_preferences": {
                "emergency_alerts": True,
                "obstacle_alerts": True,
                "low_battery_alerts": True,
                "location_updates": False,
                "daily_summary": True
            },
        }

        if guardian_doc.exists:
            existing_data = guardian_doc.to_dict()
            guardian_data["created_at"] = existing_data.get("created_at", guardian_data["created_at"])
            guardian_data["notification_preferences"] = existing_data.get(
                "notification_preferences", guardian_data["notification_preferences"]
            )

        guardian_ref.set(guardian_data, merge=True)

        return GuardianProfileResponse(
            guardian_id=guardian_id,
            email=email,
            name=profile.name,
            phone=profile.phone,
            created_at=guardian_data["created_at"],
            monitored_users=guardian_data["monitored_users"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile creation failed: {str(e)}"
        )


@router.get("/guardian/me", response_model=GuardianProfileResponse)
async def get_guardian_profile(current_user: dict = Depends(get_current_user)):
    """Get current guardian's profile"""
    try:
        guardian_id = current_user["uid"]
        
        # Get Firestore database
        db = get_firestore_db()
        
        # Get guardian document
        guardian_ref = db.collection('guardians').document(guardian_id)
        guardian_doc = guardian_ref.get()
        
        if not guardian_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        
        guardian_data = guardian_doc.to_dict()
        
        return GuardianProfileResponse(
            guardian_id=guardian_id,
            email=guardian_data["email"],
            name=guardian_data["name"],
            phone=guardian_data.get("phone"),
            created_at=guardian_data["created_at"],
            monitored_users=guardian_data.get("monitored_users", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile: {str(e)}"
        )


@router.get("/verify-token")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify if Firebase token is valid"""
    return {
        "valid": True,
        "uid": current_user["uid"],
        "email": current_user.get("email"),
        "email_verified": current_user.get("email_verified", False)
    }


@router.post("/blind-user/admin-create", response_model=BlindUserProfileResponse)
async def admin_create_blind_user(profile: BlindUserAdminCreateRequest):
    """
    Admin flow to create a blind user's Firebase Auth account and Firestore profile seed.
    """
    try:
        db = get_firestore_db()
        unique_id = profile.unique_id.strip().upper()
        blind_ref = db.collection("blind_users").document(unique_id)
        blind_doc = blind_ref.get()

        if blind_doc.exists:
            existing = blind_doc.to_dict()
            if existing.get("auth_uid"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Blind user already exists with an auth account",
                )

        blind_auth_user = create_or_update_blind_user_auth_user(
            profile.blind_user_email.strip().lower(),
            profile.blind_user_password,
        )

        blind_data = {
            "unique_id": unique_id,
            "auth_uid": blind_auth_user["uid"],
            "email": blind_auth_user["email"],
            "name": profile.name,
            "device_id": profile.device_id,
            "active": True,
            "created_at": blind_doc.to_dict().get("created_at", datetime.utcnow().isoformat() + "Z")
            if blind_doc.exists
            else datetime.utcnow().isoformat() + "Z",
            "linked_guardians": blind_doc.to_dict().get("linked_guardians", []) if blind_doc.exists else [],
        }

        blind_ref.set(blind_data, merge=True)

        return BlindUserProfileResponse(**blind_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Blind user admin creation failed: {str(e)}",
        )


@router.post("/blind-user/create-profile", response_model=BlindUserProfileResponse)
async def create_blind_user_profile(
    profile: BlindUserRegisterRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create or update a blind user profile for the currently authenticated blind user."""
    try:
        blind_auth_uid = current_user["uid"]
        email = current_user["email"]
        unique_id = profile.unique_id.strip().upper()

        db = get_firestore_db()
        blind_ref = db.collection("blind_users").document(unique_id)
        blind_doc = blind_ref.get()

        if blind_doc.exists:
            existing = blind_doc.to_dict()
            existing_auth_uid = existing.get("auth_uid")
            if existing_auth_uid and existing_auth_uid != blind_auth_uid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This blind user ID is already assigned to another account",
                )

        blind_data = {
            "unique_id": unique_id,
            "auth_uid": blind_auth_uid,
            "email": email,
            "name": profile.name,
            "device_id": profile.device_id,
            "active": True,
            "created_at": blind_doc.to_dict().get("created_at", datetime.utcnow().isoformat() + "Z")
            if blind_doc.exists
            else datetime.utcnow().isoformat() + "Z",
            "linked_guardians": blind_doc.to_dict().get("linked_guardians", []) if blind_doc.exists else [],
        }

        blind_ref.set(blind_data, merge=True)

        return BlindUserProfileResponse(**blind_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Blind user profile creation failed: {str(e)}",
        )


@router.get("/blind-user/me", response_model=BlindUserProfileResponse)
async def get_blind_user_profile(current_user: dict = Depends(get_current_user)):
    """Get the blind user profile for the currently authenticated blind user."""
    try:
        blind_auth_uid = current_user["uid"]
        db = get_firestore_db()
        _, blind_data = get_blind_user_document_by_auth_uid(db, blind_auth_uid)

        if not blind_data:
            raise HTTPException(status_code=404, detail="Blind user profile not found")

        return BlindUserProfileResponse(**blind_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blind user profile: {str(e)}",
        )


@router.post("/blind-user/add-guardian", response_model=GuardianInviteResponse)
async def invite_guardian_for_blind_user(
    request: GuardianInviteRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Blind user invites a guardian by email.
    The guardian account is created in Firebase Auth and paired automatically.
    """
    try:
        blind_auth_uid = current_user["uid"]
        guardian_email = request.guardian_email.strip().lower()

        db = get_firestore_db()
        blind_ref, blind_data = get_blind_user_document_by_auth_uid(db, blind_auth_uid)

        if not blind_data:
            raise HTTPException(status_code=404, detail="Blind user profile not found")

        temporary_password = generate_temporary_password()
        guardian_user = create_or_update_guardian_auth_user(guardian_email, temporary_password)
        guardian_id = guardian_user["uid"]

        guardian_ref = db.collection("guardians").document(guardian_id)
        guardian_doc = guardian_ref.get()
        monitored_users = guardian_doc.to_dict().get("monitored_users", []) if guardian_doc.exists else []
        if blind_data["unique_id"] not in monitored_users:
            monitored_users.append(blind_data["unique_id"])

        guardian_ref.set(
            {
                "guardian_id": guardian_id,
                "email": guardian_email,
                "name": guardian_doc.to_dict().get("name", guardian_email.split("@")[0]) if guardian_doc.exists else guardian_email.split("@")[0],
                "phone": guardian_doc.to_dict().get("phone") if guardian_doc.exists else None,
                "created_at": guardian_doc.to_dict().get("created_at", datetime.utcnow().isoformat() + "Z")
                if guardian_doc.exists
                else datetime.utcnow().isoformat() + "Z",
                "monitored_users": monitored_users,
                "notification_preferences": guardian_doc.to_dict().get(
                    "notification_preferences",
                    {
                        "emergency_alerts": True,
                        "obstacle_alerts": True,
                        "low_battery_alerts": True,
                        "location_updates": False,
                        "daily_summary": True,
                    },
                )
                if guardian_doc.exists
                else {
                    "emergency_alerts": True,
                    "obstacle_alerts": True,
                    "low_battery_alerts": True,
                    "location_updates": False,
                    "daily_summary": True,
                },
                "invited_by_user_id": blind_data["unique_id"],
                "invitation_status": "credentials_sent",
            },
            merge=True,
        )

        linked_guardians = blind_data.get("linked_guardians", [])
        if guardian_id not in linked_guardians:
            linked_guardians.append(guardian_id)
            blind_ref.update({"linked_guardians": linked_guardians})

        email_sent = send_guardian_credentials_email(
            recipient_email=guardian_email,
            blind_user_name=blind_data["name"],
            login_email=guardian_email,
            temporary_password=temporary_password,
        )

        return GuardianInviteResponse(
            status="success",
            guardian_email=guardian_email,
            guardian_id=guardian_id,
            blind_user_id=blind_data["unique_id"],
            email_sent=email_sent,
            message="Guardian account created and paired successfully",
            temporary_password=temporary_password if settings.TEST_MODE else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Guardian invitation failed: {str(e)}",
        )
