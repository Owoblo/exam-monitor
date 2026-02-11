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
            <div class="status active"><span class="dot"></span>Screen is being shared</div>
            <div class="preview" id="preview"><img id="previewImg"></div>
            <button class="stop-btn" onclick="stopSharing()">Stop Sharing</button>
        </div>

        <div class="status" id="status"></div>
    </div>

    <script>
        let stream = null;
        let captureInterval = null;
        let activeStudentId = null;
        let tabAwayCount = 0;
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const video = document.createElement('video');

        // AI sites to look for in the title bar of captured screenshots
        // (we can't get URL from getDisplayMedia, but we CAN read the
        //  page title from the shared tab's document.title via the
        //  browser tab bar visible in the screenshot — however the
        //  reliable method is tab visibility detection below)

        async function startSharing() {
            const idInput = document.getElementById('studentId');
            const studentId = idInput.value.trim();
            if (!studentId) { idInput.focus(); return; }
            activeStudentId = studentId;

            document.getElementById('joinBtn').disabled = true;
            document.getElementById('status').textContent = 'Requesting screen access...';

            try {
                stream = await navigator.mediaDevices.getDisplayMedia({
                    video: { cursor: 'always' },
                    audio: false
                });

                video.srcObject = stream;
                await video.play();

                // Show active state
                document.getElementById('setupForm').style.display = 'none';
                document.getElementById('activeView').style.display = '';
                document.getElementById('intro').textContent = 'Student: ' + studentId;
                document.getElementById('status').textContent = '';
                document.getElementById('preview').style.display = '';

                // Handle user stopping share via browser UI
                stream.getVideoTracks()[0].onended = () => stopSharing();

                // Capture and send every 4 seconds
                captureAndSend(studentId);
                captureInterval = setInterval(() => captureAndSend(studentId), 4000);

            } catch (err) {
                document.getElementById('status').className = 'status error';
                document.getElementById('status').textContent = 'Screen share was denied or cancelled.';
                document.getElementById('joinBtn').disabled = false;
            }
        }

        // Detect when student leaves this tab (switches to another app/tab)
        document.addEventListener('visibilitychange', function() {
            if (!activeStudentId || !stream) return;

            if (document.hidden) {
                tabAwayCount++;
                // Student left the exam tab — capture what they see and flag it
                sendFlag(activeStudentId, 'TAB_SWITCH', 'Student left exam tab (switch #' + tabAwayCount + ')');
            }
        });

        // Also detect window blur (catches Alt-Tab, clicking other windows)
        window.addEventListener('blur', function() {
            if (!activeStudentId || !stream) return;
            tabAwayCount++;
            sendFlag(activeStudentId, 'FOCUS_LOST', 'Student switched away from exam (switch #' + tabAwayCount + ')');
        });

        async function sendFlag(studentId, flagType, detail) {
            // Capture current screenshot for evidence
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
                        domain: flagType,
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

        async function captureAndSend(studentId) {
            if (!stream || !stream.active) return;

            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            ctx.drawImage(video, 0, 0);

            const screenshot = canvas.toDataURL('image/jpeg', 0.5);

            // Show preview
            document.getElementById('previewImg').src = screenshot;

            try {
                await fetch('/live-update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        studentId: studentId,
                        screenshot: screenshot,
                        currentUrl: 'screen-share://browser',
                        currentTitle: 'Screen Share',
                        timestamp: new Date().toISOString(),
                        type: 'LIVE_UPDATE'
                    })
                });
            } catch (e) {
                console.error('Failed to send update:', e);
            }
        }

        function stopSharing() {
            if (captureInterval) clearInterval(captureInterval);
            if (stream) stream.getTracks().forEach(t => t.stop());
            stream = null;
            activeStudentId = null;

            document.getElementById('setupForm').style.display = '';
            document.getElementById('activeView').style.display = 'none';
            document.getElementById('joinBtn').disabled = false;
            document.getElementById('intro').textContent = 'Enter your student ID and share your screen to join the monitored exam session.';
            document.getElementById('status').className = 'status';
            document.getElementById('status').textContent = 'Screen sharing stopped.';
            document.getElementById('preview').style.display = 'none';
        }

        // Enter key triggers join
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
        .topbar-left img {
            height: 24px;
            width: auto;
            flex-shrink: 0;
        }
        .topbar-left .sep {
            width: 1px;
            height: 20px;
            background: #ddd;
            flex-shrink: 0;
        }
        .topbar h1 {
            font-size: 14px;
            font-weight: 600;
            color: #222;
            white-space: nowrap;
        }
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
        @keyframes livepulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .main { padding: 16px 20px; }

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
        .tile:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-color: #bbb;
        }
        .tile.flagged {
            border-color: #d63031;
            border-width: 2px;
        }
        .tile-screen {
            width: 100%;
            aspect-ratio: 16/10;
            background: #eee;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        .tile-screen img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .tile-screen .empty {
            color: #bbb;
            font-size: 12px;
        }
        .tile-info {
            padding: 8px 10px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-top: 1px solid #f0f0f0;
        }
        .indicator {
            width: 8px; height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
            background: #b2bec3;
        }
        .indicator.red { background: #d63031; }
        .tile-text { flex: 1; min-width: 0; }
        .tile-id {
            font-weight: 600;
            font-size: 12px;
            color: #222;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tile-meta {
            font-size: 11px;
            color: #888;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-top: 1px;
        }
        .tile-violations {
            font-size: 11px;
            color: #d63031;
            font-weight: 700;
            flex-shrink: 0;
            background: #ffeaea;
            padding: 2px 7px;
            border-radius: 8px;
        }
        .empty-state {
            text-align: center;
            padding: 80px 20px;
            color: #999;
            font-size: 14px;
        }

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
        .modal-box img {
            display: block;
            max-width: 90vw;
            max-height: calc(90vh - 48px);
            object-fit: contain;
        }
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
            width: 640px;
            height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #bbb;
            font-size: 14px;
            background: #f5f5f5;
        }
    </style>
</head>
<body>
    <div class="topbar">
        <div class="topbar-left">
            <img src="/scc-logo.svg" alt="St. Clair College">
            <div class="sep"></div>
            <h1>Exam Monitor</h1>
        </div>
        <div class="topbar-stats">
            <span><strong id="sOnline">0</strong> students</span>
            <span><strong id="sViolations">0</strong> violations</span>
            <span><span class="dot-live"></span>Live</span>
        </div>
    </div>

    <div class="main">
        <div class="grid" id="grid"></div>
        <div class="empty-state" id="empty">Waiting for students to connect...</div>
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
        let violationCount = 0;
        let modalStudentId = null;

        const eventSource = new EventSource('/stream');
        eventSource.onmessage = function(e) {
            const msg = JSON.parse(e.data);
            if (msg.type === 'new_flag') handleFlag(msg.data);
            else if (msg.type === 'live_screen_update') handleLive(msg.studentId, msg.data);
        };

        async function loadInitial() {
            try {
                const res = await fetch('/live-screens');
                const screens = await res.json();
                Object.keys(screens).forEach(id => handleLive(id, screens[id]));
            } catch(e) {}
        }

        function handleLive(id, data) {
            if (!students[id]) {
                students[id] = { id: id, status: 'safe', violations: 0, site: '', screenshot: null };
            }
            students[id].screenshot = data.screenshot;
            students[id].site = extractDomain(data.currentUrl);
            render();
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
            render();
            if (modalStudentId === id) updateModal(id);
            setTimeout(() => { if (students[id]) { students[id].status = 'warning'; render(); } }, 8000);
        }

        function extractDomain(url) {
            try { return new URL(url).hostname.replace('www.', ''); } catch { return ''; }
        }

        function openModal(id) {
            modalStudentId = id;
            updateModal(id);
            document.getElementById('modal').classList.add('open');
        }

        function updateModal(id) {
            const s = students[id];
            if (!s) return;
            document.getElementById('modalId').textContent = s.id;
            document.getElementById('modalSite').textContent = s.site || 'idle';
            const container = document.getElementById('modalScreen');
            if (s.screenshot) {
                container.innerHTML = '<img src="' + s.screenshot + '">';
            } else {
                container.innerHTML = '<div class="modal-no-screen">No screen available</div>';
            }
        }

        function closeModal() {
            modalStudentId = null;
            document.getElementById('modal').classList.remove('open');
        }

        document.getElementById('modal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeModal();
        });

        function render() {
            const grid = document.getElementById('grid');
            const empty = document.getElementById('empty');
            const ids = Object.keys(students);

            document.getElementById('sOnline').textContent = ids.length;
            document.getElementById('sViolations').textContent = violationCount;

            if (ids.length === 0) { empty.style.display = ''; grid.innerHTML = ''; return; }
            empty.style.display = 'none';

            grid.innerHTML = ids.map(id => {
                const s = students[id];
                const flagged = s.status === 'flagged';
                return '<div class="tile' + (flagged ? ' flagged' : '') + '" onclick="openModal(\\'' + id + '\\')">'
                    + '<div class="tile-screen">'
                    + (s.screenshot ? '<img src="' + s.screenshot + '">' : '<span class="empty">No screen yet</span>')
                    + '</div>'
                    + '<div class="tile-info">'
                    + '<div class="indicator' + (flagged ? ' red' : '') + '"></div>'
                    + '<div class="tile-text">'
                    + '<div class="tile-id">' + s.id + '</div>'
                    + '<div class="tile-meta">' + (s.site || 'idle') + '</div>'
                    + '</div>'
                    + (s.violations > 0 ? '<div class="tile-violations">' + s.violations + '</div>' : '')
                    + '</div></div>';
            }).join('');
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
