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
        return jsonify({'error': 'Account is deactivated'}), 401
    
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
