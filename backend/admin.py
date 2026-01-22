"""
Alertrix - Admin Routes
Admin-only endpoints for personnel and system management (Firebase)
"""

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from auth import token_required, admin_required, format_user
from models import UserService, VideoService

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
