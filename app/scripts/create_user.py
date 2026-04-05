from fastapi import APIRouter, HTTPException, status
from app.Firebase_admin import get_firestore_db
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid

router = APIRouter(prefix="/device", tags=["Raspberry Pi / Smart Glasses"])


class LocationUpdate(BaseModel):
    user_id: str
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = 10.0
    battery_level: Optional[int] = None

class AlertCreate(BaseModel):
    user_id: str
    type: str
    severity: str
    object_type: Optional[str] = None
    distance_meters: Optional[float] = None
    location: dict


@router.post("/location")
async def update_location(location: LocationUpdate):
    """
    Raspberry Pi sends location updates.
    NO AUTHENTICATION REQUIRED - device is pre-configured with user_id.
    """
    try:
        user_id = location.user_id.strip().upper()
        
        # Get Firestore database
        db = get_firestore_db()
        
        # Verify user exists
        user_ref = db.collection('blind_users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        user_data = user_doc.to_dict()
        
        if not user_data.get('active', True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Prepare location data
        location_data = {
            "user_id": user_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "accuracy_meters": location.accuracy_meters,
            "timestamp": timestamp
        }
        
        if location.battery_level is not None:
            location_data["battery_level"] = location.battery_level
        
        # Save current location (overwrite)
        current_location_ref = db.collection('locations').document(f'{user_id}_current')
        current_location_ref.set(location_data)
        
        # Save to location history (new document each time)
        history_ref = db.collection('location_history').document()
        history_ref.set(location_data)
        
        # Update device battery if provided
        if location.battery_level is not None and user_data.get('device_id'):
            device_ref = db.collection('devices').document(user_data['device_id'])
            device_ref.update({
                'battery_level': location.battery_level,
                'last_sync': timestamp
            })
        
        return {
            "status": "success",
            "timestamp": timestamp
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Location update failed: {str(e)}"
        )


@router.post("/alert")
async def create_alert(alert: AlertCreate):
    """
    Raspberry Pi sends obstacle detection alerts.
    NO AUTHENTICATION REQUIRED.
    """
    try:
        user_id = alert.user_id.strip().upper()
        
        # Get Firestore database
        db = get_firestore_db()
        
        # Verify user exists
        user_ref = db.collection('blind_users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        alert_id = str(uuid.uuid4())
        
        # Prepare alert data
        alert_data = {
            "alert_id": alert_id,
            "user_id": user_id,
            "type": alert.type,
            "severity": alert.severity,
            "location": alert.location,
            "timestamp": timestamp,
            "acknowledged": False
        }
        
        if alert.object_type:
            alert_data["object_type"] = alert.object_type
        if alert.distance_meters is not None:
            alert_data["distance_meters"] = alert.distance_meters
        
        # Save alert to Firestore
        alert_ref = db.collection('alerts').document(alert_id)
        alert_ref.set(alert_data)
        
        # TODO: Notify linked guardians via push notification
        # Get user's linked guardians and send notifications
        user_data = user_doc.to_dict()
        linked_guardians = user_data.get('linked_guardians', [])
        
        # Create notifications for each guardian
        for guardian_id in linked_guardians:
            notification_id = str(uuid.uuid4())
            notification_data = {
                "notification_id": notification_id,
                "guardian_id": guardian_id,
                "user_id": user_id,
                "type": alert.type,
                "title": f"Alert: {alert.type}",
                "message": f"{alert.object_type or 'Obstacle'} detected at {alert.distance_meters or 'unknown'}m",
                "timestamp": timestamp,
                "read": False,
                "alert_id": alert_id,
                "priority": "high" if alert.severity in ["high", "critical"] else "medium"
            }
            
            # Save notification
            notification_ref = db.collection('notifications').document(notification_id)
            notification_ref.set(notification_data)
        
        return {
            "status": "success",
            "alert_id": alert_id,
            "timestamp": timestamp,
            "notified_guardians": len(linked_guardians)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alert creation failed: {str(e)}"
        )


@router.get("/health")
async def device_health():
    """Simple health check for Raspberry Pi to verify connection"""
    return {
        "status": "healthy",
        "message": "Device API is working"
    }