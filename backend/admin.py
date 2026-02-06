"""
Alertrix - Admin Routes
Admin-only endpoints for personnel and system management (Firebase)
"""

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from auth import token_required, admin_required, format_user
from models import UserService, VideoService, PersonnelService, CameraService
import re
import cv2

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# ==========================================
# USER/PERSONNEL MANAGEMENT
# ==========================================

@admin_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def get_all_users(current_user):
    """Get all users (admin only)"""
    users = UserService.get_all_users()
    return jsonify({
        'users': [format_user(u) for u in users],
        'total': len(users)
    })

@admin_bp.route('/users', methods=['POST'])
@token_required
@admin_required
def create_user(current_user):
    """Create a new user (admin only)"""
    data = request.get_json()
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'officer')
    phone = data.get('phone', '')
    shift = data.get('shift', '08:00-20:00')
    department = data.get('department', 'Security Operations')
    
    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required'}), 400
    
    if role not in ['admin', 'officer']:
        return jsonify({'error': 'Invalid role'}), 400
    
    if UserService.get_user_by_username(username):
        return jsonify({'error': 'Username already exists'}), 400
    
    if UserService.get_user_by_email(email):
        return jsonify({'error': 'Email already registered'}), 400
    
    password_hash = generate_password_hash(password)
    new_user = UserService.create_user(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        phone=phone,
        shift=shift,
        department=department
    )
    
    return jsonify({
        'message': 'User created successfully',
        'user': format_user(new_user)
    }), 201

@admin_bp.route('/users/<user_id>', methods=['GET'])
@token_required
@admin_required
def get_user(current_user, user_id):
    """Get a specific user"""
    user = UserService.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': format_user(user)})

@admin_bp.route('/users/<user_id>', methods=['PUT'])
@token_required
@admin_required
def update_user(current_user, user_id):
    """Update user details"""
    user = UserService.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    updates = {}
    
    if 'phone' in data:
        updates['phone'] = data['phone']
    if 'shift' in data:
        updates['shift'] = data['shift']
    if 'department' in data:
        updates['department'] = data['department']
    if 'role' in data and data['role'] in ['admin', 'officer']:
        if user['role'] == 'admin' and data['role'] == 'officer':
            if UserService.count_users(role='admin', is_active=True) <= 1:
                return jsonify({'error': 'Cannot demote the last admin'}), 400
        updates['role'] = data['role']
    if 'is_active' in data:
        if user['role'] == 'admin' and not data['is_active']:
            if UserService.count_users(role='admin', is_active=True) <= 1:
                return jsonify({'error': 'Cannot deactivate the last admin'}), 400
        updates['is_active'] = data['is_active']
    if 'password' in data and data['password']:
        updates['password_hash'] = generate_password_hash(data['password'])
    
    if updates:
        UserService.update_user(user_id, updates)
    
    updated_user = UserService.get_user_by_id(user_id)
    return jsonify({
        'message': 'User updated successfully',
        'user': format_user(updated_user)
    })

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, user_id):
    """Delete a user"""
    user = UserService.get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user['id'] == current_user['id']:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    if user['role'] == 'admin':
        if UserService.count_users(role='admin', is_active=True) <= 1:
            return jsonify({'error': 'Cannot delete the last admin'}), 400
    
    UserService.delete_user(user_id)
    return jsonify({'message': 'User deleted successfully'})

# ==========================================
# VIDEO EVIDENCE MANAGEMENT
# ==========================================

@admin_bp.route('/videos', methods=['GET'])
@token_required
@admin_required
def get_all_videos(current_user):
    """Get all video evidence"""
    videos = VideoService.get_all_videos()
    return jsonify({
        'videos': videos,
        'total': len(videos)
    })

@admin_bp.route('/videos/<video_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_video(current_user, video_id):
    """Delete video record"""
    VideoService.delete_video(video_id)
    return jsonify({'message': 'Video deleted successfully'})

# ==========================================
# ADMIN STATS
# ==========================================

@admin_bp.route('/stats', methods=['GET'])
@token_required
@admin_required
def get_admin_stats(current_user):
    """Get admin dashboard statistics"""
    return jsonify({
        'users': {
            'total': UserService.count_users(),
            'active': UserService.count_users(is_active=True),
            'admins': UserService.count_users(role='admin'),
            'officers': UserService.count_users(role='officer')
        },
        'videos': {
            'total': VideoService.count_videos(),
            'anomalies': VideoService.count_videos(status='ANOMALY DETECTED')
        }
    })

# ==========================================
# PERSONNEL MANAGEMENT
# ==========================================

def validate_aadhaar(aadhaar):
    """Validate Aadhaar number - must be exactly 12 digits"""
    if not aadhaar:
        return True
    aadhaar_clean = re.sub(r'\s+', '', aadhaar)
    return bool(re.match(r'^\d{12}$', aadhaar_clean))

@admin_bp.route('/personnel', methods=['GET'])
@token_required
@admin_required
def get_all_personnel(current_user):
    """Get all personnel on duty"""
    personnel = PersonnelService.get_all_personnel()
    return jsonify({
        'personnel': personnel,
        'total': len(personnel)
    })

@admin_bp.route('/personnel', methods=['POST'])
@token_required
@admin_required
def create_personnel(current_user):
    """Create a new personnel"""
    data = request.get_json()
    
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    age = data.get('age', '')
    address = data.get('address', '').strip()
    aadhaar = data.get('aadhaar', '').strip()
    
    if not name or not phone:
        return jsonify({'error': 'Name and phone are required'}), 400
    
    if not age:
        return jsonify({'error': 'Age is required'}), 400
    
    if not address:
        return jsonify({'error': 'Address is required'}), 400
    
    if not aadhaar:
        return jsonify({'error': 'Aadhaar number is required'}), 400
    
    # Validate Aadhaar - must be exactly 12 digits
    if not validate_aadhaar(aadhaar):
        return jsonify({'error': 'Aadhaar must be exactly 12 digits'}), 400
    
    # Clean Aadhaar (remove spaces)
    aadhaar_clean = re.sub(r'\s+', '', aadhaar) if aadhaar else ''
    
    personnel = PersonnelService.create_personnel(
        name=name,
        phone=phone,
        age=str(age),
        address=address,
        aadhaar=aadhaar_clean
    )
    
    if not personnel:
        return jsonify({'error': 'Failed to create personnel'}), 500
    
    return jsonify({
        'message': 'Personnel created successfully',
        'personnel': personnel
    }), 201

@admin_bp.route('/personnel/<personnel_id>', methods=['PUT'])
@token_required
@admin_required
def update_personnel(current_user, personnel_id):
    """Update personnel details"""
    person = PersonnelService.get_personnel_by_id(personnel_id)
    if not person:
        return jsonify({'error': 'Personnel not found'}), 404
    
    data = request.get_json()
    updates = {}
    
    if 'name' in data:
        updates['name'] = data['name'].strip()
    if 'phone' in data:
        updates['phone'] = data['phone'].strip()
    if 'age' in data:
        updates['age'] = str(data['age'])
    if 'address' in data:
        updates['address'] = data['address'].strip()
    if 'aadhaar' in data:
        aadhaar = data['aadhaar'].strip()
        if aadhaar and not validate_aadhaar(aadhaar):
            return jsonify({'error': 'Aadhaar must be exactly 12 digits'}), 400
        updates['aadhaar'] = re.sub(r'\s+', '', aadhaar) if aadhaar else ''
    
    if updates:
        PersonnelService.update_personnel(personnel_id, updates)
    
    updated = PersonnelService.get_personnel_by_id(personnel_id)
    return jsonify({
        'message': 'Personnel updated successfully',
        'personnel': updated
    })

@admin_bp.route('/personnel/<personnel_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_personnel(current_user, personnel_id):
    """Delete a personnel"""
    person = PersonnelService.get_personnel_by_id(personnel_id)
    if not person:
        return jsonify({'error': 'Personnel not found'}), 404
    
    PersonnelService.delete_personnel(personnel_id)
    return jsonify({'message': 'Personnel deleted successfully'})

# ==========================================
# CAMERA MANAGEMENT
# ==========================================

def format_camera(camera):
    if not camera:
        return None
    return {
        'id': camera.get('id'),
        'name': camera.get('name'),
        'location': camera.get('location'),
        'source_id': camera.get('source_id'),
        'status': camera.get('status', 'offline'),
        'visible': camera.get('visible', True),
        'created_at': str(camera.get('created_at')) if camera.get('created_at') else None
    }

def format_camera_full(camera):
    """Format camera data with source URL (admin only)"""
    if not camera:
        return None
    formatted = format_camera(camera)
    formatted['source'] = camera.get('source')
    return formatted

@admin_bp.route('/cameras', methods=['GET'])
@token_required
@admin_required
def get_all_cameras(current_user):
    """Get all cameras (admin only)"""
    cameras = CameraService.get_all_cameras()
    return jsonify({
        'cameras': [format_camera_full(c) for c in cameras],
        'total': len(cameras)
    })

@admin_bp.route('/cameras', methods=['POST'])
@token_required
@admin_required
def create_camera(current_user):
    """Create a single camera"""
    data = request.get_json()
    
    name = data.get('name', '').strip()
    location = data.get('location', '').strip()
    source = data.get('source', '').strip()
    
    if not name or not source:
        return jsonify({'error': 'Name and source (RTSP URL) are required'}), 400
    
    # Generate source_id from name
    source_id = f"cam_{name.lower().replace(' ', '_')}_{len(CameraService.get_all_cameras()) + 1}"
    
    camera = CameraService.create_camera(
        name=name,
        location=location,
        source=source,
        source_id=source_id,
        created_by=current_user.get('id')
    )
    
    if not camera:
        return jsonify({'error': 'Failed to create camera'}), 500
    
    return jsonify({
        'message': 'Camera created successfully',
        'camera': format_camera_full(camera)
    }), 201

@admin_bp.route('/cameras/bulk', methods=['POST'])
@token_required
@admin_required
def bulk_create_cameras(current_user):
    """
    Bulk create cameras using RTSP template.
    
    Expected payload:
    {
        "name_prefix": "CAM-",
        "location": "Building A",
        "rtsp_template": "rtsp://user:pass@192.168.1.{X}:554/stream1",
        "start_value": 101,
        "end_value": 108
    }
    """
    data = request.get_json()
    
    name_prefix = data.get('name_prefix', '').strip()
    location = data.get('location', '').strip()
    rtsp_template = data.get('rtsp_template', '').strip()
    start_value = data.get('start_value')
    end_value = data.get('end_value')
    
    # Validation
    if not name_prefix:
        return jsonify({'error': 'Camera name prefix is required'}), 400
    
    if not rtsp_template:
        return jsonify({'error': 'RTSP template is required'}), 400
    
    if start_value is None or end_value is None:
        return jsonify({'error': 'Start and end values are required'}), 400
    
    try:
        start_value = int(start_value)
        end_value = int(end_value)
    except (ValueError, TypeError):
        return jsonify({'error': 'Start and end values must be integers'}), 400
    
    # Call bulk create
    results = CameraService.bulk_create_cameras(
        name_prefix=name_prefix,
        location=location,
        rtsp_template=rtsp_template,
        start_value=start_value,
        end_value=end_value,
        created_by=current_user.get('id')
    )
    
    # Check for validation errors
    if len(results) == 1 and not results[0].get('success') and results[0].get('error'):
        return jsonify({'error': results[0]['error']}), 400
    
    # Format results
    formatted_results = []
    success_count = 0
    for r in results:
        if r.get('success'):
            success_count += 1
            formatted_results.append({
                'success': True,
                'camera': format_camera_full(r.get('camera'))
            })
        else:
            formatted_results.append({
                'success': False,
                'error': r.get('error')
            })
    
    return jsonify({
        'message': f'Created {success_count} of {len(results)} cameras',
        'results': formatted_results,
        'success_count': success_count,
        'total': len(results)
    }), 201 if success_count > 0 else 400

@admin_bp.route('/cameras/<camera_id>', methods=['PUT'])
@token_required
@admin_required
def update_camera(current_user, camera_id):
    """Update camera details"""
    camera = CameraService.get_camera_by_id(camera_id)
    if not camera:
        return jsonify({'error': 'Camera not found'}), 404
    
    data = request.get_json()
    updates = {}
    
    if 'name' in data:
        updates['name'] = data['name'].strip()
    if 'location' in data:
        updates['location'] = data['location'].strip()
    if 'source' in data:
        updates['source'] = data['source'].strip()
    if 'visible' in data:
        updates['visible'] = bool(data['visible'])
    if 'status' in data:
        updates['status'] = data['status']
    
    if updates:
        CameraService.update_camera(camera_id, updates)
    
    updated = CameraService.get_camera_by_id(camera_id)
    return jsonify({
        'message': 'Camera updated successfully',
        'camera': format_camera_full(updated)
    })

@admin_bp.route('/cameras/<camera_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_camera(current_user, camera_id):
    """Delete a camera"""
    camera = CameraService.get_camera_by_id(camera_id)
    if not camera:
        return jsonify({'error': 'Camera not found'}), 404
    
    CameraService.delete_camera(camera_id)
    return jsonify({'message': 'Camera deleted successfully'})

@admin_bp.route('/cameras/test-rtsp', methods=['POST'])
@token_required
@admin_required
def test_rtsp_connection(current_user):
    data = request.get_json()
    rtsp_url = data.get('rtsp_url', '').strip()
    
    if not rtsp_url:
        return jsonify({'error': 'RTSP URL is required'}), 400
    
    try:
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Try to read one frame with timeout
        ret, frame = cap.read()
        cap.release()
        
        if ret and frame is not None:
            return jsonify({
                'success': True,
                'message': 'Connection successful - stream is accessible'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not read from stream - check URL and credentials'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Connection failed: {str(e)}'
        })

