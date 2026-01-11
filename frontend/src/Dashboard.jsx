import React, { useState, useEffect, useRef } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    AreaChart
} from 'recharts';
import {
    Camera,
    Upload,
    Activity,
    AlertTriangle,
    Wifi,
    WifiOff,
    Settings,
    Bell,
    TrendingUp,
    Shield,
    Eye,
    Zap
} from 'lucide-react';

const Dashboard = () => {
    const [mode, setMode] = useState('live'); // 'live' or 'upload'
    const [isConnected, setIsConnected] = useState(false);
    const [anomalyData, setAnomalyData] = useState([]);
    const [currentScore, setCurrentScore] = useState(0);
    const [alertCount, setAlertCount] = useState(0);
    const wsRef = useRef(null);
    const maxDataPoints = 50;

    // WebSocket connection for real-time anomaly data
    useEffect(() => {
        const connectWebSocket = () => {
            wsRef.current = new WebSocket('ws://localhost:8000/ws/stream');

            wsRef.current.onopen = () => {
                setIsConnected(true);
                console.log('WebSocket connected');
            };

            wsRef.current.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const newPoint = {
                    time: new Date().toLocaleTimeString('en-US', {
                        hour12: false,
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    }),
                    score: data.anomaly_score,
                    timestamp: Date.now()
                };

                setCurrentScore(data.anomaly_score);

                // Count high anomaly alerts
                if (data.anomaly_score > 0.7) {
                    setAlertCount(prev => prev + 1);
                }

                setAnomalyData(prev => {
                    const updated = [...prev, newPoint];
                    return updated.slice(-maxDataPoints);
                });
            };

            wsRef.current.onclose = () => {
                setIsConnected(false);
                console.log('WebSocket disconnected');
                // Attempt to reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };

            wsRef.current.onerror = (error) => {
                console.error('WebSocket error:', error);
                setIsConnected(false);
            };
        };

        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, []);

    // Get anomaly level color and label
    const getAnomalyLevel = (score) => {
        if (score < 0.3) return { color: '#22c55e', label: 'Normal', bg: 'rgba(34, 197, 94, 0.1)' };
        if (score < 0.7) return { color: '#eab308', label: 'Warning', bg: 'rgba(234, 179, 8, 0.1)' };
        return { color: '#ef4444', label: 'Critical', bg: 'rgba(239, 68, 68, 0.1)' };
    };

    const anomalyLevel = getAnomalyLevel(currentScore);

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
            console.log('Upload response:', data);
            alert(`Video uploaded successfully: ${file.name}`);
        } catch (error) {
            console.error('Upload error:', error);
            alert('Failed to upload video');
        }
    };

    // Custom tooltip for the chart
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const level = getAnomalyLevel(payload[0].value);
            return (
                <div className="glass-card p-3">
                    <p className="text-gray-400 text-xs mb-1">{payload[0].payload.time}</p>
                    <p className="font-semibold" style={{ color: level.color }}>
                        Score: {payload[0].value.toFixed(4)}
                    </p>
                    <p className="text-xs" style={{ color: level.color }}>
                        {level.label}
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="min-h-screen bg-[#0f172a] text-white">
            {/* Sidebar */}
            <aside className="fixed left-0 top-0 h-full w-20 glass-card rounded-none border-l-0 border-t-0 border-b-0 flex flex-col items-center py-6 z-50">
                {/* Logo */}
                <div className="mb-8">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center glow-pulse">
                        <Shield className="w-6 h-6" />
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 flex flex-col gap-4">
                    <button
                        onClick={() => setMode('live')}
                        className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 ${mode === 'live'
                                ? 'bg-blue-500/20 text-blue-400 shadow-lg shadow-blue-500/20'
                                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                            }`}
                        title="Live Camera"
                    >
                        <Camera className="w-5 h-5" />
                    </button>
                    <button
                        onClick={() => setMode('upload')}
                        className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 ${mode === 'upload'
                                ? 'bg-purple-500/20 text-purple-400 shadow-lg shadow-purple-500/20'
                                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                            }`}
                        title="Upload Video"
                    >
                        <Upload className="w-5 h-5" />
                    </button>
                </nav>

                {/* Bottom Actions */}
                <div className="flex flex-col gap-4">
                    <button className="w-12 h-12 rounded-xl flex items-center justify-center text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-all duration-300 relative">
                        <Bell className="w-5 h-5" />
                        {alertCount > 0 && (
                            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center">
                                {alertCount > 99 ? '99+' : alertCount}
                            </span>
                        )}
                    </button>
                    <button className="w-12 h-12 rounded-xl flex items-center justify-center text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-all duration-300">
                        <Settings className="w-5 h-5" />
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="ml-20 p-8">
                {/* Header */}
                <header className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold gradient-text">Alertrix</h1>
                        <p className="text-gray-400 mt-1">Spatiotemporal Anomaly Detection System</p>
                    </div>
                    <div className="flex items-center gap-4">
                        {/* Connection Status */}
                        <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${isConnected ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                            }`}>
                            {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
                            <span className="text-sm font-medium">
                                {isConnected ? 'Connected' : 'Disconnected'}
                            </span>
                            <div className={`status-dot ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
                        </div>
                    </div>
                </header>

                {/* Stats Cards */}
                <div className="grid grid-cols-4 gap-6 mb-8">
                    {/* Current Score */}
                    <div className="glass-card p-6 glass-card-hover transition-all duration-300">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-gray-400 text-sm">Current Score</span>
                            <Activity className="w-5 h-5 text-blue-400" />
                        </div>
                        <div className="flex items-end gap-2">
                            <span
                                className="text-4xl font-bold"
                                style={{ color: anomalyLevel.color }}
                            >
                                {currentScore.toFixed(2)}
                            </span>
                            <span
                                className="text-sm mb-1 px-2 py-0.5 rounded-full"
                                style={{ backgroundColor: anomalyLevel.bg, color: anomalyLevel.color }}
                            >
                                {anomalyLevel.label}
                            </span>
                        </div>
                    </div>

                    {/* Alert Count */}
                    <div className="glass-card p-6 glass-card-hover transition-all duration-300">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-gray-400 text-sm">Alerts Today</span>
                            <AlertTriangle className="w-5 h-5 text-yellow-400" />
                        </div>
                        <div className="flex items-end gap-2">
                            <span className="text-4xl font-bold text-yellow-400">{alertCount}</span>
                            <span className="text-gray-500 text-sm mb-1">anomalies</span>
                        </div>
                    </div>

                    {/* Mode */}
                    <div className="glass-card p-6 glass-card-hover transition-all duration-300">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-gray-400 text-sm">Detection Mode</span>
                            <Eye className="w-5 h-5 text-purple-400" />
                        </div>
                        <div className="flex items-end gap-2">
                            <span className="text-2xl font-bold text-purple-400 capitalize">{mode}</span>
                            <span className="text-gray-500 text-sm mb-1">
                                {mode === 'live' ? 'Camera' : 'Video'}
                            </span>
                        </div>
                    </div>

                    {/* Processing */}
                    <div className="glass-card p-6 glass-card-hover transition-all duration-300">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-gray-400 text-sm">Processing</span>
                            <Zap className="w-5 h-5 text-cyan-400" />
                        </div>
                        <div className="flex items-end gap-2">
                            <span className="text-2xl font-bold text-cyan-400">Real-time</span>
                            <span className="text-gray-500 text-sm mb-1">100ms</span>
                        </div>
                    </div>
                </div>

                {/* Main Grid */}
                <div className="grid grid-cols-3 gap-6">
                    {/* Live Feed Section */}
                    <div className="col-span-2 glass-card p-6">
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                                    {mode === 'live' ? (
                                        <Camera className="w-5 h-5 text-blue-400" />
                                    ) : (
                                        <Upload className="w-5 h-5 text-purple-400" />
                                    )}
                                </div>
                                <div>
                                    <h2 className="text-xl font-semibold">
                                        {mode === 'live' ? 'Live Feed' : 'Video Upload'}
                                    </h2>
                                    <p className="text-gray-400 text-sm">
                                        {mode === 'live' ? 'Real-time camera stream' : 'Analyze uploaded video'}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className={`status-dot ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
                                <span className="text-sm text-gray-400">
                                    {isConnected ? 'Streaming' : 'Offline'}
                                </span>
                            </div>
                        </div>

                        {/* Video Placeholder / Upload Zone */}
                        {mode === 'live' ? (
                            <div className="aspect-video bg-black/50 rounded-xl flex items-center justify-center border border-white/10">
                                <div className="text-center">
                                    <Camera className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                                    <p className="text-gray-400">Live camera feed will appear here</p>
                                    <p className="text-gray-500 text-sm mt-2">Connect your camera to start streaming</p>
                                </div>
                            </div>
                        ) : (
                            <label className="aspect-video bg-black/50 rounded-xl flex items-center justify-center border-2 border-dashed border-white/20 hover:border-purple-500/50 cursor-pointer transition-all duration-300 group">
                                <input
                                    type="file"
                                    accept="video/*"
                                    onChange={handleFileUpload}
                                    className="hidden"
                                />
                                <div className="text-center">
                                    <Upload className="w-16 h-16 text-gray-600 mx-auto mb-4 group-hover:text-purple-400 transition-colors" />
                                    <p className="text-gray-400 group-hover:text-gray-300 transition-colors">
                                        Drop your video file here or click to browse
                                    </p>
                                    <p className="text-gray-500 text-sm mt-2">
                                        Supports MP4, AVI, MOV, MKV, WebM
                                    </p>
                                </div>
                            </label>
                        )}
                    </div>

                    {/* Real-time Anomaly Chart */}
                    <div className="glass-card p-6">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
                                <TrendingUp className="w-5 h-5 text-blue-400" />
                            </div>
                            <div>
                                <h2 className="text-xl font-semibold">Anomaly Pulse</h2>
                                <p className="text-gray-400 text-sm">Real-time detection score</p>
                            </div>
                        </div>

                        <div className="h-64 chart-container rounded-lg p-2">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={anomalyData}>
                                    <defs>
                                        <linearGradient id="anomalyGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid
                                        strokeDasharray="3 3"
                                        stroke="rgba(255,255,255,0.1)"
                                        vertical={false}
                                    />
                                    <XAxis
                                        dataKey="time"
                                        stroke="#64748b"
                                        fontSize={10}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        domain={[0, 1]}
                                        stroke="#64748b"
                                        fontSize={10}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(value) => value.toFixed(1)}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Area
                                        type="monotone"
                                        dataKey="score"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        fill="url(#anomalyGradient)"
                                        dot={false}
                                        activeDot={{ r: 4, strokeWidth: 2 }}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Threshold Indicators */}
                        <div className="mt-4 flex justify-between text-xs">
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-green-500" />
                                <span className="text-gray-400">Normal (0-0.3)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                                <span className="text-gray-400">Warning (0.3-0.7)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full bg-red-500" />
                                <span className="text-gray-400">Critical (0.7+)</span>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default Dashboard;
