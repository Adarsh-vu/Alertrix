import { useState, useEffect } from 'react';
import Dashboard from './Dashboard';
import Auth from './Auth';
import ProfileCompletion from './ProfileCompletion';
import './index.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const token = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');

    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  const handleProfileComplete = (updatedUser) => {
    setUser(updatedUser);
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading Alertrix...</p>
      </div>
    );
  }

  // Not logged in -> show Auth
  if (!user) {
    return <Auth onLogin={handleLogin} />;
  }

  // Logged in but profile not complete -> show ProfileCompletion
  if (user.profile_complete === false) {
    return <ProfileCompletion user={user} onComplete={handleProfileComplete} />;
  }

  // Logged in and profile complete -> show Dashboard
  return <Dashboard user={user} onLogout={handleLogout} />;
}

export default App;
