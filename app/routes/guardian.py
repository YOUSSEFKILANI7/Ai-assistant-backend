from fastapi import APIRouter, HTTPException, status, Depends
from app.models.auth import LinkUserRequest
from app.models.user import BlindUserResponse
from app.Firebase_admin import get_firestore_db
from app.dependencies import get_current_user
from typing import List

router = APIRouter(prefix="/guardian", tags=["Guardian"])


def get_guardian_document_or_404(db, guardian_id: str):
    guardian_ref = db.collection("guardians").document(guardian_id)
    guardian_doc = guardian_ref.get()

    if not guardian_doc.exists:
        raise HTTPException(status_code=404, detail="Guardian profile not found")

    return guardian_ref, guardian_doc.to_dict()


@router.post("/link-user")
async def link_to_blind_user(
    request: LinkUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Link guardian to a blind user using the unique ID.
    The unique ID is given to the blind user when their account is created.
    """
    try:
        guardian_id = current_user["uid"]
        user_unique_id = request.user_unique_id.strip().upper()
        
        # Get Firestore database
        db = get_firestore_db()
        
        # Check if blind user exists
        user_ref = db.collection('blind_users').document(user_unique_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No user found with ID: {user_unique_id}"
            )
        
        user_data = user_doc.to_dict()
        
        if not user_data.get('active', True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This user account is inactive"
            )
        
        # Check if guardian exists
        guardian_ref, guardian_data = get_guardian_document_or_404(db, guardian_id)
        
        # Add user to guardian's monitored list
        monitored = guardian_data.get('monitored_users', [])
        if user_unique_id not in monitored:
            monitored.append(user_unique_id)
            guardian_ref.update({'monitored_users': monitored})
        
        # Add guardian to user's linked guardians
        linked_guardians = user_data.get('linked_guardians', [])
        if guardian_id not in linked_guardians:
            linked_guardians.append(guardian_id)
            user_ref.update({'linked_guardians': linked_guardians})
        
        return {
            "status": "success",
            "message": f"Successfully linked to user {user_data['name']}",
            "user_id": user_unique_id,
            "user_name": user_data['name']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Linking failed: {str(e)}"
        )


@router.get("/monitored-users", response_model=List[BlindUserResponse])
async def get_monitored_users(current_user: dict = Depends(get_current_user)):
    """
    Get list of all blind users that this guardian is monitoring.
    """
    try:
        guardian_id = current_user["uid"]
        
        # Get Firestore database
        db = get_firestore_db()
        
        # Get guardian data
        _, guardian_data = get_guardian_document_or_404(db, guardian_id)
        monitored_ids = guardian_data.get('monitored_users', [])
        
        # Get details for each monitored user
        monitored_users = []
        for user_id in monitored_ids:
            user_ref = db.collection('blind_users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                monitored_users.append(BlindUserResponse(
                    unique_id=user_id,
                    name=user_data['name'],
                    device_id=user_data.get('device_id'),
                    active=user_data.get('active', True),
                    created_at=user_data['created_at'],
                    guardian_count=len(user_data.get('linked_guardians', []))
                ))
        
        return monitored_users
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitored users: {str(e)}"
        )


@router.delete("/unlink-user/{user_unique_id}")
async def unlink_from_user(
    user_unique_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Unlink guardian from a blind user.
    """
    try:
        guardian_id = current_user["uid"]
        user_unique_id = user_unique_id.strip().upper()
        
        # Get Firestore database
        db = get_firestore_db()
        
        # Remove from guardian's monitored list
        guardian_ref = db.collection('guardians').document(guardian_id)
        guardian_doc = guardian_ref.get()
        
        if guardian_doc.exists:
            guardian_data = guardian_doc.to_dict()
            monitored = guardian_data.get('monitored_users', [])
            if user_unique_id in monitored:
                monitored.remove(user_unique_id)
                guardian_ref.update({'monitored_users': monitored})
        
        # Remove from user's linked guardians
        user_ref = db.collection('blind_users').document(user_unique_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            linked = user_data.get('linked_guardians', [])
            if guardian_id in linked:
                linked.remove(guardian_id)
                user_ref.update({'linked_guardians': linked})
        
        return {
            "status": "success",
            "message": "Successfully unlinked from user"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unlinking failed: {str(e)}"
        )
    


@router.get("/user-location/{user_id}")
async def get_user_location(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get latest location of a blind user.
    """
    try:
        guardian_id = current_user["uid"]
        user_id = user_id.strip().upper()

        db = get_firestore_db()

        # Verify guardian exists
        _, guardian_data = get_guardian_document_or_404(db, guardian_id)

        # Verify guardian is linked to user
        if user_id not in guardian_data.get("monitored_users", []):
            raise HTTPException(
                status_code=403,
                detail="You are not linked to this user"
            )

        # Get current location
        location_ref = db.collection("locations").document(f"{user_id}_current")
        location_doc = location_ref.get()

        if not location_doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Location not available"
            )

        return location_doc.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@router.get("/alerts/{user_id}")
async def get_user_alerts(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get obstacle alerts for a blind user.
    """
    try:
        guardian_id = current_user["uid"]
        user_id = user_id.strip().upper()

        db = get_firestore_db()

        # Verify guardian link
        _, guardian_data = get_guardian_document_or_404(db, guardian_id)

        if user_id not in guardian_data.get("monitored_users", []):
            raise HTTPException(
                status_code=403,
                detail="You are not linked to this user"
            )

        alerts_query = (
            db.collection("alerts")
            .where("user_id", "==", user_id)
            .order_by("timestamp", direction="DESCENDING")
            .limit(20)
        )

        alerts = []

        for doc in alerts_query.stream():
            alerts.append(doc.to_dict())

        return alerts

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/notifications")
async def get_notifications(
    current_user: dict = Depends(get_current_user)
):
    """
    Get notifications for the guardian.
    """
    try:
        guardian_id = current_user["uid"]

        db = get_firestore_db()

        notifications_query = (
            db.collection("notifications")
            .where("guardian_id", "==", guardian_id)
            .order_by("timestamp", direction="DESCENDING")
            .limit(30)
        )

        notifications = []

        for doc in notifications_query.stream():
            notifications.append(doc.to_dict())

        return notifications

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.patch("/notifications/{notification_id}")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark notification as read.
    """
    try:
        guardian_id = current_user["uid"]

        db = get_firestore_db()

        notif_ref = db.collection("notifications").document(notification_id)
        notif_doc = notif_ref.get()

        if not notif_doc.exists:
            raise HTTPException(status_code=404, detail="Notification not found")

        notif_data = notif_doc.to_dict()

        if notif_data["guardian_id"] != guardian_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        notif_ref.update({"read": True})

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@router.get("/location-history/{user_id}")
async def get_location_history(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent location history for a blind user.
    """
    try:
        guardian_id = current_user["uid"]
        user_id = user_id.strip().upper()

        db = get_firestore_db()

        # Verify guardian
        _, guardian_data = get_guardian_document_or_404(db, guardian_id)

        if user_id not in guardian_data.get("monitored_users", []):
            raise HTTPException(status_code=403, detail="Not linked to this user")

        history_query = (
            db.collection("location_history")
            .where("user_id", "==", user_id)
            .order_by("timestamp", direction="DESCENDING")
            .limit(20)
        )

        history = []

        for doc in history_query.stream():
            history.append(doc.to_dict())

        return history

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/device-status/{user_id}")
async def get_device_status(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get device status for a blind user.
    """
    try:
        guardian_id = current_user["uid"]
        user_id = user_id.strip().upper()

        db = get_firestore_db()

        # Verify guardian
        _, guardian_data = get_guardian_document_or_404(db, guardian_id)

        if user_id not in guardian_data.get("monitored_users", []):
            raise HTTPException(status_code=403, detail="Not linked to this user")

        # Get user
        user_ref = db.collection("blind_users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_doc.to_dict()

        device_id = user_data.get("device_id")

        if not device_id:
            return {"status": "no device"}

        device_ref = db.collection("devices").document(device_id)
        device_doc = device_ref.get()

        if not device_doc.exists:
            return {"status": "device not registered"}

        return device_doc.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/user-summary/{user_id}")
async def get_user_summary(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Return a summary for the guardian dashboard.
    """
    try:
        guardian_id = current_user["uid"]
        user_id = user_id.strip().upper()

        db = get_firestore_db()

        # Verify guardian
        _, guardian_data = get_guardian_document_or_404(db, guardian_id)

        if user_id not in guardian_data.get("monitored_users", []):
            raise HTTPException(status_code=403, detail="Not linked to this user")

        # Get current location
        location_doc = (
            db.collection("locations")
            .document(f"{user_id}_current")
            .get()
        )

        location = location_doc.to_dict() if location_doc.exists else None

        # Get latest alerts
        alerts_query = (
            db.collection("alerts")
            .where("user_id", "==", user_id)
            .order_by("timestamp", direction="DESCENDING")
            .limit(5)
        )

        alerts = [doc.to_dict() for doc in alerts_query.stream()]

        return {
            "user_id": user_id,
            "current_location": location,
            "recent_alerts": alerts
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
