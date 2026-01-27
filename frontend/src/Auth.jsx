import React, { useState } from 'react';
import { User, Mail, Lock, Phone, Building, X } from 'lucide-react';
import { auth, googleProvider } from './firebase';
import { signInWithPopup } from 'firebase/auth';
import './Auth.css';

const Auth = ({ onLogin }) => {
    const [isRightPanelActive, setIsRightPanelActive] = useState(false);
    const [loginData, setLoginData] = useState({ username: '', password: '' });
    const [signupData, setSignupData] = useState({ username: '', email: '', password: '', phone: '', department: '' });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [showForgotModal, setShowForgotModal] = useState(false);


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

    const handleGoogleSignIn = async () => {
        setError('');
        setLoading(true);

        try {
            const result = await signInWithPopup(auth, googleProvider);
            const idToken = await result.user.getIdToken();

            // Send token to backend for verification and user creation
            const response = await fetch('http://localhost:5000/api/auth/google', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ idToken })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Google sign-in failed');
            }

            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            onLogin(data.user);
        } catch (err) {
            console.error('Google Sign-In Error:', err);
            setError(err.message || 'Google sign-in failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className={`auth-container ${isRightPanelActive ? 'right-panel-active' : ''}`}>

                {/* Sign Up Form - Clean & Modern */}
                <div className="form-container sign-up-container">
                    <form onSubmit={handleSignup}>
                        <h1>Create Account</h1>

                        {/* Google Sign-In Button */}
                        <button type="button" className="google-btn-gradient" onClick={handleGoogleSignIn} disabled={loading}>
                            <span className="google-g">G</span>
                            <span className="google-text">Sign in with Google</span>
                        </button>

                        <div className="divider">
                            <span>or register with email</span>
                        </div>

                        {/* Two-column layout for cleaner look */}
                        <div className="form-row">
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

                        <div className="form-row">
                            <div className="input-group">
                                <Phone size={18} className="input-icon" />
                                <input
                                    type="tel"
                                    placeholder="Phone"
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

                        {/* Google Sign-In Button */}
                        <button type="button" className="google-btn-gradient" onClick={handleGoogleSignIn} disabled={loading}>
                            <span className="google-g">G</span>
                            <span className="google-text">Continue with Google</span>
                        </button>

                        <div className="divider">
                            <span>or use your account</span>
                        </div>

                        <div className="input-group">
                            <User size={18} className="input-icon" />
                            <input
                                type="text"
                                placeholder="Username or Email"
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

                        <a href="#" className="forgot-link" onClick={(e) => { e.preventDefault(); setShowForgotModal(true); }}>Forgot your password?</a>
                        {error && <p className="error-text">{error}</p>}
                        <button type="submit" className="auth-btn" disabled={loading}>
                            {loading ? 'Please wait...' : 'Login'}
                        </button>
                    </form>
                </div>

                {/* Overlay Container */}
                <div className="overlay-container">
                    <div className="overlay">
                        {/* Cosmic Elements */}
                        <div className="cosmic-elements">
                            <div className="comet comet-1"></div>
                            <div className="comet comet-2"></div>
                            <div className="comet comet-3"></div>
                            <div className="comet comet-4"></div>
                            <div className="star star-1"></div>
                            <div className="star star-2"></div>
                            <div className="star star-3"></div>
                        </div>

                        <div className="overlay-panel overlay-left">
                            <h1>Welcome Back!</h1>
                            <p>Already have an account? Sign in to access your security dashboard</p>
                            <button
                                className="ghost-btn"
                                onClick={() => setIsRightPanelActive(false)}
                            >
                                Sign In
                            </button>
                        </div>
                        <div className="overlay-panel overlay-right">
                            <h1>Hello, Welcome!</h1>
                            <p>Join Alertrix and start monitoring with AI-powered security</p>
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

            {/* Forgot Password Modal */}
            {showForgotModal && (
                <div className="modal-overlay" onClick={() => setShowForgotModal(false)}>
                    <div className="forgot-modal" onClick={(e) => e.stopPropagation()}>
                        <button className="modal-close-btn" onClick={() => setShowForgotModal(false)}>
                            <X size={20} />
                        </button>
                        <h2>Reset Password</h2>
                        <p className="modal-message">Please contact your administrator to reset your password.</p>
                        <button className="auth-btn" onClick={() => setShowForgotModal(false)}>
                            OK
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Auth;
