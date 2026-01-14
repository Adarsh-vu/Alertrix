import React, { useState, useEffect, useRef } from 'react';
import bannerImage from './assets/banner.jpg';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area
} from 'recharts';
import {
    Camera,
    Upload,
    Activity,
    AlertTriangle,
    Bell,
    BellOff,
    Settings,
    Users,
    Cpu,
    LayoutDashboard,
    Radio,
    Brain,
    User,
    LogOut,
    Shield,
    Mail,
    Phone,
    Clock,
    CheckCircle,
    XCircle,
    Volume2,
    VolumeX,
    FileVideo,
    Play,
    Trash2,
    Save,
    ChevronDown,
    Plus,
    Edit2,
    Check,
    Eye,
    EyeOff
} from 'lucide-react';

const Dashboard = () => {
    const [activeTab, setActiveTab] = useState('dashboard');
    const [isConnected, setIsConnected] = useState(false);
    const [currentScore, setCurrentScore] = useState(0);
    const [alertCount, setAlertCount] = useState(3);
    const [alertsMuted, setAlertsMuted] = useState(false);
    const [showProfile, setShowProfile] = useState(false);

    // New Hero Banner State
    const [floatingElements, setFloatingElements] = useState([]);
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

    useEffect(() => {
        // Generate floating particles
        const particles = Array.from({ length: 20 }, (_, i) => ({
            id: i,
            x: Math.random() * 100,
            y: Math.random() * 100,
            size: Math.random() * 3 + 1,
            duration: Math.random() * 10 + 15,
            delay: Math.random() * 5,
        }));
        setFloatingElements(particles);
    }, []);

    const handleMouseMove = (e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        setMousePos({
            x: ((e.clientX - rect.left) / rect.width - 0.5) * 20,
            y: ((e.clientY - rect.top) / rect.height - 0.5) * 20,
        });
    };
    const [anomalyData, setAnomalyData] = useState([]);
    const [uploadedVideos, setUploadedVideos] = useState([]);
    const [alertSettings, setAlertSettings] = useState({
        emailAlerts: true,
        soundAlerts: true,
        pushNotifications: false,
        threshold: 0.7,
        cooldown: 30
    });
    const wsRef = useRef(null);
    const maxDataPoints = 30;

    // Profile data for security officer (will be populated from sign up)
    const userProfile = {
        name: 'Adarsh Kumar',
        role: 'Security Administrator',
        email: 'adarsh@alertrix.com',
        phone: '+91 98765 43210',
        department: 'Security Operations',
        shift: '08:00 - 20:00'
    };

    // Camera feed data (editable)
    const [cameras, setCameras] = useState([
        { id: 1, name: 'Camera 1', location: 'Entrance', status: 'active', score: 12, visible: true },
        { id: 2, name: 'Camera 2', location: 'Parking', status: 'active', score: 8, visible: true },
        { id: 3, name: 'Camera 3', location: 'Hallway', status: 'offline', score: 0, visible: true },
        { id: 4, name: 'Camera 4', location: 'Exit', status: 'active', score: 15, visible: true },
    ]);
    const [showCameraManager, setShowCameraManager] = useState(false);
    const [editingCameraId, setEditingCameraId] = useState(null);

    // Personnel on duty (editable)
    const [personnel, setPersonnel] = useState([
        { id: 1, name: 'Rajesh Kumar', phone: '+91 98765 11111', age: 35 },
        { id: 2, name: 'Amit Singh', phone: '+91 98765 22222', age: 28 },
        { id: 3, name: 'Priya Sharma', phone: '+91 98765 33333', age: 32 },
    ]);
    const [showPersonnelManager, setShowPersonnelManager] = useState(false);
    const [editingPersonId, setEditingPersonId] = useState(null);
    const [newPerson, setNewPerson] = useState({ name: '', phone: '', age: '' });

    // WebSocket connection
    useEffect(() => {
        const connectWebSocket = () => {
            wsRef.current = new WebSocket('ws://localhost:8000/ws/stream');

            wsRef.current.onopen = () => {
                setIsConnected(true);
            };

            wsRef.current.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const score = data.anomaly_score;
                setCurrentScore(Math.round(score * 100));

                const newPoint = {
                    time: new Date().toLocaleTimeString('en-US', {
                        hour12: false,
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    }),
                    score: score
                };

                setAnomalyData(prev => {
                    const updated = [...prev, newPoint];
                    return updated.slice(-maxDataPoints);
                });

                if (score > 0.7 && !alertsMuted) {
                    setAlertCount(prev => prev + 1);
                }
            };

            wsRef.current.onclose = () => {
                setIsConnected(false);
                setTimeout(connectWebSocket, 3000);
            };

            wsRef.current.onerror = () => {
                setIsConnected(false);
            };
        };

        connectWebSocket();
        return () => wsRef.current?.close();
    }, [alertsMuted]);

    // Handle file upload
    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:8000/upload', {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            setUploadedVideos(prev => [...prev, {
                id: Date.now(),
                name: file.name,
                size: (file.size / 1024 / 1024).toFixed(2) + ' MB',
                status: 'uploaded',
                uploadTime: new Date().toLocaleString()
            }]);
        } catch (error) {
            console.error('Upload error:', error);
        }
    };

    const tabs = [
        { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { id: 'video', label: 'Video Analysis', icon: Upload },
        { id: 'live', label: 'Live AI Monitoring', icon: Radio },
        { id: 'alerts', label: 'Alert Settings', icon: Bell },
    ];

    // Render Dashboard Tab
    const renderDashboard = () => (
        <>
            {/* Stats Cards */}
            <div className="stats-grid">
                <div className="stat-card clickable" onClick={() => setShowCameraManager(true)}>
                    <div className="stat-icon purple"><Camera size={24} /></div>
                    <div className="stat-content">
                        <h3>Connected Cameras</h3>
                        <div className="value">{cameras.filter(c => c.visible).length}</div>
                        <div className="sub-text">{cameras.length} Total • Click to manage</div>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon orange"><AlertTriangle size={24} /></div>
                    <div className="stat-content">
                        <h3>Anomalies Detected</h3>
                        <div className="value">{alertCount}</div>
                        <div className="sub-text warning">Last 24 hours</div>
                    </div>
                </div>
                <div className="stat-card clickable" onClick={() => setShowPersonnelManager(true)}>
                    <div className="stat-icon blue"><Users size={24} /></div>
                    <div className="stat-content">
                        <h3>Personnel</h3>
                        <div className="value">{personnel.length}</div>
                        <div className="sub-text">On duty • Click to manage</div>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon teal"><Activity size={24} /></div>
                    <div className="stat-content">
                        <h3>AI Model Status</h3>
                        <div className="value">98%</div>
                        <div className="sub-text">Optimal</div>
                    </div>
                </div>
            </div>

            {/* AI Engine Banner */}
            <div className="ai-banner">
                <div className="ai-banner-icon">
                    <div className="scanning-camera">
                        <Camera size={40} />
                        <div className="scan-line"></div>
                    </div>
                </div>
                <div className="ai-banner-content">
                    <h2>Transformer-Based AI Detection Engine</h2>
                    <p>Our advanced spatiotemporal transformer model analyzes video feeds in real-time, detecting anomalies with industry-leading accuracy.</p>
                </div>
            </div>

            {/* Camera Feeds - Only show visible cameras */}
            <section className="camera-section">
                <h2>Live AI-Monitored Camera Feeds</h2>
                <div className="camera-grid">
                    {cameras.filter(c => c.visible).map((camera) => (
                        <div key={camera.id} className="camera-card">
                            <span className={`camera-badge ${camera.status}`}>
                                {camera.status === 'active' ? 'AI ACTIVE' : 'OFFLINE'}
                            </span>
                            {camera.status === 'active' && (
                                <span className="score-badge">Score: {camera.score}%</span>
                            )}
                            <div className="camera-placeholder"><Camera /></div>
                            <div className="camera-label">
                                <h4>{camera.name}</h4>
                                <p>{camera.location}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Camera Manager Modal */}
            {showCameraManager && (
                <div className="modal-overlay" onClick={() => setShowCameraManager(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Manage Cameras</h3>
                            <button className="modal-close" onClick={() => setShowCameraManager(false)}>×</button>
                        </div>
                        <div className="modal-body">
                            {cameras.map(camera => (
                                <div key={camera.id} className="manager-item">
                                    <button
                                        className={`visibility-btn ${camera.visible ? 'visible' : ''}`}
                                        onClick={() => setCameras(cameras.map(c =>
                                            c.id === camera.id ? { ...c, visible: !c.visible } : c
                                        ))}
                                        title={camera.visible ? 'Hide from feed' : 'Show in feed'}
                                    >
                                        {camera.visible ? <Eye size={18} /> : <EyeOff size={18} />}
                                    </button>
                                    <div className="manager-item-content">
                                        {editingCameraId === camera.id ? (
                                            <>
                                                <input
                                                    type="text"
                                                    value={camera.name}
                                                    onChange={(e) => setCameras(cameras.map(c =>
                                                        c.id === camera.id ? { ...c, name: e.target.value } : c
                                                    ))}
                                                    className="manager-input"
                                                    placeholder="Camera name"
                                                />
                                                <input
                                                    type="text"
                                                    value={camera.location}
                                                    onChange={(e) => setCameras(cameras.map(c =>
                                                        c.id === camera.id ? { ...c, location: e.target.value } : c
                                                    ))}
                                                    className="manager-input"
                                                    placeholder="Location (e.g., Parking)"
                                                />
                                            </>
                                        ) : (
                                            <>
                                                <span className="manager-name">{camera.name}</span>
                                                <span className="manager-sub">{camera.location}</span>
                                            </>
                                        )}
                                    </div>
                                    <button
                                        className="edit-btn"
                                        onClick={() => setEditingCameraId(editingCameraId === camera.id ? null : camera.id)}
                                    >
                                        {editingCameraId === camera.id ? <Check size={16} /> : <Edit2 size={16} />}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Personnel Manager Modal */}
            {showPersonnelManager && (
                <div className="modal-overlay" onClick={() => setShowPersonnelManager(false)}>
                    <div className="modal" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>Personnel On Duty</h3>
                            <button className="modal-close" onClick={() => setShowPersonnelManager(false)}>×</button>
                        </div>
                        <div className="modal-body">
                            {personnel.map(person => (
                                <div key={person.id} className="manager-item">
                                    <div className="person-avatar">{person.name.charAt(0)}</div>
                                    <div className="manager-item-content">
                                        {editingPersonId === person.id ? (
                                            <>
                                                <input
                                                    type="text"
                                                    value={person.name}
                                                    onChange={(e) => setPersonnel(personnel.map(p =>
                                                        p.id === person.id ? { ...p, name: e.target.value } : p
                                                    ))}
                                                    className="manager-input"
                                                    placeholder="Name"
                                                />
                                                <input
                                                    type="tel"
                                                    value={person.phone}
                                                    onChange={(e) => setPersonnel(personnel.map(p =>
                                                        p.id === person.id ? { ...p, phone: e.target.value } : p
                                                    ))}
                                                    className="manager-input"
                                                    placeholder="Phone"
                                                />
                                                <input
                                                    type="number"
                                                    value={person.age}
                                                    onChange={(e) => setPersonnel(personnel.map(p =>
                                                        p.id === person.id ? { ...p, age: e.target.value } : p
                                                    ))}
                                                    className="manager-input small"
                                                    placeholder="Age"
                                                />
                                            </>
                                        ) : (
                                            <>
                                                <span className="manager-name">{person.name}</span>
                                                <span className="manager-sub">{person.phone} • Age: {person.age}</span>
                                            </>
                                        )}
                                    </div>
                                    <button
                                        className="edit-btn"
                                        onClick={() => setEditingPersonId(editingPersonId === person.id ? null : person.id)}
                                    >
                                        {editingPersonId === person.id ? <Check size={16} /> : <Edit2 size={16} />}
                                    </button>
                                    <button
                                        className="delete-btn"
                                        onClick={() => setPersonnel(personnel.filter(p => p.id !== person.id))}
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            ))}

                            {/* Add New Personnel */}
                            <div className="add-person-form">
                                <h4>Add New Personnel</h4>
                                <div className="add-form-row">
                                    <input
                                        type="text"
                                        value={newPerson.name}
                                        onChange={(e) => setNewPerson({ ...newPerson, name: e.target.value })}
                                        className="manager-input"
                                        placeholder="Name"
                                    />
                                    <input
                                        type="tel"
                                        value={newPerson.phone}
                                        onChange={(e) => setNewPerson({ ...newPerson, phone: e.target.value })}
                                        className="manager-input"
                                        placeholder="Phone"
                                    />
                                    <input
                                        type="number"
                                        value={newPerson.age}
                                        onChange={(e) => setNewPerson({ ...newPerson, age: e.target.value })}
                                        className="manager-input small"
                                        placeholder="Age"
                                    />
                                    <button
                                        className="add-btn"
                                        onClick={() => {
                                            if (newPerson.name && newPerson.phone && newPerson.age) {
                                                setPersonnel([...personnel, { id: Date.now(), ...newPerson }]);
                                                setNewPerson({ name: '', phone: '', age: '' });
                                            }
                                        }}
                                    >
                                        <Plus size={18} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );

    // Render Video Analysis Tab
    const renderVideoAnalysis = () => (
        <div className="page-content">
            <div className="page-header">
                <h1>Video Analysis</h1>
                <p>Upload and analyze video files for anomaly detection</p>
            </div>

            {/* Upload Area */}
            <div className="upload-section">
                <label className="upload-dropzone">
                    <input type="file" accept="video/*" onChange={handleFileUpload} hidden />
                    <Upload size={48} />
                    <h3>Drop your video file here</h3>
                    <p>or click to browse</p>
                    <span className="file-types">Supports MP4, AVI, MOV, MKV, WebM</span>
                </label>
            </div>

            {/* Uploaded Videos List */}
            {uploadedVideos.length > 0 && (
                <div className="videos-list">
                    <h3>Uploaded Videos</h3>
                    {uploadedVideos.map(video => (
                        <div key={video.id} className="video-item">
                            <FileVideo size={24} />
                            <div className="video-info">
                                <h4>{video.name}</h4>
                                <p>{video.size} • {video.uploadTime}</p>
                            </div>
                            <div className="video-actions">
                                <button className="btn-icon" title="Analyze"><Play size={18} /></button>
                                <button className="btn-icon danger" title="Delete"><Trash2 size={18} /></button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );

    // Render Live AI Monitoring Tab
    const renderLiveMonitoring = () => (
        <div className="page-content">
            <div className="page-header">
                <h1>Live AI Monitoring</h1>
                <p>Real-time anomaly detection and scoring</p>
            </div>

            {/* Connection Status */}
            <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                <div className="status-indicator"></div>
                <span>{isConnected ? 'Connected to AI Model' : 'Disconnected - Reconnecting...'}</span>
            </div>

            {/* Current Score Display */}
            <div className="score-display">
                <div className="score-circle" style={{
                    background: `conic-gradient(${currentScore > 70 ? '#ef4444' : currentScore > 30 ? '#f97316' : '#14b8a6'} ${currentScore * 3.6}deg, #1e293b 0deg)`
                }}>
                    <div className="score-inner">
                        <span className="score-value">{currentScore}%</span>
                        <span className="score-label">Anomaly Score</span>
                    </div>
                </div>
            </div>

            {/* Real-time Chart */}
            <div className="chart-section">
                <h3>Real-time Anomaly Trend</h3>
                <div className="chart-container">
                    <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={anomalyData}>
                            <defs>
                                <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                            <YAxis domain={[0, 1]} stroke="#64748b" fontSize={10} />
                            <Tooltip
                                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                                labelStyle={{ color: '#94a3b8' }}
                            />
                            <Area type="monotone" dataKey="score" stroke="#14b8a6" strokeWidth={2} fill="url(#colorScore)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );

    // Render Alert Settings Tab
    const renderAlertSettings = () => (
        <div className="page-content">
            <div className="page-header">
                <h1>Alert Settings</h1>
                <p>Configure how you receive anomaly alerts</p>
            </div>

            <div className="settings-grid">
                {/* Notification Preferences */}
                <div className="settings-card">
                    <h3>Notification Preferences</h3>

                    <div className="setting-item">
                        <div className="setting-info">
                            <Mail size={20} />
                            <div>
                                <h4>Email Alerts</h4>
                                <p>Receive alerts via email</p>
                            </div>
                        </div>
                        <label className="toggle">
                            <input
                                type="checkbox"
                                checked={alertSettings.emailAlerts}
                                onChange={(e) => setAlertSettings({ ...alertSettings, emailAlerts: e.target.checked })}
                            />
                            <span className="toggle-slider"></span>
                        </label>
                    </div>

                    <div className="setting-item">
                        <div className="setting-info">
                            <Volume2 size={20} />
                            <div>
                                <h4>Sound Alerts</h4>
                                <p>Play sound on detection</p>
                            </div>
                        </div>
                        <label className="toggle">
                            <input
                                type="checkbox"
                                checked={alertSettings.soundAlerts}
                                onChange={(e) => setAlertSettings({ ...alertSettings, soundAlerts: e.target.checked })}
                            />
                            <span className="toggle-slider"></span>
                        </label>
                    </div>

                    <div className="setting-item">
                        <div className="setting-info">
                            <Bell size={20} />
                            <div>
                                <h4>Push Notifications</h4>
                                <p>Browser push notifications</p>
                            </div>
                        </div>
                        <label className="toggle">
                            <input
                                type="checkbox"
                                checked={alertSettings.pushNotifications}
                                onChange={(e) => setAlertSettings({ ...alertSettings, pushNotifications: e.target.checked })}
                            />
                            <span className="toggle-slider"></span>
                        </label>
                    </div>
                </div>

                {/* Detection Settings */}
                <div className="settings-card">
                    <h3>Detection Settings</h3>

                    <div className="setting-item column">
                        <div className="setting-info">
                            <AlertTriangle size={20} />
                            <div>
                                <h4>Alert Threshold</h4>
                                <p>Minimum score to trigger alert: {(alertSettings.threshold * 100).toFixed(0)}%</p>
                            </div>
                        </div>
                        <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.05"
                            value={alertSettings.threshold}
                            onChange={(e) => setAlertSettings({ ...alertSettings, threshold: parseFloat(e.target.value) })}
                            className="range-slider"
                        />
                    </div>

                    <div className="setting-item column">
                        <div className="setting-info">
                            <Clock size={20} />
                            <div>
                                <h4>Alert Cooldown</h4>
                                <p>Wait {alertSettings.cooldown} seconds between alerts</p>
                            </div>
                        </div>
                        <input
                            type="range"
                            min="10"
                            max="120"
                            step="10"
                            value={alertSettings.cooldown}
                            onChange={(e) => setAlertSettings({ ...alertSettings, cooldown: parseInt(e.target.value) })}
                            className="range-slider"
                        />
                    </div>
                </div>
            </div>

            <button className="btn-primary">
                <Save size={18} />
                Save Settings
            </button>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-100">
            {/* Animated Hero Banner Section */}
            <div className="w-full bg-slate-900 border-b border-teal-900">
                <div
                    className="relative w-full h-[240px] overflow-hidden"
                    onMouseMove={handleMouseMove}
                    style={{
                        background: 'linear-gradient(135deg, #0f172a 0%, #164e63 50%, #0f172a 100%)',
                    }}
                >
                    {/* Animated Grid Background */}
                    <div className="absolute inset-0 opacity-20 pointer-events-none">
                        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                            <defs>
                                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#14b8a6" strokeWidth="0.5" />
                                </pattern>
                            </defs>
                            <rect width="100%" height="100%" fill="url(#grid)" />
                        </svg>
                    </div>

                    {/* Circuit Lines */}
                    <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ filter: 'blur(0.5px)' }}>
                        <line x1="0" y1="30%" x2="30%" y2="30%" stroke="#14b8a6" strokeWidth="1" opacity="0.6">
                            <animate attributeName="x2" values="0%;40%;0%" dur="8s" repeatCount="indefinite" />
                        </line>
                        <line x1="100%" y1="60%" x2="70%" y2="60%" stroke="#14b8a6" strokeWidth="1" opacity="0.6">
                            <animate attributeName="x2" values="100%;60%;100%" dur="10s" repeatCount="indefinite" />
                        </line>
                        <line x1="20%" y1="0" x2="20%" y2="40%" stroke="#0891b2" strokeWidth="1" opacity="0.4">
                            <animate attributeName="y2" values="0%;50%;0%" dur="12s" repeatCount="indefinite" />
                        </line>
                        <line x1="80%" y1="100%" x2="80%" y2="60%" stroke="#0891b2" strokeWidth="1" opacity="0.4">
                            <animate attributeName="y2" values="100%;50%;100%" dur="9s" repeatCount="indefinite" />
                        </line>
                    </svg>

                    {/* Floating Particles */}
                    {floatingElements.map((particle) => (
                        <div
                            key={particle.id}
                            className="absolute rounded-full bg-teal-400 pointer-events-none"
                            style={{
                                left: `${particle.x}%`,
                                top: `${particle.y}%`,
                                width: `${particle.size}px`,
                                height: `${particle.size}px`,
                                animation: `float ${particle.duration}s ease-in-out infinite`,
                                animationDelay: `${particle.delay}s`,
                                opacity: 0.4,
                            }}
                        />
                    ))}

                    {/* CENTRAL CONTAINER FOR TITLE AND NAV */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10 top-4">

                        {/* LEFT NAV GROUP */}
                        <div className="flex gap-4 pr-12 pointer-events-auto items-center">
                            {tabs.slice(0, 2).map((tab) => (
                                <button
                                    key={tab.id}
                                    className={`banner-nav-tab ${activeTab === tab.id ? 'active' : ''}`}
                                    onClick={() => setActiveTab(tab.id)}
                                >
                                    <tab.icon size={18} />
                                    <span>{tab.label}</span>
                                </button>
                            ))}
                        </div>

                        {/* CENTER BRANDING */}
                        <div
                            className="relative flex flex-col items-center justify-center mx-4"
                            style={{
                                transform: `translate(${mousePos.x * 0.2}px, ${mousePos.y * 0.2}px)`,
                            }}
                        >
                            {/* Shield Logo */}
                            <div className="relative mb-2">
                                <svg width="60" height="60" viewBox="0 0 100 100" className="drop-shadow-xl">
                                    <defs>
                                        <linearGradient id="shieldGradientSmall" x1="0%" y1="0%" x2="100%" y2="100%">
                                            <stop offset="0%" stopColor="#14b8a6" />
                                            <stop offset="100%" stopColor="#06b6d4" />
                                        </linearGradient>
                                    </defs>
                                    <path
                                        d="M 50 10 L 80 25 L 80 55 Q 80 80 50 90 Q 20 80 20 55 L 20 25 Z"
                                        fill="url(#shieldGradientSmall)"
                                        opacity="0.9"
                                    />
                                    <path d="M 50 30 L 60 36 L 60 48 L 50 54 L 40 48 L 40 36 Z" fill="none" stroke="white" strokeWidth="2" opacity="0.9" />
                                </svg>
                            </div>

                            <h1
                                className="text-5xl font-bold text-white tracking-wider banner-title-animated"
                                style={{
                                    textShadow: '0 0 20px rgba(20, 184, 166, 0.6)',
                                    letterSpacing: '0.1em',
                                }}
                            >
                                Alertrix AI
                            </h1>
                            <p className="text-teal-300 text-sm mt-1 tracking-widest uppercase opacity-80">
                                Your AI guardian angel
                            </p>
                        </div>

                        {/* RIGHT NAV GROUP */}
                        <div className="flex gap-4 pl-12 pointer-events-auto items-center">
                            {tabs.slice(2, 4).map((tab) => (
                                <button
                                    key={tab.id}
                                    className={`banner-nav-tab ${activeTab === tab.id ? 'active' : ''}`}
                                    onClick={() => setActiveTab(tab.id)}
                                >
                                    <tab.icon size={18} />
                                    <span>{tab.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Glowing Orbs */}
                    <div className="absolute top-10 left-20 w-32 h-32 bg-teal-500 rounded-full opacity-10 blur-3xl animate-pulse pointer-events-none" />
                    <div className="absolute bottom-10 right-20 w-40 h-40 bg-cyan-500 rounded-full opacity-10 blur-3xl animate-pulse pointer-events-none" style={{ animationDelay: '1s' }} />

                    {/* Data Streams (Repositioned) */}
                    <div className="absolute top-8 left-6 text-teal-400 text-[10px] font-mono opacity-30 pointer-events-none">
                        <div className="mb-1">SYS: ACTIVE</div>
                        <div className="mb-1">SEC: HIGH</div>
                        <div>NET: ON</div>
                    </div>
                    <div className="absolute bottom-4 right-6 text-teal-400 text-[10px] font-mono opacity-30 text-right pointer-events-none">
                        <div className="mb-1">AI: 98%</div>
                        <div>UP: 99.9%</div>
                    </div>

                    {/* Floating Hexagons */}
                    <div className="absolute top-1/4 right-1/4 opacity-20 pointer-events-none">
                        <svg width="60" height="60" viewBox="0 0 60 60" className="animate-float">
                            <polygon points="30,5 50,17.5 50,42.5 30,55 10,42.5 10,17.5" fill="none" stroke="#14b8a6" strokeWidth="1" />
                        </svg>
                    </div>
                    <div className="absolute bottom-1/4 left-1/4 opacity-20 pointer-events-none">
                        <svg width="40" height="40" viewBox="0 0 40 40" className="animate-float" style={{ animationDelay: '2s' }}>
                            <polygon points="20,3 33,11 33,27 20,35 7,27 7,11" fill="none" stroke="#06b6d4" strokeWidth="1" />
                        </svg>
                    </div>

                    {/* Banner Controls (Absolute Positioned) */}
                    <div className="absolute top-4 right-4 flex items-center gap-3 z-20 pointer-events-auto">
                        <div className="glass-badge">
                            <Cpu size={14} />
                            <span>AI Active</span>
                            <div className="pulse-dot"></div>
                        </div>

                        <button
                            className={`glass-btn ${alertsMuted ? 'muted' : ''}`}
                            onClick={(e) => { e.stopPropagation(); setAlertsMuted(!alertsMuted); }}
                            title={alertsMuted ? 'Unmute Alerts' : 'Mute Alerts'}
                        >
                            {alertsMuted ? <BellOff size={18} /> : <Bell size={18} />}
                            {!alertsMuted && alertCount > 0 && (
                                <span className="alert-count">{alertCount > 99 ? '99+' : alertCount}</span>
                            )}
                        </button>

                        <div className="glass-divider"></div>

                        <button
                            className="glass-btn profile-trigger"
                            onClick={(e) => { e.stopPropagation(); setShowProfile(!showProfile); }}
                        >
                            <User size={18} />
                        </button>
                    </div>


                </div>

                {/* Profile Dropdown (Moved outside overflow-hidden container) */}
                {showProfile && (
                    <div className="absolute top-16 right-4 z-50">
                        <div className="profile-dropdown banner-dropdown">
                            <div className="profile-header">
                                <div className="profile-avatar large">
                                    <User size={28} />
                                </div>
                                <div className="profile-info">
                                    <h4>{userProfile.name}</h4>
                                    <span className="role-badge">{userProfile.role}</span>
                                </div>
                            </div>

                            <div className="profile-details">
                                <div className="detail-item">
                                    <Mail size={16} />
                                    <span>{userProfile.email}</span>
                                </div>
                                <div className="detail-item">
                                    <Phone size={16} />
                                    <span>{userProfile.phone}</span>
                                </div>
                                <div className="detail-item">
                                    <Shield size={16} />
                                    <span>{userProfile.department}</span>
                                </div>
                                <div className="detail-item">
                                    <Clock size={16} />
                                    <span>Shift: {userProfile.shift}</span>
                                </div>
                            </div>

                            <div className="profile-footer">
                                <button className="btn-secondary">
                                    <Settings size={16} />
                                    Settings
                                </button>
                                <button className="btn-logout">
                                    <LogOut size={16} />
                                    Sign Out
                                </button>
                            </div>
                        </div>
                    </div>
                )}


            </div>

            {/* Main Content */}
            <main className="main-content">
                {activeTab === 'dashboard' && renderDashboard()}
                {activeTab === 'video' && renderVideoAnalysis()}
                {activeTab === 'live' && renderLiveMonitoring()}
                {activeTab === 'alerts' && renderAlertSettings()}
            </main>
        </div>
    );
};

export default Dashboard;
