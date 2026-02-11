from flask import Flask, request, jsonify, render_template_string, Response, send_from_directory
from flask_cors import CORS
from datetime import datetime
import base64
import json
import time
import queue
import threading

app = Flask(__name__)
CORS(app)

# Store flags in memory (use database later)
flags = []

# Store live screenshots for each student
live_screens = {}  # {studentId: {screenshot, url, timestamp}}

# SSE: list of per-client queues so multiple viewers all get events
sse_clients = []
sse_clients_lock = threading.Lock()

# WebRTC signaling store
webrtc_offers = {}   # {studentId: complete offer SDP}
webrtc_answers = {}  # {studentId: complete answer SDP}

def broadcast(message):
    """Send an event to every connected SSE client."""
    with sse_clients_lock:
        dead = []
        for q in sse_clients:
            try:
                q.put_nowait(message)
            except Exception:
                dead.append(q)
        for q in dead:
            sse_clients.remove(q)

@app.route('/flag', methods=['POST'])
def receive_flag():
    data = request.json
    data['received_at'] = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
    flags.append(data)
    print(f"🚨 FLAG: Student {data['studentId']} accessed {data['domain']} at {data['received_at']}")

    # Push to all SSE clients for real-time updates
    broadcast({
        'type': 'new_flag',
        'data': data
    })

    return jsonify({'status': 'received'}), 200

@app.route('/live-update', methods=['POST'])
def receive_live_update():
    """Receive live screenshot updates from students"""
    data = request.json
    student_id = data.get('studentId')

    # Store latest screenshot for this student
    live_screens[student_id] = {
        'screenshot': data.get('screenshot'),
        'currentUrl': data.get('currentUrl'),
        'currentTitle': data.get('currentTitle'),
        'timestamp': data.get('timestamp'),
        'lastUpdate': datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
    }

    # Push update to all SSE clients
    broadcast({
        'type': 'live_screen_update',
        'studentId': student_id,
        'data': live_screens[student_id]
    })

    return jsonify({'status': 'received'}), 200

@app.route('/live-screens')
def get_live_screens():
    """Get current live screens for all students"""
    return jsonify(live_screens)

@app.route('/flags')
def get_flags():
    """Return all recorded flags for the violation log"""
    return jsonify(list(reversed(flags)))

# --- WebRTC Signaling ---

@app.route('/signal/offer', methods=['POST'])
def signal_offer():
    """Student posts their complete offer SDP (with ICE candidates baked in)"""
    data = request.json
    student_id = data['studentId']
    webrtc_offers[student_id] = data['offer']
    # Clear any stale answer from a previous session
    webrtc_answers.pop(student_id, None)
    # Notify all monitors so they can connect
    broadcast({
        'type': 'webrtc_offer',
        'studentId': student_id,
        'offer': data['offer']
    })
    return jsonify({'status': 'ok'})

@app.route('/signal/answer', methods=['POST'])
def signal_answer():
    """Professor posts their complete answer SDP"""
    data = request.json
    student_id = data['studentId']
    webrtc_answers[student_id] = data['answer']
    return jsonify({'status': 'ok'})

@app.route('/signal/answer/<student_id>')
def get_answer(student_id):
    """Student polls for the professor's answer"""
    answer = webrtc_answers.get(student_id)
    if answer:
        return jsonify({'answer': answer})
    return jsonify({'answer': None})

@app.route('/signal/offers')
def get_offers():
    """Professor gets all pending offers (for when monitor loads after students join)"""
    return jsonify(webrtc_offers)

# --- End WebRTC Signaling ---

@app.route('/stream')
def stream():
    """Server-Sent Events endpoint for real-time updates (supports multiple viewers)"""
    client_queue = queue.Queue()
    with sse_clients_lock:
        sse_clients.append(client_queue)

    def event_stream():
        try:
            while True:
                try:
                    message = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(message)}\n\n"
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            with sse_clients_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)

    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/dashboard')
def dashboard():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Exam Monitor Dashboard - Saint Clair College</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .header {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .header h1 {
                color: #2c3e50;
                margin-bottom: 10px;
            }
            .header .subtitle {
                color: #7f8c8d;
                font-size: 14px;
            }
            .stats {
                background: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-around;
            }
            .stat-box {
                text-align: center;
            }
            .stat-number {
                font-size: 36px;
                font-weight: bold;
                color: #e74c3c;
            }
            .stat-label {
                color: #7f8c8d;
                font-size: 14px;
                margin-top: 5px;
            }
            .flag {
                background: white;
                margin: 15px 0;
                padding: 20px;
                border-radius: 10px;
                border-left: 5px solid #e74c3c;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                animation: slideIn 0.3s ease-out;
            }
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            .flag-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #ecf0f1;
            }
            .alert-badge {
                background: #e74c3c;
                color: white;
                padding: 8px 15px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
            }
            .flag-info {
                margin: 10px 0;
                line-height: 1.6;
            }
            .flag-label {
                font-weight: bold;
                color: #2c3e50;
                display: inline-block;
                width: 120px;
            }
            .flag-value {
                color: #34495e;
            }
            .timestamp {
                color: #95a5a6;
                font-size: 14px;
                font-style: italic;
            }
            .flag img {
                max-width: 100%;
                margin-top: 15px;
                border-radius: 8px;
                border: 2px solid #ecf0f1;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .no-flags {
                background: white;
                padding: 40px;
                border-radius: 10px;
                text-align: center;
                color: #7f8c8d;
            }
            .auto-refresh {
                position: fixed;
                top: 20px;
                right: 20px;
                background: rgba(255,255,255,0.9);
                padding: 10px 15px;
                border-radius: 20px;
                font-size: 12px;
                color: #2c3e50;
            }
        </style>
        <script>
            // Real-time updates using Server-Sent Events
            const eventSource = new EventSource('/stream');

            eventSource.onmessage = function(event) {
                const message = JSON.parse(event.data);

                if (message.type === 'new_flag') {
                    // New violation detected! Reload to show it
                    console.log('🚨 New violation detected! Reloading...');
                    location.reload();
                } else if (message.type === 'heartbeat') {
                    // Keep-alive heartbeat, do nothing
                    console.log('💓 Connection alive');
                }
            };

            eventSource.onerror = function(error) {
                console.error('SSE connection error, will retry...', error);
            };
        </script>
    </head>
    <body>
        <div class="auto-refresh">
            ⚡ Live Updates: ON
        </div>

        <div class="header">
            <h1>🚨 Live Exam Integrity Monitor</h1>
            <p class="subtitle">Saint Clair College - Real-time AI Detection System</p>
        </div>

        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{{ flags|length }}</div>
                <div class="stat-label">Total Flags</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ unique_students|length }}</div>
                <div class="stat-label">Students Flagged</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ unique_domains|length }}</div>
                <div class="stat-label">Unique AI Sites</div>
            </div>
        </div>

        {% if flags %}
            {% for flag in flags %}
            <div class="flag">
                <div class="flag-header">
                    <span class="alert-badge">⚠️ UNAUTHORIZED ACCESS DETECTED</span>
                    <span class="timestamp">{{ flag.received_at }}</span>
                </div>

                <div class="flag-info">
                    <div>
                        <span class="flag-label">Student ID:</span>
                        <span class="flag-value">{{ flag.studentId }}</span>
                    </div>
                    <div>
                        <span class="flag-label">AI Site Accessed:</span>
                        <span class="flag-value" style="color: #e74c3c; font-weight: bold;">{{ flag.domain }}</span>
                    </div>
                    {% if flag.flagType %}
                    <div>
                        <span class="flag-label">Violation Type:</span>
                        <span class="flag-value" style="color: #e74c3c; font-weight: bold;">
                            {% if flag.flagType == 'PASTE' %}📋 PASTED TEXT INTO AI
                            {% elif flag.flagType == 'COPY' %}📄 COPIED AI RESPONSE
                            {% elif flag.flagType == 'TYPING' %}⌨️ TYPED INTO AI
                            {% else %}🌐 VISITED AI SITE
                            {% endif %}
                        </span>
                    </div>
                    {% endif %}
                    <div>
                        <span class="flag-label">Full URL:</span>
                        <span class="flag-value" style="font-size: 12px; word-break: break-all;">{{ flag.fullUrl }}</span>
                    </div>
                </div>

                {% if flag.pastedText or flag.copiedText or flag.typedText %}
                <div style="background: #fff3cd; padding: 15px; margin-top: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                    <strong style="color: #856404;">🔍 CAPTURED EVIDENCE:</strong>
                    <div style="margin-top: 10px; font-family: monospace; background: white; padding: 10px; border-radius: 3px; max-height: 200px; overflow-y: auto;">
                        {% if flag.pastedText %}
                            <div style="margin-bottom: 10px;">
                                <strong style="color: #d32f2f;">📋 Text Pasted:</strong><br>
                                "{{ flag.pastedText }}"
                                {% if flag.textLength > 500 %}
                                <br><em style="color: #666;">(Showing first 500 of {{ flag.textLength }} characters)</em>
                                {% endif %}
                            </div>
                        {% endif %}
                        {% if flag.copiedText %}
                            <div style="margin-bottom: 10px;">
                                <strong style="color: #d32f2f;">📄 Text Copied:</strong><br>
                                "{{ flag.copiedText }}"
                                {% if flag.textLength > 500 %}
                                <br><em style="color: #666;">(Showing first 500 of {{ flag.textLength }} characters)</em>
                                {% endif %}
                            </div>
                        {% endif %}
                        {% if flag.typedText %}
                            <div style="margin-bottom: 10px;">
                                <strong style="color: #d32f2f;">⌨️ Text Typed:</strong><br>
                                "{{ flag.typedText }}"
                                {% if flag.textLength > 500 %}
                                <br><em style="color: #666;">(Showing first 500 of {{ flag.textLength }} characters)</em>
                                {% endif %}
                            </div>
                        {% endif %}
                    </div>
                </div>
                {% endif %}

                {% if flag.screenshot %}
                <details open>
                    <summary style="cursor: pointer; color: #3498db; font-weight: bold; margin-top: 10px;">
                        📸 View Screenshot Evidence
                    </summary>
                    <img src="{{ flag.screenshot }}" alt="Screenshot Evidence">
                </details>
                {% endif %}
            </div>
            {% endfor %}
        {% else %}
            <div class="no-flags">
                <h2>✅ No Violations Detected</h2>
                <p style="margin-top: 10px;">All students are following exam protocols</p>
            </div>
        {% endif %}
    </body>
    </html>
    '''

    # Calculate stats
    unique_students = set(flag['studentId'] for flag in flags)
    unique_domains = set(flag['domain'] for flag in flags)

    return render_template_string(
        html,
        flags=list(reversed(flags)),
        unique_students=unique_students,
        unique_domains=unique_domains
    )

@app.route('/grid')
def grid_dashboard():
    """Grid view dashboard - visual monitoring of all students"""
    with open('grid-dashboard.html', 'r') as f:
        return f.read()

@app.route('/demo')
def demo():
    """Split-screen demo view - student simulation + live monitoring"""
    with open('demo.html', 'r') as f:
        return f.read()

@app.route('/join')
def join_exam():
    """Student join page — share screen via browser, no extension needed"""
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Join Exam Session — St. Clair College</title>
    <style>
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            background: #f4f5f7;
            color: #333;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .card {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            padding: 40px;
            max-width: 420px;
            width: 90%;
            text-align: center;
        }
        .card img { height: 32px; margin-bottom: 20px; }
        .card h1 { font-size: 18px; font-weight: 600; color: #222; margin-bottom: 6px; }
        .card p { font-size: 13px; color: #888; margin-bottom: 24px; line-height: 1.5; }
        .field {
            margin-bottom: 16px;
            text-align: left;
        }
        .field label {
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: #555;
            margin-bottom: 4px;
        }
        .field input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            outline: none;
        }
        .field input:focus { border-color: #4a90d9; }
        .btn {
            display: inline-block;
            width: 100%;
            padding: 12px;
            background: #00843D;
            color: #fff;
            border: none;
            border-radius: 5px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn:hover { background: #006e33; }
        .btn:disabled { background: #aaa; cursor: not-allowed; }
        .status {
            margin-top: 20px;
            font-size: 13px;
            color: #666;
        }
        .status.active { color: #00843D; }
        .status.error { color: #d63031; }
        .preview {
            margin-top: 16px;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #e0e0e0;
            display: none;
        }
        .preview img {
            width: 100%;
            display: block;
        }
        .dot {
            display: inline-block;
            width: 7px; height: 7px;
            background: #d63031;
            border-radius: 50%;
            margin-right: 5px;
            animation: pulse 2s infinite;
            vertical-align: middle;
        }
        @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
        .stop-btn {
            margin-top: 12px;
            padding: 8px 20px;
            background: #fff;
            color: #d63031;
            border: 1px solid #d63031;
            border-radius: 5px;
            font-size: 12px;
            cursor: pointer;
        }
        .stop-btn:hover { background: #ffeaea; }
        .mode-note {
            font-size: 11px;
            color: #999;
            margin-top: 8px;
            line-height: 1.4;
        }
        .mode-note strong { color: #666; }
        @media (max-width: 500px) {
            body { padding: 12px; }
            .card { padding: 24px 20px; width: 95%; }
            .card h1 { font-size: 16px; }
            .card p { font-size: 12px; }
            .field input { font-size: 16px; padding: 12px; }
            .btn { padding: 14px; font-size: 15px; }
            .stop-btn { padding: 10px 24px; font-size: 13px; }
        }
    </style>
</head>
<body>
    <div class="card">
        <img src="/scc-logo.svg" alt="St. Clair College">
        <h1>Join Exam Session</h1>
        <p id="intro">Enter your student ID and share your screen to join the monitored exam session.</p>

        <div id="setupForm">
            <div class="field">
                <label>Student ID</label>
                <input type="text" id="studentId" placeholder="e.g. W0871234" autofocus>
            </div>
            <button class="btn" id="joinBtn" onclick="startSharing()">Share Screen & Join</button>
        </div>

        <div id="activeView" style="display:none;">
            <div class="status active"><span class="dot"></span><span id="shareMode">Screen is being shared</span></div>
            <div id="rtcStatus" style="font-size:11px;color:#aaa;margin-top:4px;">Connecting live stream...</div>
            <div class="preview" id="preview"><img id="previewImg"></div>
            <div id="captureStats" style="font-size:11px;color:#aaa;margin-top:8px;">Captures: 0 | Flags: 0</div>
            <button class="stop-btn" onclick="stopSharing()">Stop Sharing</button>
        </div>

        <div class="status" id="status"></div>
    </div>

    <script>
        let stream = null;
        let captureWorker = null;
        let activeStudentId = null;
        let tabAwayCount = 0;
        let lastFlaggedLabel = '';
        let captureCount = 0;
        let flagCount = 0;
        let peerConnection = null;
        let answerPollInterval = null;
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const video = document.createElement('video');

        const RTC_CONFIG = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };

        function updateStats() {
            const el = document.getElementById('captureStats');
            if (el) el.textContent = 'Captures: ' + captureCount + ' | Flags: ' + flagCount;
        }

        async function setupWebRTC(studentId, mediaStream) {
            const rtcEl = document.getElementById('rtcStatus');
            try {
                peerConnection = new RTCPeerConnection(RTC_CONFIG);

                // Add video track to peer connection
                mediaStream.getVideoTracks().forEach(track => {
                    peerConnection.addTrack(track, mediaStream);
                });

                // Create offer
                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);

                // Wait for ICE gathering to complete (bakes candidates into SDP)
                await new Promise((resolve) => {
                    if (peerConnection.iceGatheringState === 'complete') {
                        resolve();
                    } else {
                        peerConnection.addEventListener('icegatheringstatechange', () => {
                            if (peerConnection.iceGatheringState === 'complete') resolve();
                        });
                        // Fallback timeout — don't wait forever
                        setTimeout(resolve, 5000);
                    }
                });

                // Send complete offer (with ICE candidates) to signaling server
                await fetch('/signal/offer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        studentId: studentId,
                        offer: peerConnection.localDescription
                    })
                });

                rtcEl.textContent = 'Waiting for professor to connect...';

                // Poll for answer from professor
                answerPollInterval = setInterval(async () => {
                    try {
                        const res = await fetch('/signal/answer/' + encodeURIComponent(studentId));
                        const data = await res.json();
                        if (data.answer) {
                            clearInterval(answerPollInterval);
                            answerPollInterval = null;
                            await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
                            rtcEl.textContent = 'Live stream connected';
                            rtcEl.style.color = '#00843D';
                        }
                    } catch (e) {
                        console.error('Answer poll error:', e);
                    }
                }, 1500);

                // Monitor connection state
                peerConnection.addEventListener('connectionstatechange', () => {
                    const state = peerConnection.connectionState;
                    if (state === 'connected') {
                        rtcEl.textContent = 'Live stream connected';
                        rtcEl.style.color = '#00843D';
                    } else if (state === 'disconnected' || state === 'failed') {
                        rtcEl.textContent = 'Live stream disconnected — screenshots still active';
                        rtcEl.style.color = '#d63031';
                    }
                });

            } catch (e) {
                console.error('WebRTC setup error:', e);
                rtcEl.textContent = 'Live stream unavailable — using screenshots';
                rtcEl.style.color = '#e17055';
            }
        }

        // Web Worker that keeps ticking even when tab is in background
        function startWorkerTimer(studentId) {
            if (captureWorker) captureWorker.terminate();
            const blob = new Blob([
                'setInterval(function(){ postMessage("tick"); }, 1000);'
            ], { type: 'application/javascript' });
            captureWorker = new Worker(URL.createObjectURL(blob));
            captureWorker.onmessage = function() {
                captureAndSend(studentId);
            };
            // Fire immediately too
            captureAndSend(studentId);
        }

        // AI sites — matched against the shared tab/window title
        const AI_KEYWORDS = [
            'chatgpt', 'openai', 'claude', 'anthropic', 'gemini',
            'copilot', 'perplexity', 'bard', 'poe.com', 'character.ai',
            'you.com', 'phind', 'huggingface', 'hugging face', 'writesonic',
            'jasper', 'quillbot', 'grammarly'
        ];

        function detectAI(label) {
            if (!label) return null;
            const lower = label.toLowerCase();
            for (const kw of AI_KEYWORDS) {
                if (lower.includes(kw)) return kw;
            }
            return null;
        }

        // Detect if screen share is available (not on mobile)
        const canScreenShare = !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia);
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        let usingCamera = false;

        // Update button text for mobile
        if (isMobile || !canScreenShare) {
            document.getElementById('joinBtn').textContent = 'Share Camera & Join';
            document.getElementById('intro').textContent = 'Enter your student ID and share your camera to join the monitored exam session.';
        }

        async function startSharing() {
            const idInput = document.getElementById('studentId');
            const studentId = idInput.value.trim();
            if (!studentId) { idInput.focus(); return; }
            activeStudentId = studentId;

            document.getElementById('joinBtn').disabled = true;
            document.getElementById('status').textContent = isMobile ? 'Requesting camera access...' : 'Requesting screen access...';

            try {
                if (isMobile || !canScreenShare) {
                    // Mobile: use front camera
                    stream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
                        audio: false
                    });
                    usingCamera = true;
                } else {
                    // Desktop: prefer entire screen so professor sees everything
                    stream = await navigator.mediaDevices.getDisplayMedia({
                        video: { cursor: 'always', displaySurface: 'monitor' },
                        audio: false
                    });
                    usingCamera = false;
                }

                video.srcObject = stream;
                video.setAttribute('playsinline', '');
                video.setAttribute('autoplay', '');
                await video.play();

                // Show active state
                document.getElementById('setupForm').style.display = 'none';
                document.getElementById('activeView').style.display = '';
                document.getElementById('intro').textContent = 'Student: ' + studentId;
                document.getElementById('status').textContent = '';
                document.getElementById('preview').style.display = '';

                if (usingCamera) {
                    document.querySelector('.status.active').innerHTML = '<span class="dot"></span>Camera is being shared';
                }

                // Handle user stopping share via browser UI
                stream.getVideoTracks()[0].onended = () => stopSharing();

                // Use Web Worker timer so captures continue when this tab is in background
                startWorkerTimer(studentId);

                // Set up WebRTC for real-time video streaming to professor
                setupWebRTC(studentId, stream);

            } catch (err) {
                document.getElementById('status').className = 'status error';
                document.getElementById('status').textContent = isMobile
                    ? 'Camera access was denied. Please allow camera permissions.'
                    : 'Screen share was denied or cancelled.';
                document.getElementById('joinBtn').disabled = false;
            }
        }

        // Detect when student leaves this tab
        // Uses sendBeacon for reliability (fetch can get cancelled on page hide)
        let lastSwitchTime = 0;
        function handleTabLeave(type, detail) {
            if (!activeStudentId || !stream) return;
            const now = Date.now();
            if (now - lastSwitchTime < 3000) return; // debounce 3s
            lastSwitchTime = now;
            tabAwayCount++;
            sendFlagBeacon(activeStudentId, type, detail + ' (switch #' + tabAwayCount + ')');
        }

        // sendBeacon version — guaranteed delivery even when page is hiding
        function sendFlagBeacon(studentId, flagType, detail, domain) {
            let screenshot = null;
            try {
                if (stream && stream.active && video.videoWidth > 0) {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    ctx.drawImage(video, 0, 0);
                    screenshot = canvas.toDataURL('image/jpeg', 0.5);
                }
            } catch(e) {}

            const payload = JSON.stringify({
                studentId: studentId,
                domain: domain || flagType,
                fullUrl: detail,
                flagType: flagType,
                timestamp: new Date().toISOString(),
                screenshot: screenshot
            });
            // sendBeacon is fire-and-forget, survives page hide
            navigator.sendBeacon('/flag', new Blob([payload], { type: 'application/json' }));
            flagCount++;
            updateStats();
        }

        document.addEventListener('visibilitychange', function() {
            if (document.hidden) handleTabLeave('TAB_SWITCH', 'Student left exam tab');
        });

        window.addEventListener('blur', function() {
            handleTabLeave('FOCUS_LOST', 'Student switched away from exam');
        });

        async function sendFlag(studentId, flagType, detail, domain) {
            let screenshot = null;
            if (stream && stream.active) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                ctx.drawImage(video, 0, 0);
                screenshot = canvas.toDataURL('image/jpeg', 0.6);
            }

            try {
                await fetch('/flag', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        studentId: studentId,
                        domain: domain || flagType,
                        fullUrl: detail,
                        flagType: flagType,
                        timestamp: new Date().toISOString(),
                        screenshot: screenshot
                    })
                });
            } catch (e) {
                console.error('Failed to send flag:', e);
            }
        }

        let sendingInProgress = false;
        let wasHidden = false;
        let hiddenSince = 0;
        async function captureAndSend(studentId) {
            if (!stream || !stream.active) return;
            if (sendingInProgress) return;
            sendingInProgress = true;

            // Periodic check: is this tab still hidden? Flag every 10 seconds of hidden time
            if (document.hidden) {
                if (!wasHidden) {
                    wasHidden = true;
                    hiddenSince = Date.now();
                } else if (Date.now() - hiddenSince > 10000) {
                    // Student has been away for 10+ seconds — flag it
                    hiddenSince = Date.now(); // reset so it flags again in 10s
                    sendFlagBeacon(studentId, 'EXTENDED_ABSENCE',
                        'Student away from exam tab for extended period');
                }
            } else {
                wasHidden = false;
            }

            const track = stream.getVideoTracks()[0];
            const label = track.label || '';
            const settings = track.getSettings ? track.getSettings() : {};
            const surfaceType = settings.displaySurface || 'unknown';
            let currentTitle = '';

            if (usingCamera) {
                currentTitle = 'Camera Feed';
            } else {
                // Screen share mode — check track label for AI sites
                const aiMatch = detectAI(label);
                if (aiMatch && label !== lastFlaggedLabel) {
                    lastFlaggedLabel = label;
                    sendFlagBeacon(studentId, 'AI_DETECTED',
                        'AI tool detected: ' + label + ' (surface: ' + surfaceType + ')',
                        aiMatch);
                }
                currentTitle = label || 'Screen Share';
                if (surfaceType === 'browser') currentTitle = label || 'Browser Tab';
                else if (surfaceType === 'window') currentTitle = label || 'Window';
                else if (surfaceType === 'monitor') currentTitle = 'Full Screen';
            }

            // Scale down for fast streaming — cap at 960px wide
            const scale = Math.min(1, 960 / (video.videoWidth || 960));
            canvas.width = Math.round((video.videoWidth || 960) * scale);
            canvas.height = Math.round((video.videoHeight || 540) * scale);
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const screenshot = canvas.toDataURL('image/jpeg', 0.3);
            document.getElementById('previewImg').src = screenshot;

            try {
                await fetch('/live-update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        studentId: studentId,
                        screenshot: screenshot,
                        currentUrl: usingCamera ? 'camera://front' : surfaceType + '://' + (label || 'browser'),
                        currentTitle: currentTitle,
                        timestamp: new Date().toISOString(),
                        type: 'LIVE_UPDATE'
                    })
                });
                captureCount++;
                updateStats();
            } catch (e) {
                console.error('Failed to send update:', e);
            } finally {
                sendingInProgress = false;
            }
        }

        function stopSharing() {
            if (captureWorker) { captureWorker.terminate(); captureWorker = null; }
            if (answerPollInterval) { clearInterval(answerPollInterval); answerPollInterval = null; }
            if (peerConnection) { peerConnection.close(); peerConnection = null; }
            if (stream) stream.getTracks().forEach(t => t.stop());
            stream = null;
            activeStudentId = null;
            lastFlaggedLabel = '';
            usingCamera = false;

            document.getElementById('setupForm').style.display = '';
            document.getElementById('activeView').style.display = 'none';
            document.getElementById('joinBtn').disabled = false;
            const defaultMsg = (isMobile || !canScreenShare)
                ? 'Enter your student ID and share your camera to join the monitored exam session.'
                : 'Enter your student ID and share your screen to join the monitored exam session.';
            document.getElementById('intro').textContent = defaultMsg;
            document.getElementById('status').className = 'status';
            document.getElementById('status').textContent = 'Sharing stopped.';
            document.getElementById('preview').style.display = 'none';
        }

        document.getElementById('studentId').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') startSharing();
        });
    </script>
</body>
</html>'''
    return html

@app.route('/scc-logo.svg')
def scc_logo():
    return send_from_directory('.', 'scc-logo.svg', mimetype='image/svg+xml')

@app.route('/monitor')
def monitor():
    """Minimalist professor dashboard — clean, small fonts, no flash"""
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Exam Monitor — St. Clair College</title>
    <style>
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
        html, body {
            height: 100%;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 13px;
            background: #f4f5f7;
            color: #333;
        }
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 20px;
            background: #fff;
            border-bottom: 1px solid #ddd;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .topbar-left {
            display: flex;
            align-items: center;
            gap: 12px;
            overflow: hidden;
        }
        .topbar-left img { height: 24px; width: auto; flex-shrink: 0; }
        .topbar-left .sep { width: 1px; height: 20px; background: #ddd; flex-shrink: 0; }
        .topbar h1 { font-size: 14px; font-weight: 600; color: #222; white-space: nowrap; }
        .topbar-nav {
            display: flex;
            gap: 4px;
            margin-left: 16px;
        }
        .topbar-nav button {
            padding: 5px 14px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #fff;
            font-size: 12px;
            cursor: pointer;
            color: #555;
        }
        .topbar-nav button:hover { background: #f0f0f0; }
        .topbar-nav button.active { background: #222; color: #fff; border-color: #222; }
        .topbar-stats {
            display: flex;
            gap: 20px;
            font-size: 12px;
            color: #666;
            flex-shrink: 0;
        }
        .topbar-stats strong { color: #222; }
        .dot-live {
            display: inline-block;
            width: 7px; height: 7px;
            background: #d63031;
            border-radius: 50%;
            margin-right: 4px;
            vertical-align: middle;
            animation: livepulse 2s infinite;
        }
        @keyframes livepulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }

        .main { padding: 16px 20px; }
        .panel { display: none; }
        .panel.active { display: block; }

        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 14px;
        }
        .tile {
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            overflow: hidden;
            cursor: pointer;
            transition: box-shadow 0.15s, border-color 0.15s;
        }
        .tile:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-color: #bbb; }
        .tile.flagged { border-color: #d63031; border-width: 2px; }
        .tile-screen {
            width: 100%;
            aspect-ratio: 16/10;
            background: #eee;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            position: relative;
        }
        .tile-screen img, .tile-screen video { width: 100%; height: 100%; object-fit: cover; transition: opacity 0.15s; }
        .tile-screen video { background: #111; }
        .tile-screen .empty { color: #bbb; font-size: 12px; }
        .rtc-badge {
            position: absolute; top: 6px; right: 6px;
            font-size: 9px; font-weight: 700; padding: 2px 6px;
            border-radius: 3px; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .rtc-badge.live { background: #d63031; color: #fff; }
        .rtc-badge.screenshots { background: rgba(0,0,0,0.5); color: #fff; }
        .tile-info {
            padding: 8px 10px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-top: 1px solid #f0f0f0;
        }
        .indicator { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; background: #b2bec3; }
        .indicator.red { background: #d63031; }
        .tile-text { flex: 1; min-width: 0; }
        .tile-id { font-weight: 600; font-size: 12px; color: #222; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .tile-meta { font-size: 11px; color: #888; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 1px; }
        .tile-violations { font-size: 11px; color: #d63031; font-weight: 700; flex-shrink: 0; background: #ffeaea; padding: 2px 7px; border-radius: 8px; }
        .empty-state { text-align: center; padding: 80px 20px; color: #999; font-size: 14px; }

        /* Violation Log */
        .log-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        .log-table th {
            text-align: left;
            padding: 8px 12px;
            background: #fff;
            border-bottom: 2px solid #e0e0e0;
            font-weight: 600;
            color: #555;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            position: sticky;
            top: 48px;
            z-index: 10;
        }
        .log-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: top;
        }
        .log-table tr:hover td { background: #fafafa; }
        .log-time { white-space: nowrap; color: #888; font-size: 11px; }
        .log-student { font-weight: 600; color: #222; }
        .log-type {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .log-type.ai { background: #d63031; color: #fff; }
        .log-type.tab { background: #e17055; color: #fff; }
        .log-type.focus { background: #fdcb6e; color: #222; }
        .log-type.access { background: #d63031; color: #fff; }
        .log-detail { color: #666; font-size: 11px; max-width: 300px; word-break: break-word; }
        .log-thumb {
            width: 120px;
            height: 75px;
            object-fit: cover;
            border-radius: 3px;
            border: 1px solid #e0e0e0;
            cursor: pointer;
        }
        .log-thumb:hover { border-color: #888; }
        .log-empty { text-align: center; padding: 60px 20px; color: #aaa; }

        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.55);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal-overlay.open { display: flex; }
        .modal-box {
            background: #fff;
            border-radius: 8px;
            overflow: hidden;
            max-width: 90vw;
            max-height: 90vh;
            box-shadow: 0 12px 40px rgba(0,0,0,0.25);
            display: flex;
            flex-direction: column;
        }
        .modal-box img, .modal-box video {
            display: block;
            max-width: 90vw;
            max-height: calc(90vh - 48px);
            object-fit: contain;
        }
        .modal-box video { background: #111; }
        .modal-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 16px;
            background: #fafafa;
            border-top: 1px solid #eee;
            font-size: 12px;
            gap: 16px;
        }
        .modal-bar .mid { font-weight: 600; color: #222; }
        .modal-bar .msite { color: #888; flex: 1; }
        .modal-bar .mclose {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 4px 14px;
            cursor: pointer;
            font-size: 12px;
            color: #555;
        }
        .modal-bar .mclose:hover { background: #f0f0f0; }
        .modal-no-screen {
            width: 640px; height: 400px;
            display: flex; align-items: center; justify-content: center;
            color: #bbb; font-size: 14px; background: #f5f5f5;
        }

        /* Mobile responsive */
        @media (max-width: 600px) {
            .topbar {
                flex-wrap: wrap;
                gap: 8px;
                padding: 8px 12px;
            }
            .topbar-left { gap: 8px; flex-wrap: wrap; width: 100%; }
            .topbar-left .sep { display: none; }
            .topbar h1 { font-size: 13px; }
            .topbar-nav { margin-left: 0; }
            .topbar-nav button { padding: 4px 10px; font-size: 11px; }
            .topbar-stats { width: 100%; justify-content: flex-start; gap: 14px; font-size: 11px; }
            .main { padding: 10px; }
            .grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
            .tile-info { padding: 6px 8px; gap: 6px; }
            .tile-id { font-size: 11px; }
            .tile-meta { font-size: 10px; }
            .log-table { display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }
            .log-table th { top: 0; font-size: 10px; padding: 6px 8px; white-space: nowrap; }
            .log-table td { padding: 8px; font-size: 11px; }
            .log-thumb { width: 80px; height: 50px; }
            .log-detail { max-width: 150px; }
            .modal-box { max-width: 96vw; max-height: 96vh; border-radius: 6px; }
            .modal-box img { max-width: 96vw; max-height: calc(96vh - 44px); }
            .modal-no-screen { width: 90vw; height: 50vw; }
            .modal-bar { padding: 8px 12px; font-size: 11px; }
            .empty-state { padding: 40px 16px; font-size: 13px; }
        }
    </style>
</head>
<body>
    <div class="topbar">
        <div class="topbar-left">
            <img src="/scc-logo.svg" alt="St. Clair College">
            <div class="sep"></div>
            <h1>Exam Monitor</h1>
            <div class="topbar-nav">
                <button class="active" id="navScreens" onclick="showPanel('screens')">Live Screens</button>
                <button id="navLog" onclick="showPanel('log')">Violation Log<span id="logBadge"></span></button>
            </div>
        </div>
        <div class="topbar-stats">
            <span><strong id="sOnline">0</strong> students</span>
            <span><strong id="sViolations">0</strong> violations</span>
            <span><span class="dot-live"></span>Live</span>
        </div>
    </div>

    <div class="main">
        <!-- Live Screens Panel -->
        <div class="panel active" id="panelScreens">
            <div class="grid" id="grid"></div>
            <div class="empty-state" id="empty">Waiting for students to connect...</div>
        </div>

        <!-- Violation Log Panel -->
        <div class="panel" id="panelLog">
            <table class="log-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Student</th>
                        <th>Type</th>
                        <th>Details</th>
                        <th>Evidence</th>
                    </tr>
                </thead>
                <tbody id="logBody"></tbody>
            </table>
            <div class="log-empty" id="logEmpty">No violations recorded yet.</div>
        </div>
    </div>

    <div class="modal-overlay" id="modal">
        <div class="modal-box">
            <div id="modalScreen"></div>
            <div class="modal-bar">
                <span class="mid" id="modalId"></span>
                <span class="msite" id="modalSite"></span>
                <button class="mclose" onclick="closeModal()">Close</button>
            </div>
        </div>
    </div>

    <script>
        const students = {};
        const violationLog = [];
        let violationCount = 0;
        let modalStudentId = null;
        const peerConnections = {}; // {studentId: RTCPeerConnection}
        const remoteStreams = {};   // {studentId: MediaStream}

        const RTC_CONFIG = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };

        // Tab navigation
        function showPanel(name) {
            document.getElementById('panelScreens').classList.toggle('active', name === 'screens');
            document.getElementById('panelLog').classList.toggle('active', name === 'log');
            document.getElementById('navScreens').classList.toggle('active', name === 'screens');
            document.getElementById('navLog').classList.toggle('active', name === 'log');
        }

        // --- WebRTC: connect to a student's stream ---
        async function connectToStudent(studentId, offer) {
            // Close any existing connection for this student
            if (peerConnections[studentId]) {
                peerConnections[studentId].close();
            }

            const pc = new RTCPeerConnection(RTC_CONFIG);
            peerConnections[studentId] = pc;

            // When we receive the video track from the student
            pc.ontrack = function(event) {
                remoteStreams[studentId] = event.streams[0];
                // Update the tile to show live video
                if (students[studentId]) {
                    students[studentId].rtcConnected = true;
                }
                renderGrid();
                if (modalStudentId === studentId) updateModal(studentId);
            };

            pc.onconnectionstatechange = function() {
                if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
                    if (students[studentId]) students[studentId].rtcConnected = false;
                    renderGrid();
                }
            };

            try {
                // Set the student's offer
                await pc.setRemoteDescription(new RTCSessionDescription(offer));

                // Create answer
                const answer = await pc.createAnswer();
                await pc.setLocalDescription(answer);

                // Wait for ICE gathering
                await new Promise((resolve) => {
                    if (pc.iceGatheringState === 'complete') {
                        resolve();
                    } else {
                        pc.addEventListener('icegatheringstatechange', () => {
                            if (pc.iceGatheringState === 'complete') resolve();
                        });
                        setTimeout(resolve, 5000);
                    }
                });

                // Send complete answer to signaling server
                await fetch('/signal/answer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        studentId: studentId,
                        answer: pc.localDescription
                    })
                });
            } catch (e) {
                console.error('WebRTC connect error for', studentId, e);
            }
        }

        // SSE
        const eventSource = new EventSource('/stream');
        eventSource.onmessage = function(e) {
            const msg = JSON.parse(e.data);
            if (msg.type === 'new_flag') handleFlag(msg.data);
            else if (msg.type === 'live_screen_update') handleLive(msg.studentId, msg.data);
            else if (msg.type === 'webrtc_offer') {
                // New student wants to stream — connect!
                connectToStudent(msg.studentId, msg.offer);
            }
        };

        async function loadInitial() {
            try {
                const res = await fetch('/live-screens');
                const screens = await res.json();
                Object.keys(screens).forEach(id => handleLive(id, screens[id]));
            } catch(e) {}
            // Load existing flags into the log
            try {
                const res = await fetch('/flags');
                const flags = await res.json();
                flags.reverse().forEach(f => addToLog(f, true));
                renderLog();
            } catch(e) {}
            // Connect to any existing WebRTC offers (student joined before professor)
            try {
                const res = await fetch('/signal/offers');
                const offers = await res.json();
                Object.keys(offers).forEach(id => {
                    if (!peerConnections[id]) connectToStudent(id, offers[id]);
                });
            } catch(e) {}
        }

        function handleLive(id, data) {
            if (!students[id]) {
                students[id] = { id: id, status: 'safe', violations: 0, site: '', screenshot: null };
            }
            students[id].screenshot = data.screenshot;
            var title = data.currentTitle || '';
            if (title && title !== 'Screen Share' && title !== 'Full Screen') {
                students[id].site = title;
            } else {
                students[id].site = extractDomain(data.currentUrl);
            }
            renderGrid();
            if (modalStudentId === id) updateModal(id);
        }

        function handleFlag(data) {
            const id = data.studentId;
            if (!students[id]) {
                students[id] = { id: id, status: 'safe', violations: 0, site: '', screenshot: null };
            }
            students[id].status = 'flagged';
            students[id].violations++;
            students[id].site = data.domain;
            if (data.screenshot) students[id].screenshot = data.screenshot;
            violationCount++;

            addToLog(data, false);
            renderGrid();
            renderLog();
            if (modalStudentId === id) updateModal(id);
            setTimeout(() => { if (students[id]) { students[id].status = 'warning'; renderGrid(); } }, 8000);
        }

        function addToLog(flag, silent) {
            violationLog.unshift({
                time: flag.received_at || flag.timestamp || new Date().toISOString(),
                studentId: flag.studentId,
                type: flag.flagType || 'ACCESS',
                domain: flag.domain || '',
                detail: flag.fullUrl || '',
                screenshot: flag.screenshot || null
            });
            if (!silent) {
                violationCount = violationLog.length;
            }
        }

        function typeLabel(t) {
            const lower = (t || '').toUpperCase();
            if (lower.includes('AI')) return 'ai';
            if (lower.includes('TAB')) return 'tab';
            if (lower.includes('FOCUS')) return 'focus';
            return 'access';
        }

        function typeName(t) {
            const lower = (t || '').toUpperCase();
            if (lower.includes('AI')) return 'AI Detected';
            if (lower.includes('TAB')) return 'Tab Switch';
            if (lower.includes('FOCUS')) return 'Focus Lost';
            if (lower.includes('PASTE')) return 'Paste';
            if (lower.includes('COPY')) return 'Copy';
            if (lower.includes('TYPING')) return 'Typing';
            return 'Site Access';
        }

        function fmtTime(t) {
            try {
                if (t.includes('T') || t.includes('Z')) {
                    const d = new Date(t);
                    return d.toLocaleDateString('en-US', {month:'short',day:'numeric',year:'numeric'})
                        + ' ' + d.toLocaleTimeString('en-US', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
                }
                return t;
            } catch { return t; }
        }

        function extractDomain(url) {
            try { return new URL(url).hostname.replace('www.', ''); } catch { return ''; }
        }

        // Modal
        function openModal(id) {
            modalStudentId = id;
            updateModal(id);
            document.getElementById('modal').classList.add('open');
        }
        function openScreenshot(src, label) {
            modalStudentId = null;
            document.getElementById('modalId').textContent = label || 'Evidence';
            document.getElementById('modalSite').textContent = '';
            document.getElementById('modalScreen').innerHTML = '<img src="' + src + '">';
            document.getElementById('modal').classList.add('open');
        }
        function updateModal(id) {
            const s = students[id];
            if (!s) return;
            document.getElementById('modalId').textContent = s.id;
            document.getElementById('modalSite').textContent = s.site || 'idle';
            const c = document.getElementById('modalScreen');
            // Prefer live WebRTC video in modal
            if (s.rtcConnected && remoteStreams[id]) {
                if (!c.querySelector('video') || c.querySelector('video').dataset.sid !== id) {
                    const v = document.createElement('video');
                    v.autoplay = true;
                    v.playsinline = true;
                    v.muted = true;
                    v.dataset.sid = id;
                    v.srcObject = remoteStreams[id];
                    c.innerHTML = '';
                    c.appendChild(v);
                }
            } else {
                c.innerHTML = s.screenshot ? '<img src="' + s.screenshot + '">' : '<div class="modal-no-screen">No screen available</div>';
            }
        }
        function closeModal() {
            modalStudentId = null;
            document.getElementById('modal').classList.remove('open');
        }
        document.getElementById('modal').addEventListener('click', function(e) { if (e.target === this) closeModal(); });
        document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeModal(); });

        // Render — in-place DOM updates to avoid flicker at 1s intervals
        function renderGrid() {
            const grid = document.getElementById('grid');
            const empty = document.getElementById('empty');
            const ids = Object.keys(students);

            document.getElementById('sOnline').textContent = ids.length;
            document.getElementById('sViolations').textContent = violationLog.length;

            if (ids.length === 0) { empty.style.display = ''; grid.innerHTML = ''; return; }
            empty.style.display = 'none';

            ids.forEach(id => {
                const s = students[id];
                const flagged = s.status === 'flagged';
                let tile = document.getElementById('tile-' + id);

                if (!tile) {
                    tile = document.createElement('div');
                    tile.id = 'tile-' + id;
                    tile.className = 'tile';
                    tile.onclick = function() { openModal(id); };
                    tile.innerHTML =
                        '<div class="tile-screen">'
                        + '<video autoplay playsinline muted style="display:none"></video>'
                        + '<img style="display:none">'
                        + '<span class="empty">No screen yet</span>'
                        + '<span class="rtc-badge screenshots" style="display:none"></span>'
                        + '</div>'
                        + '<div class="tile-info">'
                        + '<div class="indicator"></div>'
                        + '<div class="tile-text">'
                        + '<div class="tile-id"></div>'
                        + '<div class="tile-meta"></div>'
                        + '</div>'
                        + '<div class="tile-violations" style="display:none"></div>'
                        + '</div>';
                    grid.appendChild(tile);
                }

                tile.className = 'tile' + (flagged ? ' flagged' : '');
                const vid = tile.querySelector('.tile-screen video');
                const img = tile.querySelector('.tile-screen img');
                const emptyLabel = tile.querySelector('.tile-screen .empty');
                const badge = tile.querySelector('.rtc-badge');

                // Prefer WebRTC live video over screenshots
                if (s.rtcConnected && remoteStreams[id]) {
                    if (vid.srcObject !== remoteStreams[id]) {
                        vid.srcObject = remoteStreams[id];
                    }
                    vid.style.display = '';
                    img.style.display = 'none';
                    if (emptyLabel) emptyLabel.style.display = 'none';
                    badge.className = 'rtc-badge live';
                    badge.textContent = 'LIVE';
                    badge.style.display = '';
                } else if (s.screenshot) {
                    img.src = s.screenshot;
                    img.style.display = '';
                    vid.style.display = 'none';
                    if (emptyLabel) emptyLabel.style.display = 'none';
                    badge.className = 'rtc-badge screenshots';
                    badge.textContent = 'IMG';
                    badge.style.display = '';
                } else {
                    vid.style.display = 'none';
                    img.style.display = 'none';
                    if (emptyLabel) emptyLabel.style.display = '';
                    badge.style.display = 'none';
                }
                tile.querySelector('.indicator').className = 'indicator' + (flagged ? ' red' : '');
                tile.querySelector('.tile-id').textContent = s.id;
                tile.querySelector('.tile-meta').textContent = s.site || 'idle';
                const vBadge = tile.querySelector('.tile-violations');
                if (s.violations > 0) {
                    vBadge.textContent = s.violations;
                    vBadge.style.display = '';
                } else {
                    vBadge.style.display = 'none';
                }
            });

            Array.from(grid.children).forEach(el => {
                const tileId = el.id.replace('tile-', '');
                if (!students[tileId]) el.remove();
            });
        }

        function renderLog() {
            const body = document.getElementById('logBody');
            const empty = document.getElementById('logEmpty');

            if (violationLog.length === 0) { body.innerHTML = ''; empty.style.display = ''; return; }
            empty.style.display = 'none';

            body.innerHTML = violationLog.map((v, i) => {
                const cls = typeLabel(v.type);
                return '<tr>'
                    + '<td class="log-time">' + fmtTime(v.time) + '</td>'
                    + '<td class="log-student">' + v.studentId + '</td>'
                    + '<td><span class="log-type ' + cls + '">' + typeName(v.type) + '</span></td>'
                    + '<td class="log-detail">' + (v.domain || '') + (v.detail ? '<br>' + v.detail : '') + '</td>'
                    + '<td>' + (v.screenshot ? '<img class="log-thumb" src="' + v.screenshot + '" onclick="openScreenshot(this.src, \\'' + v.studentId + ' — ' + fmtTime(v.time).replace(/'/g,'') + '\\')">' : '<span style="color:#ccc">—</span>') + '</td>'
                    + '</tr>';
            }).join('');

            // Update badge
            document.getElementById('logBadge').textContent = violationLog.length > 0 ? ' (' + violationLog.length + ')' : '';
        }

        loadInitial();
    </script>
</body>
</html>'''
    return html

@app.route('/')
def index():
    return '''
    <html>
    <head>
        <title>Exam Monitor Server</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .button-group {
                display: flex;
                gap: 15px;
                justify-content: center;
                margin-top: 20px;
            }
            a {
                display: inline-block;
                padding: 15px 30px;
                background: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
            }
            a:hover {
                background: #2980b9;
            }
            .grid-link {
                background: #e74c3c;
            }
            .grid-link:hover {
                background: #c0392b;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔒 Exam Monitor Server Running</h1>
            <p>Ready to receive flags from browser extension</p>
            <div class="button-group">
                <a href="/monitor" style="background: #111;">Professor View</a>
                <a href="/join" style="background: #00843D;">Student Join</a>
                <a href="/grid" class="grid-link">Grid View</a>
                <a href="/dashboard">Log View</a>
            </div>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') != 'production'

    print("=" * 60)
    print("  ST. CLAIR COLLEGE - EXAM INTEGRITY MONITOR")
    print("=" * 60)
    print(f"  Monitor:    http://localhost:{port}/monitor")
    print(f"  Demo:       http://localhost:{port}/demo")
    print(f"  Grid View:  http://localhost:{port}/grid")
    print(f"  Dashboard:  http://localhost:{port}/dashboard")
    print(f"  API:        http://localhost:{port}/flag")
    print("=" * 60)
    print("  Server is running and waiting for flags...\n")
    app.run(debug=debug, host='0.0.0.0', port=port)
