import React, { useState } from 'react';
import { Phone, Building, User, Shield, Lock } from 'lucide-react';
import './Auth.css';

const ProfileCompletion = ({ user, onComplete }) => {
    const [formData, setFormData] = useState({ phone: '', department: '', password: '', confirmPassword: '' });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (formData.password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        setLoading(true);

        try {
            const token = localStorage.getItem('token');
            const response = await fetch('http://localhost:5000/api/auth/complete-profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    phone: formData.phone,
                    department: formData.department,
                    password: formData.password
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to complete profile');
            }

            // Update stored user data
            localStorage.setItem('user', JSON.stringify(data.user));
            onComplete(data.user);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="profile-completion-card">
                <div className="profile-header-section">
                    <div className="profile-icon-wrapper">
                        <Shield size={40} />
                    </div>
                    <h1>Complete Your Profile</h1>
                    <p>Set up your password and details to enable email login</p>
                </div>

                <div className="user-info-preview">
                    <div className="user-avatar">
                        <User size={24} />
                    </div>
                    <div className="user-details">
                        <span className="user-name">{user?.username || 'User'}</span>
                        <span className="user-email">{user?.email}</span>
                    </div>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="input-group">
                        <Lock size={18} className="input-icon" />
                        <input
                            type="password"
                            placeholder="Create Password"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <Lock size={18} className="input-icon" />
                        <input
                            type="password"
                            placeholder="Confirm Password"
                            value={formData.confirmPassword}
                            onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <Phone size={18} className="input-icon" />
                        <input
                            type="tel"
                            placeholder="Phone Number"
                            value={formData.phone}
                            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <Building size={18} className="input-icon" />
                        <input
                            type="text"
                            placeholder="Department"
                            value={formData.department}
                            onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                            required
                        />
                    </div>

                    {error && <p className="error-text">{error}</p>}

                    <button type="submit" className="auth-btn full-width" disabled={loading}>
                        {loading ? 'Saving...' : 'Complete Profile'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ProfileCompletion;
