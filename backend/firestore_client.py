"""Firestore client initialization and connection management."""
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client
from config import FIREBASE_PROJECT_ID, FIREBASE_CREDENTIALS_PATH, FIREBASE_DATABASE_NAME
import os

_db = None


def get_firestore_client() -> Client:
    """
    Returns a Firestore client instance. Initializes Firebase app on first call.
    Singleton pattern ensures only one Firebase app is initialized.
    """
    global _db
    
    if _db is not None:
        return _db
    
    # Initialize Firebase Admin SDK
    if not firebase_admin._apps:
        # Check if running in GCP environment (uses application default credentials)
        if os.getenv("GAE_ENV") or os.getenv("FUNCTION_NAME") or os.getenv("K_SERVICE"):
            firebase_admin.initialize_app()
        else:
            # Local development - use service account key file
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            # Don't specify projectId - let it use the one from credentials
            firebase_admin.initialize_app(cred)
    
    # Get Firestore client with specific database name
    _db = firestore.client(database_id=FIREBASE_DATABASE_NAME)
    return _db
