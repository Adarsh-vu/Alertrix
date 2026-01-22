import React, { useState, useEffect, useRef } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import {
    Camera, Upload, Activity, AlertTriangle, Bell, BellOff, Settings, Users, Cpu,
    LayoutDashboard, Radio, Brain, User, LogOut, Shield, Mail, Phone, Clock,
    FileVideo, Play, Trash2, Save, Plus, Edit2, Check, Eye, EyeOff, Volume2
} from 'lucide-react';
import { PersonStanding } from 'lucide-react';
import './Auth.css';

const Dashboard = ({ user, onLogout }) => {
    const [activeTab, setActiveTab] = useState('dashboard');
    const [isConnected, setIsConnected] = useState(false);
    const [currentScore, setCurrentScore] = useState(0);
    const [alertCount, setAlertCount] = useState(3);
    const [alertsMuted, setAlertsMuted] = useState(false);
    const [showProfile, setShowProfile] = useState(false);
    const [floatingElements, setFloatingElements] = useState([]);
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

    useEffect(() => {
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
    // Forensic Analysis State
    const [previewUrl, setPreviewUrl] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [alertSettings, setAlertSettings] = useState({
        emailAlerts: true,
        soundAlerts: true,
        pushNotifications: false,
        threshold: 0.40,
        cooldown: 30
    });
    const wsRef = useRef(null);
    const maxDataPoints = 30;

    // Profile data - use logged in user data
    const userProfile = {
        name: user?.username || 'Guest',
        role: user?.role === 'admin' ? 'Administrator' : 'Security Officer',
        email: user?.email || 'user@alertrix.com',
        phone: user?.phone || 'Not set',
        department: user?.department || 'Security Operations',
        shift: user?.shift || '08:00 - 20:00'
    };

    const isAdmin = user?.role === 'admin';

    // Camera feed data
    const [cameras, setCameras] = useState([
        { id: 1, name: 'Camera 1', location: 'Entrance', status: 'active', score: 12, visible: true },
        { id: 2, name: 'Camera 2', location: 'Parking', status: 'active', score: 8, visible: true },
        { id: 3, name: 'Camera 3', location: 'Hallway', status: 'offline', score: 0, visible: true },
        { id: 4, name: 'Camera 4', location: 'Exit', status: 'active', score: 15, visible: true },
    ]);
    const [showCameraManager, setShowCameraManager] = useState(false);
    const [editingCameraId, setEditingCameraId] = useState(null);

    // Personnel on duty
    const [personnel, setPersonnel] = useState([
        { id: 1, name: 'Rajesh Kumar', phone: '+91 98765 11111', age: 35 },
        { id: 2, name: 'Amit Singh', phone: '+91 98765 22222', age: 28 },
        { id: 3, name: 'Priya Sharma', phone: '+91 98765 33333', age: 32 },
    ]);
    const [showPersonnelManager, setShowPersonnelManager] = useState(false);
    const [editingPersonId, setEditingPersonId] = useState(null);
    const [newPerson, setNewPerson] = useState({ name: '', phone: '', age: '' });

    // WebSocket connection (PHASE 3)
    /*
    useEffect(() => {
        const connectWebSocket = () => {
            wsRef.current = new WebSocket('ws://localhost:5000/ws/stream');
            wsRef.current.onopen = () => setIsConnected(true);
            wsRef.current.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const score = data.anomaly_score;
                setCurrentScore(Math.round(score * 100));
                // ... logic ...
            };
            wsRef.current.onclose = () => setIsConnected(false);
        };
        // connectWebSocket();
        // return () => wsRef.current?.close();
    }, []);
    */

    // Handle file upload
    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        // 1. Immediate Preview
        const objectUrl = URL.createObjectURL(file);
        setPreviewUrl(objectUrl);
        setAnalysisResult(null);
        setIsAnalyzing(true);

        const formData = new FormData();
        formData.append('video', file);

        const startTime = performance.now();

        try {
            // 5-minute timeout for long analysis
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 300000);

            const response = await fetch('http://localhost:5000/analyze', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Backend error:', errorText);
                throw new Error(`Server Error: ${response.status}`);
            }

            const data = await response.json();
            console.log('Analysis result:', data);
            const endTime = performance.now();
            const duration = ((endTime - startTime) / 1000).toFixed(2);

            // 2. Store Result
            setAnalysisResult({ ...data, processingTime: duration });
            setIsAnalyzing(false);

            // Keep existing log
            setUploadedVideos(prev => [...prev, {
                id: Date.now(),
                name: file.name,
                size: (file.size / 1024 / 1024).toFixed(2) + ' MB',
                status: data.status === 'ANOMALY DETECTED' ? '⚠️ ANOMALY' : '✅ CLEAR',
                uploadTime: new Date().toLocaleString(),
                details: data
            }]);

        } catch (error) {
            console.error('Upload error:', error);
            setIsAnalyzing(false);
            if (error.name === 'AbortError') {
                alert("Analysis timed out. Try a shorter video or check backend.");
            } else {
                alert(`Analysis Failed: ${error.message}`);
            }
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
                                    >
                                        {camera.visible ? <Eye size={18} /> : <EyeOff size={18} />}
                                    </button>
                                    <div className="manager-item-content">
                                        {editingCameraId === camera.id ? (
                                            <>
                                                <input type="text" value={camera.name} onChange={(e) => setCameras(cameras.map(c => c.id === camera.id ? { ...c, name: e.target.value } : c))} className="manager-input" placeholder="Camera name" />
                                                <input type="text" value={camera.location} onChange={(e) => setCameras(cameras.map(c => c.id === camera.id ? { ...c, location: e.target.value } : c))} className="manager-input" placeholder="Location" />
                                            </>
                                        ) : (
                                            <>
                                                <span className="manager-name">{camera.name}</span>
                                                <span className="manager-sub">{camera.location}</span>
                                            </>
                                        )}
                                    </div>
                                    <button className="edit-btn" onClick={() => setEditingCameraId(editingCameraId === camera.id ? null : camera.id)}>
                                        {editingCameraId === camera.id ? <Check size={16} /> : <Edit2 size={16} />}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

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
                                                <input type="text" value={person.name} onChange={(e) => setPersonnel(personnel.map(p => p.id === person.id ? { ...p, name: e.target.value } : p))} className="manager-input" />
                                                <input type="tel" value={person.phone} onChange={(e) => setPersonnel(personnel.map(p => p.id === person.id ? { ...p, phone: e.target.value } : p))} className="manager-input" />
                                                <input type="number" value={person.age} onChange={(e) => setPersonnel(personnel.map(p => p.id === person.id ? { ...p, age: e.target.value } : p))} className="manager-input small" />
                                            </>
                                        ) : (
                                            <>
                                                <span className="manager-name">{person.name}</span>
                                                <span className="manager-sub">{person.phone} • Age: {person.age}</span>
                                            </>
                                        )}
                                    </div>
                                    <button className="edit-btn" onClick={() => setEditingPersonId(editingPersonId === person.id ? null : person.id)}>
                                        {editingPersonId === person.id ? <Check size={16} /> : <Edit2 size={16} />}
                                    </button>
                                    <button className="delete-btn" onClick={() => setPersonnel(personnel.filter(p => p.id !== person.id))}><Trash2 size={16} /></button>
                                </div>
                            ))}
                            <div className="add-person-form">
                                <h4>Add New Personnel</h4>
                                <div className="add-form-row">
                                    <input type="text" value={newPerson.name} onChange={(e) => setNewPerson({ ...newPerson, name: e.target.value })} className="manager-input" placeholder="Name" />
                                    <input type="tel" value={newPerson.phone} onChange={(e) => setNewPerson({ ...newPerson, phone: e.target.value })} className="manager-input" placeholder="Phone" />
                                    <input type="number" value={newPerson.age} onChange={(e) => setNewPerson({ ...newPerson, age: e.target.value })} className="manager-input small" placeholder="Age" />
                                    <button className="add-btn" onClick={() => { if (newPerson.name && newPerson.phone) { setPersonnel([...personnel, { id: Date.now(), ...newPerson }]); setNewPerson({ name: '', phone: '', age: '' }); } }}><Plus size={18} /></button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );

    const renderVideoAnalysis = () => {
        // Calculate Summary Metrics
        const details = analysisResult?.details || [];
        const maxScore = details.length > 0 ? Math.max(...details.map(d => d.score)) : 0;

        // Calculate Average Threat Score
        const anomalousFrames = details.filter(d => d.score > alertSettings.threshold);
        let avgScore = 0;

        if (anomalousFrames.length > 0) {
            avgScore = anomalousFrames.reduce((a, b) => a + b.score, 0) / anomalousFrames.length;
        } else if (details.length > 0) {
            const sorted = [...details].sort((a, b) => b.score - a.score);
            const top10Percent = sorted.slice(0, Math.ceil(details.length * 0.1));
            avgScore = top10Percent.reduce((a, b) => a + b.score, 0) / top10Percent.length;
        }

        const anomalyCount = details.filter(d => d.score > alertSettings.threshold).length;
        const confidenceLevel = maxScore > 0.8 ? 'Very High' : maxScore > 0.6 ? 'High' : 'Moderate';
        const chartData = details.map((d) => ({
            time: d.time, // Use raw seconds for linear axis
            score: (d.score * 100).toFixed(1),
            threshold: alertSettings.threshold * 100
        }));

        const formatTime = (seconds) => {
            if (!seconds && seconds !== 0) return '';
            const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
            const secs = Math.floor(seconds % 60).toString().padStart(2, '0');
            return `${mins}:${secs}`;
        };

        return (
            <div className="page-content">
                <div className="flex justify-between items-end mb-6">
                    <div>
                        <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-cyan-300">Forensic Analysis Hub</h1>
                        <p className="text-slate-400 mt-1">Transformer based spatiotemporal anomaly detection</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                    {/* LEFT COLUMN: Player & Input */}
                    <div className="lg:col-span-2">
                        <div className="relative bg-slate-900 rounded-2xl overflow-hidden border border-slate-700 shadow-2xl group h-full">
                            {!previewUrl ? (
                                <label className="flex flex-col items-center justify-center h-[400px] cursor-pointer bg-slate-800/20 hover:bg-slate-800/40 transition-all duration-300 border-2 border-dashed border-slate-600 hover:border-teal-500/50 group-hover:shadow-[0_0_30px_rgba(20,184,166,0.1)]">
                                    <input type="file" accept="video/*" onChange={handleFileUpload} hidden />
                                    <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                                        <Upload size={32} className="text-teal-400" />
                                    </div>
                                    <h3 className="text-2xl font-bold text-white mb-2">Upload Evidence</h3>
                                    <p className="text-slate-400">Drag & drop or click to browse</p>
                                    <div className="mt-6 flex gap-3">
                                        <span className="px-3 py-1 rounded-md bg-slate-800 text-xs text-slate-400 border border-slate-700">MP4</span>
                                        <span className="px-3 py-1 rounded-md bg-slate-800 text-xs text-slate-400 border border-slate-700">AVI</span>
                                        <span className="px-3 py-1 rounded-md bg-slate-800 text-xs text-slate-400 border border-slate-700">MKV</span>
                                    </div>
                                </label>
                            ) : (
                                <div className="relative w-full h-full bg-black flex flex-col justify-center">
                                    <div className="absolute top-0 left-0 right-0 z-10 p-4 bg-gradient-to-b from-black/80 to-transparent flex justify-between items-center opacity-0 group-hover:opacity-100 transition-opacity">
                                        <span className="text-xs font-mono text-teal-400 bg-teal-900/30 px-2 py-1 rounded border border-teal-500/30">SOURCE: RAW_FOOTAGE.mp4</span>
                                        <button
                                            onClick={() => { setPreviewUrl(null); setAnalysisResult(null); setIsAnalyzing(false); }}
                                            className="text-red-400 hover:text-white hover:bg-red-500/20 p-2 rounded-lg transition-colors flex items-center gap-2 text-xs"
                                        >
                                            <Trash2 size={14} /> DISCARD
                                        </button>
                                    </div>
                                    <video controls src={previewUrl} className="w-full max-h-[500px] object-contain" />

                                    {/* COMPACT LOADING STATE */}
                                    {isAnalyzing && (
                                        <div className="absolute bottom-0 left-0 right-0 h-1 bg-slate-800">
                                            <div className="h-full bg-gradient-to-r from-teal-500 via-cyan-400 to-blue-500 animate-loading-bar box-shadow-[0_0_10px_rgba(20,184,166,0.5)]"></div>
                                            <div className="absolute bottom-4 left-4 bg-black/60 backdrop-blur-md px-4 py-2 rounded-lg border border-teal-500/30 flex items-center gap-3">
                                                <div className="w-2 h-2 rounded-full bg-teal-400 animate-ping"></div>
                                                <span className="text-teal-400 text-sm font-bold tracking-wide">ANALYZING FRAMES...</span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* RIGHT COLUMN: Results Summary */}
                    <div className="flex flex-col gap-4">
                        {analysisResult ? (
                            <>
                                <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-1 border border-slate-700 shadow-xl">
                                    <div className="bg-slate-900/50 rounded-xl p-5 h-full relative overflow-hidden">
                                        <div className={`absolute top-0 right-0 p-3 opacity-20 ${analysisResult.status === 'ANOMALY DETECTED' ? 'text-red-500' : 'text-teal-500'}`}>
                                            <Shield size={80} />
                                        </div>
                                        <h4 className="text-slate-400 text-sm font-bold uppercase tracking-wider mb-1">Final Verdict</h4>
                                        <div className={`text-3xl font-black tracking-tight ${analysisResult.status === 'ANOMALY DETECTED' ? 'text-red-400' : 'text-teal-400'}`}>
                                            {analysisResult.status === 'ANOMALY DETECTED' ? 'ANOMALY DETECTED' : 'SECURE'}
                                        </div>
                                        <p className="text-slate-500 text-xs mt-2">processed in {analysisResult.processingTime || '0.00'}s</p>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    {/* Max Risk Card */}
                                    <div className={`rounded-2xl p-5 border shadow-lg relative overflow-hidden group transition-all duration-300 hover:scale-[1.02] ${maxScore > 0.8 ? 'bg-gradient-to-br from-red-950/80 to-slate-900 border-red-500/40 shadow-red-900/20' : 'bg-gradient-to-br from-slate-800 to-slate-900 border-slate-700/50'}`}>
                                        <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
                                            <AlertTriangle size={48} className={maxScore > 0.8 ? 'text-red-500' : 'text-slate-400'} />
                                        </div>
                                        <h4 className={`text-xs font-bold uppercase tracking-wider mb-3 ${maxScore > 0.8 ? 'text-red-400' : 'text-slate-400'}`}>Max Risk Level</h4>
                                        <div className="flex items-baseline gap-1">
                                            <span className={`text-4xl font-black tracking-tight ${maxScore > 0.8 ? 'text-red-500 drop-shadow-[0_0_10px_rgba(239,68,68,0.5)]' : maxScore > 0.5 ? 'text-orange-500' : 'text-teal-500'}`}>
                                                {(maxScore * 100).toFixed(0)}
                                            </span>
                                            <span className="text-sm font-bold opacity-60">%</span>
                                        </div>
                                        <div className={`mt-2 h-1 w-full rounded-full bg-slate-800 overflow-hidden`}>
                                            <div className={`h-full ${maxScore > 0.8 ? 'bg-red-500' : 'bg-teal-500'}`} style={{ width: `${maxScore * 100}%` }}></div>
                                        </div>
                                    </div>

                                    {/* Avg Score Card */}
                                    <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-5 border border-slate-700/50 shadow-lg hover:border-cyan-500/30 transition-all duration-300 hover:scale-[1.02] group relative overflow-hidden">
                                        <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                                            <Brain size={48} className="text-cyan-400" />
                                        </div>
                                        <h4 className="text-cyan-400/70 text-xs font-bold uppercase tracking-wider mb-3">Average Score</h4>
                                        <div className="flex items-baseline gap-1">
                                            <span className="text-4xl font-black tracking-tight text-white drop-shadow-[0_0_10px_rgba(34,211,238,0.3)]">{(avgScore * 100).toFixed(0)}</span>
                                            <span className="text-sm font-bold text-slate-500">%</span>
                                        </div>
                                        <div className="mt-2 text-xs text-slate-500 flex items-center gap-1">
                                            <div className="w-2 h-2 rounded-full bg-cyan-500"></div>
                                            Avg Threat Score
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-slate-900 rounded-2xl p-6 border border-slate-700 flex flex-col gap-4">
                                    <h4 className="text-slate-400 text-xs font-bold uppercase">Detection Summary</h4>
                                    <div className="flex justify-between items-center py-2 border-b border-slate-800">
                                        <span className="text-slate-300">Total Anomalies</span>
                                        <span className="font-mono font-bold text-white bg-slate-800 px-2 py-1 rounded">{anomalyCount}</span>
                                    </div>
                                    <div className="flex justify-between items-center py-2 border-b border-slate-800">
                                        <span className="text-slate-300">Duration</span>
                                        <span className="font-mono text-slate-400">{details.length} frames</span>
                                    </div>
                                    <div className="flex justify-between items-center py-2">
                                        <span className="text-slate-300">Confidence</span>
                                        <span className="font-mono text-teal-400">{confidenceLevel}</span>
                                    </div>
                                </div>
                            </>
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-500 border-2 border-dashed border-slate-800 rounded-3xl">
                                <div className="w-16 h-16 bg-slate-900 rounded-full flex items-center justify-center mb-4">
                                    <Activity size={24} className="opacity-50" />
                                </div>
                                <p className="text-sm">Upload video to generate forensic insights</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* BOTTOM ROW: Anomaly Trend Graph */}
                {analysisResult && (
                    <div className="w-full bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-700/50 p-6 shadow-2xl relative overflow-hidden group">
                        {/* Cyber Grid Background */}
                        <div className="absolute inset-0 opacity-10 pointer-events-none"
                            style={{ backgroundImage: 'linear-gradient(#0f172a 1px, transparent 1px), linear-gradient(90deg, #0f172a 1px, transparent 1px)', backgroundSize: '20px 20px' }}>
                        </div>
                        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent opacity-80 pointer-events-none"></div>

                        <div className="flex justify-between items-center mb-6 relative z-10">
                            <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                                <Activity size={18} className="text-cyan-400" /> Anomaly Timeline
                            </h3>
                            <div className="flex gap-2">
                                <span className="text-[10px] font-mono text-cyan-500 bg-cyan-950/30 px-2 py-1 rounded border border-cyan-500/20">LIVE_FEED_01</span>
                            </div>
                        </div>

                        <div className="h-[300px] w-full relative z-10">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id="colorTrend" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.8} />
                                            <stop offset="95%" stopColor="#14b8a6" stopOpacity={0.1} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} opacity={0.4} />
                                    <XAxis
                                        dataKey="time"
                                        type="number"
                                        domain={[0, 'auto']}
                                        tickCount={8}
                                        tickFormatter={formatTime}
                                        stroke="#94a3b8"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        domain={[0, 100]}
                                        stroke="#94a3b8"
                                        fontSize={12}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(value) => `${value}%`}
                                    />
                                    <Tooltip
                                        cursor={{ stroke: '#94a3b8', strokeWidth: 1, strokeDasharray: '4 4' }}
                                        contentStyle={{ background: 'rgba(15, 23, 42, 0.9)', border: '1px solid #334155', borderRadius: '8px', color: '#fff', boxShadow: '0 10px 30px -10px rgba(0,0,0,0.5)' }}
                                        itemStyle={{ color: '#fff', fontWeight: 'bold' }}
                                        labelStyle={{ color: '#94a3b8', marginBottom: '4px' }}
                                        labelFormatter={(label) => `Time: ${formatTime(label)}`}
                                        formatter={(value, name) => [
                                            `${value}%`,
                                            name === 'score' ? 'Threat Score' : 'Threshold'
                                        ]}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="score"
                                        stroke="#2dd4bf"
                                        strokeWidth={2}
                                        fill="url(#colorTrend)"
                                        fillOpacity={1}
                                        animationDuration={1500}
                                    />
                                    {/* Threshold Line at 70% */}
                                    <Line type="monotone" dataKey="threshold" stroke="#ef4444" strokeDasharray="4 4" strokeWidth={2} dot={false} activeDot={false} opacity={0.8} />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

            </div>
        );
    };

    const renderLiveMonitoring = () => (
        <div className="page-content">
            <div className="page-header">
                <h1>Live AI Monitoring</h1>
                <p>Real-time anomaly detection and scoring</p>
            </div>
            <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                <div className="status-indicator"></div>
                <span>{isConnected ? 'Connected to AI Model' : 'Disconnected - Reconnecting...'}</span>
            </div>
            <div className="score-display">
                <div className="score-circle" style={{ background: `conic-gradient(${currentScore > 70 ? '#ef4444' : currentScore > 30 ? '#f97316' : '#14b8a6'} ${currentScore * 3.6}deg, #1e293b 0deg)` }}>
                    <div className="score-inner">
                        <span className="score-value">{currentScore}%</span>
                        <span className="score-label">Anomaly Score</span>
                    </div>
                </div>
            </div>
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
                            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} labelStyle={{ color: '#94a3b8' }} />
                            <Area type="monotone" dataKey="score" stroke="#14b8a6" strokeWidth={2} fill="url(#colorScore)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );

    const renderAlertSettings = () => (
        <div className="page-content">
            <div className="page-header">
                <h1>Alert Settings</h1>
                <p>Configure how you receive anomaly alerts</p>
            </div>
            <div className="settings-grid">
                <div className="settings-card">
                    <h3>Notification Preferences</h3>
                    <div className="setting-item">
                        <div className="setting-info"><Mail size={20} /><div><h4>Email Alerts</h4><p>Receive alerts via email</p></div></div>
                        <label className="toggle"><input type="checkbox" checked={alertSettings.emailAlerts} onChange={(e) => setAlertSettings({ ...alertSettings, emailAlerts: e.target.checked })} /><span className="toggle-slider"></span></label>
                    </div>
                    <div className="setting-item">
                        <div className="setting-info"><Volume2 size={20} /><div><h4>Sound Alerts</h4><p>Play sound on detection</p></div></div>
                        <label className="toggle"><input type="checkbox" checked={alertSettings.soundAlerts} onChange={(e) => setAlertSettings({ ...alertSettings, soundAlerts: e.target.checked })} /><span className="toggle-slider"></span></label>
                    </div>
                    <div className="setting-item">
                        <div className="setting-info"><Bell size={20} /><div><h4>Push Notifications</h4><p>Browser push notifications</p></div></div>
                        <label className="toggle"><input type="checkbox" checked={alertSettings.pushNotifications} onChange={(e) => setAlertSettings({ ...alertSettings, pushNotifications: e.target.checked })} /><span className="toggle-slider"></span></label>
                    </div>
                </div>
                <div className="settings-card">
                    <h3>Detection Settings</h3>
                    <div className="setting-item column">
                        <div className="setting-info"><AlertTriangle size={20} /><div><h4>Alert Threshold</h4><p>Fixed by Model ({(alertSettings.threshold * 100).toFixed(0)}%)</p></div></div>
                    </div>
                    <div className="setting-item column">
                        <div className="setting-info"><Clock size={20} /><div><h4>Alert Cooldown</h4><p>Wait {alertSettings.cooldown} seconds</p></div></div>
                        <input type="range" min="10" max="120" step="10" value={alertSettings.cooldown} onChange={(e) => setAlertSettings({ ...alertSettings, cooldown: parseInt(e.target.value) })} className="range-slider" />
                    </div>
                </div>
            </div>
            <button className="btn-primary"><Save size={18} /> Save Settings</button>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-100">
            <div className="w-full bg-slate-900 border-b border-teal-900">
                <div className="relative w-full h-[240px] overflow-hidden" onMouseMove={handleMouseMove} style={{ background: 'linear-gradient(135deg, #0f172a 0%, #164e63 50%, #0f172a 100%)' }}>
                    <div className="absolute inset-0 opacity-20 pointer-events-none">
                        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg"><defs><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="#14b8a6" strokeWidth="0.5" /></pattern></defs><rect width="100%" height="100%" fill="url(#grid)" /></svg>
                    </div>
                    <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ filter: 'blur(0.5px)' }}>
                        <line x1="0" y1="30%" x2="30%" y2="30%" stroke="#14b8a6" strokeWidth="1" opacity="0.6"><animate attributeName="x2" values="0%;40%;0%" dur="8s" repeatCount="indefinite" /></line>
                        <line x1="100%" y1="60%" x2="70%" y2="60%" stroke="#14b8a6" strokeWidth="1" opacity="0.6"><animate attributeName="x2" values="100%;60%;100%" dur="10s" repeatCount="indefinite" /></line>
                    </svg>
                    {floatingElements.map((particle) => (
                        <div key={particle.id} className="absolute rounded-full bg-teal-400 pointer-events-none" style={{ left: `${particle.x}%`, top: `${particle.y}%`, width: `${particle.size}px`, height: `${particle.size}px`, animation: `float ${particle.duration}s ease-in-out infinite`, animationDelay: `${particle.delay}s`, opacity: 0.4 }} />
                    ))}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10 top-4">
                        <div className="flex gap-4 pr-12 pointer-events-auto items-center">
                            {tabs.slice(0, 2).map((tab) => (
                                <button key={tab.id} className={`banner-nav-tab ${activeTab === tab.id ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)}>
                                    <tab.icon size={18} /><span>{tab.label}</span>
                                </button>
                            ))}
                        </div>
                        <div className="relative flex flex-col items-center justify-center mx-4" style={{ transform: `translate(${mousePos.x * 0.2}px, ${mousePos.y * 0.2}px)` }}>
                            <div className="relative mb-2">
                                <svg width="60" height="60" viewBox="0 0 100 100" className="drop-shadow-xl">
                                    <defs><linearGradient id="shieldGradientSmall" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#14b8a6" /><stop offset="100%" stopColor="#06b6d4" /></linearGradient></defs>
                                    <path d="M 50 10 L 80 25 L 80 55 Q 80 80 50 90 Q 20 80 20 55 L 20 25 Z" fill="url(#shieldGradientSmall)" opacity="0.9" />
                                    <path d="M 50 30 L 60 36 L 60 48 L 50 54 L 40 48 L 40 36 Z" fill="none" stroke="white" strokeWidth="2" opacity="0.9" />
                                </svg>
                            </div>
                            <h1 className="text-5xl font-bold text-white tracking-wider banner-title-animated" style={{ textShadow: '0 0 20px rgba(20, 184, 166, 0.6)', letterSpacing: '0.1em' }}>Alertrix AI</h1>
                            <p className="text-teal-300 text-sm mt-1 tracking-widest uppercase opacity-80">Your AI guardian angel</p>
                        </div>
                        <div className="flex gap-4 pl-12 pointer-events-auto items-center">
                            {tabs.slice(2, 4).map((tab) => (
                                <button key={tab.id} className={`banner-nav-tab ${activeTab === tab.id ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)}>
                                    <tab.icon size={18} /><span>{tab.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="absolute top-4 right-4 flex items-center gap-3 z-20 pointer-events-auto">
                        <div className="glass-badge"><Cpu size={14} /><span>AI Active</span><div className="pulse-dot"></div></div>
                        <button className={`glass-btn ${alertsMuted ? 'muted' : ''}`} onClick={(e) => { e.stopPropagation(); setAlertsMuted(!alertsMuted); }} title={alertsMuted ? 'Unmute Alerts' : 'Mute Alerts'}>
                            {alertsMuted ? <BellOff size={18} /> : <Bell size={18} />}
                            {!alertsMuted && alertCount > 0 && <span className="alert-count">{alertCount > 99 ? '99+' : alertCount}</span>}
                        </button>
                        <div className="glass-divider"></div>
                        <button className="glass-btn profile-trigger" onClick={(e) => { e.stopPropagation(); setShowProfile(!showProfile); }}><User size={18} /></button>
                    </div>
                </div>
                {showProfile && (
                    <div className="absolute top-16 right-4 z-50">
                        <div className="profile-dropdown banner-dropdown">
                            <div className="profile-header"><div className="profile-avatar large"><User size={28} /></div><div className="profile-info"><h4>{userProfile.name}</h4><span className="role-badge">{userProfile.role}</span></div></div>
                            <div className="profile-details">
                                <div className="detail-item"><Mail size={16} /><span>{userProfile.email}</span></div>
                                <div className="detail-item"><Phone size={16} /><span>{userProfile.phone}</span></div>
                                <div className="detail-item"><Shield size={16} /><span>{userProfile.department}</span></div>
                                <div className="detail-item"><Clock size={16} /><span>Shift: {userProfile.shift}</span></div>
                            </div>
                            <div className="profile-footer">
                                <button className="btn-secondary"><Settings size={16} /> Settings</button>
                                <button className="logout-btn" onClick={onLogout}>
                                    <span className="logout-btn-text">Log Out</span>
                                    <span className="logout-btn-icon"><PersonStanding size={18} /></span>
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
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