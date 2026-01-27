import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os

# ==========================================
# FIREBASE CONFIGURATION
# ==========================================
CREDENTIALS_FILE = "firebase-credentials.json"
db = None

def init_firebase():
    """Initialize Firebase Admin SDK and connect to Firestore"""
    global db
    try:
        # Check if already initialized to prevent multiple app errors
        if not firebase_admin._apps:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Missing {CREDENTIALS_FILE}. See setup instructions.")
            
            cred = credentials.Certificate(CREDENTIALS_FILE)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully!")
        
        db = firestore.client()
        return True
    except Exception as e:
        print(f"❌ Firebase Error: {e}")
        return False

# ==========================================
# USER OPERATIONS (Firestore)
# ==========================================
class UserService:
    COLLECTION = 'users'
    
    @staticmethod
    def create_user(username, email, password_hash, role='officer', phone='', shift='08:00-20:00', department='Security Operations', google_uid='', profile_complete=True):
        """Create a new user document"""
        if not db: return None
            
        user_data = {
            'username': username,
            'email': email.lower(),
            'password_hash': password_hash,
            'role': role,
            'phone': phone,
            'shift': shift,
            'department': department,
            'is_active': True,
            'google_uid': google_uid,
            'profile_complete': profile_complete,
            'created_at': datetime.utcnow()
        }
        
        doc_ref = db.collection(UserService.COLLECTION).document()
        doc_ref.set(user_data)
        user_data['id'] = doc_ref.id
        return user_data
    
    @staticmethod
    def get_user_by_id(user_id):
        if not db: return None
        doc = db.collection(UserService.COLLECTION).document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    @staticmethod
    def get_user_by_username(username):
        if not db: return None
        docs = db.collection(UserService.COLLECTION).where('username', '==', username).limit(1).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    @staticmethod
    def get_user_by_email(email):
        if not db: return None
        docs = db.collection(UserService.COLLECTION).where('email', '==', email.lower()).limit(1).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    @staticmethod
    def get_all_users():
        if not db: return []
        docs = db.collection(UserService.COLLECTION).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        users = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            users.append(data)
        return users
    
    @staticmethod
    def update_user(user_id, updates):
        if not db: return False
        db.collection(UserService.COLLECTION).document(user_id).update(updates)
        return True
    
    @staticmethod
    def delete_user(user_id):
        if not db: return False
        db.collection(UserService.COLLECTION).document(user_id).delete()
        return True
    
    @staticmethod
    def count_users(role=None, is_active=None):
        if not db: return 0
        query = db.collection(UserService.COLLECTION)
        if role:
            query = query.where('role', '==', role)
        if is_active is not None:
            query = query.where('is_active', '==', is_active)
        return len(list(query.stream()))

# ==========================================
# VIDEO EVIDENCE OPERATIONS (Firestore)
# ==========================================
class VideoService:
    COLLECTION = 'video_evidence'
    
    @staticmethod
    def create_video(filename, cloudinary_url, status, max_score, anomaly_count, processing_time, uploaded_by=None):
        if not db: return None
            
        video_data = {
            'filename': filename,
            'cloudinary_url': cloudinary_url,
            'status': status,
            'max_score': max_score,
            'anomaly_count': anomaly_count,
            'processing_time': processing_time,
            'uploaded_by': uploaded_by,
            'created_at': datetime.utcnow()
        }
        
        doc_ref = db.collection(VideoService.COLLECTION).document()
        doc_ref.set(video_data)
        video_data['id'] = doc_ref.id
        return video_data
    
    @staticmethod
    def get_all_videos():
        if not db: return []
        docs = db.collection(VideoService.COLLECTION).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        videos = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            videos.append(data)
        return videos
    
    @staticmethod
    def delete_video(video_id):
        if not db: return False
        db.collection(VideoService.COLLECTION).document(video_id).delete()
        return True
    
    @staticmethod
    def count_videos(status=None):
        if not db: return 0
        query = db.collection(VideoService.COLLECTION)
        if status:
            query = query.where('status', '==', status)
        return len(list(query.stream()))