"""Admin endpoints for Phase 3A setup and testing."""
from fastapi import APIRouter, HTTPException
from models import FirestoreCollections, User
from config import TEST_USER_ID, GOOGLE_REFRESH_TOKEN, ASSISTANT_NAME

router = APIRouter(prefix="/admin", tags=["admin"])
fs = FirestoreCollections()


@router.post("/init-test-user")
def initialize_test_user():
    """
    Initialize the test user in Firestore.
    Run this once before testing Phase 3A.
    """
    try:
        # Check if user already exists
        existing_user = fs.get_user(TEST_USER_ID)
        if existing_user:
            return {
                "status": "already_exists",
                "user_id": TEST_USER_ID,
                "message": "Test user already initialized"
            }
        
        # Create test user
        test_user = User(
            user_id=TEST_USER_ID,
            email="dev@example.com",
            full_name="Test Developer",
            job_title="Software Engineer",
            company="Test Corp",
            timezone="America/Los_Angeles",
            google_refresh_token=GOOGLE_REFRESH_TOKEN,
            assistant_name=ASSISTANT_NAME
        )
        
        fs.create_or_update_user(test_user)
        
        return {
            "status": "created",
            "user_id": TEST_USER_ID,
            "message": "Test user initialized successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize test user: {str(e)}")


@router.get("/user/{user_id}")
def get_user(user_id: str):
    """Get user details."""
    user = fs.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.model_dump()


@router.get("/tool-actions/{user_id}")
def get_user_tool_actions(user_id: str, limit: int = 10):
    """Get recent tool actions for a user."""
    try:
        docs = fs.db.collection('tool_action_log')\
            .where('user_id', '==', user_id)\
            .order_by('timestamp', direction='DESCENDING')\
            .limit(limit)\
            .get()
        
        actions = [doc.to_dict() for doc in docs]
        return {"actions": actions, "count": len(actions)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tool actions: {str(e)}")
