"""
Alertrix - Authentication Routes
JWT-based authentication with Firebase Firestore
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from firebase_admin import auth as firebase_auth

from models import UserService, init_firebase

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Secret key for JWT
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'alertrix-secret-key-change-in-production')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = UserService.get_user_by_id(data['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
            if not current_user.get('is_active', True):
                return jsonify({'error': 'Account is deactivated'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

def format_user(user):
    """Format user data for JSON response (remove sensitive fields)"""
    if not user:
        return None
    return {
        'id': user.get('id'),
        'username': user.get('username'),
        'email': user.get('email'),
        'role': user.get('role'),
        'phone': user.get('phone'),
        'shift': user.get('shift'),
        'department': user.get('department'),
        'is_active': user.get('is_active', True),
        'profile_complete': user.get('profile_complete', True),
        'created_at': str(user.get('created_at')) if user.get('created_at') else None
    }

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    phone = data.get('phone', '').strip()
    department = data.get('department', '').strip()
    
    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required'}), 400
    
    if not phone or not department:
        return jsonify({'error': 'Phone and department are required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    # Check existing users
    if UserService.get_user_by_username(username):
        return jsonify({'error': 'Username already exists'}), 400
    
    if UserService.get_user_by_email(email):
        return jsonify({'error': 'Email already registered'}), 400
    
    # First user becomes admin (admin has no shift)
    is_first_user = UserService.count_users() == 0
    role = 'admin' if is_first_user else 'officer'
    
    password_hash = generate_password_hash(password)
    new_user = UserService.create_user(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        phone=phone,
        department=department,
        shift='' if role == 'admin' else '08:00-20:00'  # Only officers have shifts
    )
    
    if not new_user:
        return jsonify({'error': 'Database not initialized. Add Firebase credentials.'}), 500
    
    return jsonify({
        'message': 'User registered successfully',
        'user': format_user(new_user)
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    # Allow login with username or email
    user = UserService.get_user_by_username(username)
    if not user:
        user = UserService.get_user_by_email(username)
    
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401
    
    if not check_password_hash(user.get('password_hash', ''), password):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    if not user.get('is_active', True):
        return jsonify({'error': 'Account locked. Please contact your administrator.', 'locked': True}), 401
    
    # Generate JWT token (24 hour expiry)
    token = jwt.encode({
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, SECRET_KEY, algorithm='HS256')
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': format_user(user)
    })

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    # Check if user is still active
    if not current_user.get('is_active', True):
        return jsonify({'error': 'Account deactivated', 'locked': True}), 401
    return jsonify({'user': format_user(current_user)})

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    data = request.get_json()
    
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    if not check_password_hash(current_user.get('password_hash', ''), old_password):
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    
    new_hash = generate_password_hash(new_password)
    UserService.update_user(current_user['id'], {'password_hash': new_hash})
    
    return jsonify({'message': 'Password changed successfully'})

@auth_bp.route('/admin/reset-password', methods=['POST'])
@token_required
def admin_reset_password(current_user):
    """Admin can reset any user's password"""
    if current_user.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('new_password', '')
    
    if not user_id or not new_password:
        return jsonify({'error': 'User ID and new password are required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    target_user = UserService.get_user_by_id(user_id)
    if not target_user:
        return jsonify({'error': 'User not found'}), 404
    
    new_hash = generate_password_hash(new_password)
    UserService.update_user(user_id, {'password_hash': new_hash})
    
    return jsonify({'message': f"Password reset for {target_user['username']}"})

@auth_bp.route('/google', methods=['POST'])
def google_signin():
    """Handle Google Sign-In - verify token and create/return user"""
    data = request.get_json()
    
    if not data or 'idToken' not in data:
        return jsonify({'error': 'ID token is required'}), 400
    
    try:
        # Verify the Google ID token using Firebase Admin SDK
        decoded_token = firebase_auth.verify_id_token(data['idToken'])
        google_uid = decoded_token['uid']
        email = decoded_token.get('email', '').lower()
        name = decoded_token.get('name', email.split('@')[0])
        
        if not email:
            return jsonify({'error': 'Email not provided by Google'}), 400
        
        # Check if user already exists by email
        user = UserService.get_user_by_email(email)
        
        if not user:
            # First user becomes admin
            is_first_user = UserService.count_users() == 0
            role = 'admin' if is_first_user else 'officer'
            
            # Create new user (Google users don't have password)
            user = UserService.create_user(
                username=name,
                email=email,
                password_hash='',  # No password for Google users
                role=role,
                phone='',  # Will be collected via profile completion
                department='',
                shift='' if role == 'admin' else '08:00-20:00',
                google_uid=google_uid,
                profile_complete=False  # Needs to complete profile
            )
            
            if not user:
                return jsonify({'error': 'Failed to create user'}), 500
        else:
            # Update google_uid if not set
            if not user.get('google_uid'):
                UserService.update_user(user['id'], {'google_uid': google_uid})
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, SECRET_KEY, algorithm='HS256')
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': format_user(user)
        })
        
    except firebase_auth.InvalidIdTokenError:
        return jsonify({'error': 'Invalid Google token'}), 401
    except Exception as e:
        print(f"Google Sign-In Error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@auth_bp.route('/complete-profile', methods=['POST'])
@token_required
def complete_profile(current_user):
    """Complete profile for Google users - add phone, department, and password"""
    data = request.get_json()
    
    phone = data.get('phone', '').strip()
    department = data.get('department', '').strip()
    password = data.get('password', '')
    
    if not phone or not department:
        return jsonify({'error': 'Phone and department are required'}), 400
    
    if not password or len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    updates = {
        'phone': phone,
        'department': department,
        'password_hash': generate_password_hash(password),
        'profile_complete': True
    }
    
    UserService.update_user(current_user['id'], updates)
    updated_user = UserService.get_user_by_id(current_user['id'])
    
    return jsonify({
        'message': 'Profile completed successfully',
        'user': format_user(updated_user)
    })

