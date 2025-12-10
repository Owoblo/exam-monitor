from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS
from datetime import datetime
import base64
import json
import time
import queue

app = Flask(__name__)
CORS(app)

# Store flags in memory (use database later)
flags = []

# Store live screenshots for each student
live_screens = {}  # {studentId: {screenshot, url, timestamp}}

# Queue for real-time updates (SSE)
update_queue = queue.Queue()

@app.route('/flag', methods=['POST'])
def receive_flag():
    data = request.json
    data['received_at'] = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
    flags.append(data)
    print(f"🚨 FLAG: Student {data['studentId']} accessed {data['domain']} at {data['received_at']}")

    # Push to SSE queue for real-time updates
    update_queue.put({
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

    # Push update via SSE
    update_queue.put({
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
    """Server-Sent Events endpoint for real-time updates"""
    def event_stream():
        while True:
            try:
                # Wait for new updates (timeout after 30 seconds to send heartbeat)
                message = update_queue.get(timeout=30)
                yield f"data: {json.dumps(message)}\n\n"
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

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
                <a href="/demo" style="background: #00843D;">🎯 DEMO (Recommended)</a>
                <a href="/grid" class="grid-link">📹 Grid View</a>
                <a href="/dashboard">📊 List Dashboard</a>
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
    print("🚀 ST. CLAIR COLLEGE - EXAM INTEGRITY MONITOR")
    print("=" * 60)
    print(f"🎯 DEMO (Recommended): http://localhost:{port}/demo")
    print(f"📹 Grid View: http://localhost:{port}/grid")
    print(f"📊 List Dashboard: http://localhost:{port}/dashboard")
    print(f"🔌 API Endpoint: http://localhost:{port}/flag")
    print("=" * 60)
    print("✅ Server is running and waiting for flags...\n")
    app.run(debug=debug, host='0.0.0.0', port=port)
