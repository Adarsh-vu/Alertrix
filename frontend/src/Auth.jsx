import React, { useState } from 'react';
import { User, Mail, Lock, Github, Phone, Building } from 'lucide-react';
import './Auth.css';

const Auth = ({ onLogin }) => {
    const [isRightPanelActive, setIsRightPanelActive] = useState(false);
    const [loginData, setLoginData] = useState({ username: '', password: '' });
    const [signupData, setSignupData] = useState({ username: '', email: '', password: '', phone: '', department: '' });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await fetch('http://localhost:5000/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(loginData)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Login failed');
            }

            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            onLogin(data.user);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSignup = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await fetch('http://localhost:5000/api/auth/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(signupData)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Signup failed');
            }

            // Auto switch to login after successful signup
            setIsRightPanelActive(false);
            setLoginData({ username: signupData.username, password: '' });
            setError('');
            alert('Registration successful! Please login.');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className={`auth-container ${isRightPanelActive ? 'right-panel-active' : ''}`}>

                {/* Sign Up Form */}
                <div className="form-container sign-up-container">
                    <form onSubmit={handleSignup}>
                        <h1>Create Account</h1>
                        <div className="social-container">
                            <a href="#" className="social"><i className="fab fa-google"></i></a>
                            <a href="#" className="social"><i className="fab fa-facebook-f"></i></a>
                            <a href="#" className="social"><Github size={18} /></a>
                            <a href="#" className="social"><i className="fab fa-linkedin-in"></i></a>
                        </div>
                        <span>or use your email for registration</span>

                        <div className="input-group">
                            <User size={18} className="input-icon" />
                            <input
                                type="text"
                                placeholder="Username"
                                value={signupData.username}
                                onChange={(e) => setSignupData({ ...signupData, username: e.target.value })}
                                required
                            />
                        </div>
                        <div className="input-group">
                            <Mail size={18} className="input-icon" />
                            <input
                                type="email"
                                placeholder="Email"
                                value={signupData.email}
                                onChange={(e) => setSignupData({ ...signupData, email: e.target.value })}
                                required
                            />
                        </div>
                        <div className="input-group">
                            <Lock size={18} className="input-icon" />
                            <input
                                type="password"
                                placeholder="Password"
                                value={signupData.password}
                                onChange={(e) => setSignupData({ ...signupData, password: e.target.value })}
                                required
                            />
                        </div>
                        <div className="input-group">
                            <Phone size={18} className="input-icon" />
                            <input
                                type="tel"
                                placeholder="Phone Number"
                                value={signupData.phone}
                                onChange={(e) => setSignupData({ ...signupData, phone: e.target.value })}
                                required
                            />
                        </div>
                        <div className="input-group">
                            <Building size={18} className="input-icon" />
                            <input
                                type="text"
                                placeholder="Department"
                                value={signupData.department}
                                onChange={(e) => setSignupData({ ...signupData, department: e.target.value })}
                                required
                            />
                        </div>

                        {error && <p className="error-text">{error}</p>}
                        <button type="submit" className="auth-btn" disabled={loading}>
                            {loading ? 'Please wait...' : 'Register'}
                        </button>
                    </form>
                </div>

                {/* Sign In Form */}
                <div className="form-container sign-in-container">
                    <form onSubmit={handleLogin}>
                        <h1>Sign In</h1>
                        <div className="social-container">
                            <a href="#" className="social"><i className="fab fa-google"></i></a>
                            <a href="#" className="social"><i className="fab fa-facebook-f"></i></a>
                            <a href="#" className="social"><Github size={18} /></a>
                            <a href="#" className="social"><i className="fab fa-linkedin-in"></i></a>
                        </div>
                        <span>or use your account</span>

                        <div className="input-group">
                            <User size={18} className="input-icon" />
                            <input
                                type="text"
                                placeholder="Username"
                                value={loginData.username}
                                onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                                required
                            />
                        </div>
                        <div className="input-group">
                            <Lock size={18} className="input-icon" />
                            <input
                                type="password"
                                placeholder="Password"
                                value={loginData.password}
                                onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                                required
                            />
                        </div>

                        <a href="#" className="forgot-link">Forgot your password?</a>
                        {error && <p className="error-text">{error}</p>}
                        <button type="submit" className="auth-btn" disabled={loading}>
                            {loading ? 'Please wait...' : 'Login'}
                        </button>
                    </form>
                </div>

                {/* Overlay Container */}
                <div className="overlay-container">
                    <div className="overlay">
                        <div className="overlay-panel overlay-left">
                            <h1>Welcome Back!</h1>
                            <p>To keep connected with us please login with your personal info</p>
                            <button
                                className="ghost-btn"
                                onClick={() => setIsRightPanelActive(false)}
                            >
                                Sign In
                            </button>
                        </div>
                        <div className="overlay-panel overlay-right">
                            <h1>Hello, Welcome!</h1>
                            <p>Enter your personal details and start your journey with us</p>
                            <button
                                className="ghost-btn"
                                onClick={() => setIsRightPanelActive(true)}
                            >
                                Sign Up
                            </button>
                        </div>
                    </div>
                </div>

                {/* Mobile Toggle */}
                <div className="mobile-toggle">
                    {isRightPanelActive ? (
                        <p>Already have an account? <span onClick={() => setIsRightPanelActive(false)}>Sign In</span></p>
                    ) : (
                        <p>Don't have an account? <span onClick={() => setIsRightPanelActive(true)}>Register</span></p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Auth;
