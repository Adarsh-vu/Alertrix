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

# ==========================================
# PERSONNEL OPERATIONS (Firestore)
# ==========================================
class PersonnelService:
    COLLECTION = 'personnel'
    
    @staticmethod
    def create_personnel(name, phone, age, address='', aadhaar=''):
        """Create a new personnel document"""
        if not db: return None
            
        personnel_data = {
            'name': name,
            'phone': phone,
            'age': age,
            'address': address,
            'aadhaar': aadhaar,
            'created_at': datetime.utcnow()
        }
        
        doc_ref = db.collection(PersonnelService.COLLECTION).document()
        doc_ref.set(personnel_data)
        personnel_data['id'] = doc_ref.id
        return personnel_data
    
    @staticmethod
    def get_all_personnel():
        if not db: return []
        docs = db.collection(PersonnelService.COLLECTION).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        personnel = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            personnel.append(data)
        return personnel
    
    @staticmethod
    def get_personnel_by_id(personnel_id):
        if not db: return None
        doc = db.collection(PersonnelService.COLLECTION).document(personnel_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    @staticmethod
    def update_personnel(personnel_id, updates):
        if not db: return False
        db.collection(PersonnelService.COLLECTION).document(personnel_id).update(updates)
        return True
    
    @staticmethod
    def delete_personnel(personnel_id):
        if not db: return False
        db.collection(PersonnelService.COLLECTION).document(personnel_id).delete()
        return True

# ==========================================
# CAMERA MANAGEMENT (Firestore)
# ==========================================
class CameraService:
    COLLECTION = 'cameras'
    MAX_BULK_SIZE = 8 
    
    @staticmethod
    def create_camera(name, location, source, source_id, created_by=None):
        """Create a new camera entry"""
        if not db: return None
        
        camera_data = {
            'name': name,
            'location': location,
            'source': source,  # RTSP/HTTP URL
            'source_id': source_id,
            'status': 'offline',
            'visible': True,
            'created_by': created_by,
            'created_at': datetime.utcnow()
        }
        
        doc_ref = db.collection(CameraService.COLLECTION).document()
        doc_ref.set(camera_data)
        camera_data['id'] = doc_ref.id
        return camera_data
    
    @staticmethod
    def bulk_create_cameras(name_prefix, location, rtsp_template, start_value, end_value, created_by=None):
        """
        Create multiple cameras using an RTSP template.
        Template uses {X} as placeholder for the varying value.
        
        Returns: list of {camera, success, error} dicts
        """
        if not db: return []
        
        results = []
        count = end_value - start_value + 1
        
        # Enforce bulk size limit
        if count > CameraService.MAX_BULK_SIZE:
            return [{'success': False, 'error': f'Bulk size exceeds limit of {CameraService.MAX_BULK_SIZE}'}]
        
        if count <= 0:
            return [{'success': False, 'error': 'End value must be greater than or equal to start value'}]
        
        if '{X}' not in rtsp_template:
            return [{'success': False, 'error': 'RTSP template must contain {X} placeholder'}]
        
        for i in range(start_value, end_value + 1):
            try:
                # Generate source URL by replacing {X} with current value
                source_url = rtsp_template.replace('{X}', str(i))
                camera_name = f"{name_prefix}{i}"
                source_id = f"cam_{name_prefix.lower().replace(' ', '_')}{i}"
                
                camera = CameraService.create_camera(
                    name=camera_name,
                    location=location,
                    source=source_url,
                    source_id=source_id,
                    created_by=created_by
                )
                
                if camera:
                    results.append({'camera': camera, 'success': True, 'error': None})
                else:
                    results.append({'camera': None, 'success': False, 'error': 'Failed to create camera'})
            except Exception as e:
                results.append({'camera': None, 'success': False, 'error': str(e)})
        
        return results
    
    @staticmethod
    def get_all_cameras():
        if not db: return []
        docs = db.collection(CameraService.COLLECTION).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        cameras = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            cameras.append(data)
        return cameras
    
    @staticmethod
    def get_camera_by_id(camera_id):
        if not db: return None
        doc = db.collection(CameraService.COLLECTION).document(camera_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    @staticmethod
    def update_camera(camera_id, updates):
        if not db: return False
        db.collection(CameraService.COLLECTION).document(camera_id).update(updates)
        return True
    
    @staticmethod
    def delete_camera(camera_id):
        if not db: return False
        db.collection(CameraService.COLLECTION).document(camera_id).delete()
        return True
    
    @staticmethod
    def seed_demo_cameras():
        """
        Seed 4 demo cameras if no cameras exist in the database.
        Uses placeholder URLs since real CCTV feeds aren't available.
        """
        if not db: return []
        
        # Check if cameras already exist
        existing = list(db.collection(CameraService.COLLECTION).limit(1).stream())
        if existing:
            print("[CameraService] Demo cameras already exist, skipping seed.")
            return []
        
        # Demo camera configurations - 1 added via single, 3 via group for demo
        demo_cameras = [
            {
                'name': 'Camera 1 - Entrance',
                'location': 'Main Entrance',
                'source': 'demo://entrance',
                'source_id': 'demo_cam_entrance',
                'status': 'active',
                'visible': True,
                'addedVia': 'single'
            {
                'name': 'Camera 2 - Parking',
                'location': 'Parking Lot A',
                'source': 'demo://parking',
                'source_id': 'demo_cam_parking',
                'status': 'active',
                'visible': True,
                'addedVia': 'group'
            },
            {
                'name': 'Camera 3 - Hallway',
                'location': 'Main Hallway',
                'source': 'demo://hallway',
                'source_id': 'demo_cam_hallway',
                'status': 'offline',
                'visible': True,
                'addedVia': 'group'
            },
            {
                'name': 'Camera 4 - Exit',
                'location': 'Emergency Exit',
                'source': 'demo://exit',
                'source_id': 'demo_cam_exit',
                'status': 'active',
                'visible': True,
                'addedVia': 'group'
            }
        ]
        
        created_cameras = []
        for cam_data in demo_cameras:
            cam_data['created_by'] = 'system'
            cam_data['created_at'] = datetime.utcnow()
            
            doc_ref = db.collection(CameraService.COLLECTION).document()
            doc_ref.set(cam_data)
            cam_data['id'] = doc_ref.id
            created_cameras.append(cam_data)
        
        print(f"[CameraService] Seeded {len(created_cameras)} demo cameras to Firebase.")
        return created_cameras