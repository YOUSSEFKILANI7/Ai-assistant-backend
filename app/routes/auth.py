from fastapi import APIRouter, HTTPException, status, Depends
from app.models.auth import GuardianRegisterRequest, GuardianProfileResponse
from app.Firebase_admin import get_firestore_db, get_firebase_user
from app.dependencies import get_current_user
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
        
        # Check if profile exists
        guardian_ref = db.collection('guardians').document(guardian_id)
        guardian_doc = guardian_ref.get()
        
        if guardian_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile already exists"
            )
        
        # Get email verification status from Firebase Auth
        firebase_user = get_firebase_user(guardian_id)
        email_verified = firebase_user.get('email_verified', False) if firebase_user else False
        
        # Create guardian profile
        guardian_data = {
            "guardian_id": guardian_id,
            "email": email,
            "name": profile.name,
            "phone": profile.phone,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "monitored_users": [],
            "notification_preferences": {
                "emergency_alerts": True,
                "obstacle_alerts": True,
                "low_battery_alerts": True,
                "location_updates": False,
                "daily_summary": True
            }
        }
        
        # Save to Firestore
        guardian_ref.set(guardian_data)
        
        return GuardianProfileResponse(
            guardian_id=guardian_id,
            email=email,
            name=profile.name,
            phone=profile.phone,
            created_at=guardian_data["created_at"],
            monitored_users=[]
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