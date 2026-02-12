#!/usr/bin/env python3
"""
Camera Web Server - Live view + controls + gallery
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Flask, Response, render_template_string, jsonify, send_from_directory

app = Flask(__name__)

CAM_DIR = Path.home() / "recordings"
CAM_DIR.mkdir(exist_ok=True)

stream_process = None

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Pi Camera</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #eee; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { text-align: center; margin-bottom: 20px; color: #00d4ff; }
        h2 { margin: 20px 0 10px; color: #00d4ff; font-size: 1.2em; }

        .live-section { text-align: center; margin-bottom: 20px; }
        #stream { max-width: 100%; border-radius: 8px; background: #000; min-height: 300px; }

        .controls { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin: 20px 0; }
        button {
            padding: 12px 24px; font-size: 16px; border: none; border-radius: 6px;
            cursor: pointer; transition: all 0.2s; font-weight: 600;
        }
        .btn-primary { background: #00d4ff; color: #000; }
        .btn-success { background: #00ff88; color: #000; }
        .btn-danger { background: #ff4757; color: #fff; }
        .btn-secondary { background: #444; color: #fff; }
        button:hover { transform: scale(1.05); opacity: 0.9; }
        button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

        input[type="number"] {
            width: 60px; padding: 10px; border-radius: 6px; border: none;
            background: #333; color: #fff; text-align: center;
        }

        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
        .gallery-item {
            background: #2a2a4a; border-radius: 8px; overflow: hidden;
            transition: transform 0.2s;
        }
        .gallery-item:hover { transform: scale(1.02); }
        .gallery-item img, .gallery-item video { width: 100%; height: 150px; object-fit: cover; }
        .gallery-item .info { padding: 10px; font-size: 12px; }
        .gallery-item .name { color: #00d4ff; word-break: break-all; }
        .gallery-item .meta { color: #888; margin-top: 5px; }
        .gallery-item .actions { margin-top: 8px; display: flex; gap: 5px; }
        .gallery-item .actions button { padding: 5px 10px; font-size: 12px; }

        .tabs { display: flex; gap: 10px; margin-bottom: 15px; }
        .tab { padding: 10px 20px; background: #333; border-radius: 6px; cursor: pointer; }
        .tab.active { background: #00d4ff; color: #000; }

        .status { text-align: center; padding: 10px; background: #333; border-radius: 6px; margin: 10px 0; }
        .status.recording { background: #ff4757; animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }

        .empty { text-align: center; padding: 40px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Pi Camera</h1>

        <div id="status" class="status">Ready</div>

        <div class="live-section">
            <img id="stream" src="/stream" alt="Live Stream">
        </div>

        <div class="controls">
            <button class="btn-primary" onclick="snap()">Snap</button>
            <button class="btn-success" onclick="record()">Record</button>
            <input type="number" id="duration" value="10" min="1" max="3600"> sec
            <button class="btn-danger" id="startBtn" onclick="startContinuous()">Start</button>
            <button class="btn-secondary" id="stopBtn" onclick="stopRecording()" disabled>Stop</button>
            <button class="btn-secondary" onclick="refreshGallery()">Refresh</button>
        </div>

        <h2>Recordings</h2>
        <div class="tabs">
            <div class="tab active" onclick="showTab(this, 'all')">All</div>
            <div class="tab" onclick="showTab(this, 'photos')">Photos</div>
            <div class="tab" onclick="showTab(this, 'videos')">Videos</div>
        </div>
        <div id="gallery" class="gallery"></div>
    </div>

    <script>
        let currentTab = 'all';

        async function api(endpoint, method) {
            method = method || 'POST';
            const res = await fetch('/api/' + endpoint, {method: method});
            return res.json();
        }

        function setStatus(msg, isRecording) {
            const el = document.getElementById('status');
            el.textContent = msg;
            el.className = 'status' + (isRecording ? ' recording' : '');
        }

        async function snap() {
            setStatus('Capturing...');
            const data = await api('snap');
            setStatus(data.message);
            refreshGallery();
        }

        async function record() {
            const dur = document.getElementById('duration').value;
            setStatus('Recording ' + dur + 's...', true);
            const data = await api('record/' + dur);
            setStatus(data.message);
            refreshGallery();
        }

        async function startContinuous() {
            setStatus('Recording...', true);
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            await api('start');
        }

        async function stopRecording() {
            setStatus('Stopping...');
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            const data = await api('stop');
            setStatus(data.message);
            refreshGallery();
        }

        function showTab(el, tab) {
            currentTab = tab;
            document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
            el.classList.add('active');
            refreshGallery();
        }

        async function refreshGallery() {
            const data = await api('list', 'GET');
            const gallery = document.getElementById('gallery');

            let files = data.files;
            if (currentTab === 'photos') files = files.filter(function(f) { return f.type === 'photo'; });
            if (currentTab === 'videos') files = files.filter(function(f) { return f.type === 'video'; });

            if (files.length === 0) {
                gallery.innerHTML = '<div class="empty">No recordings yet</div>';
                return;
            }

            gallery.innerHTML = files.map(function(f) {
                if (f.type === 'photo') {
                    return '<div class="gallery-item">' +
                        '<img src="/media/' + f.name + '" loading="lazy">' +
                        '<div class="info">' +
                        '<div class="name">' + f.name + '</div>' +
                        '<div class="meta">' + f.size + ' - ' + f.date + '</div>' +
                        '<div class="actions">' +
                        '<a href="/media/' + f.name + '" download><button class="btn-secondary">Download</button></a>' +
                        '<button class="btn-danger" onclick="deleteFile(\'' + f.name + '\')">Delete</button>' +
                        '</div></div></div>';
                } else {
                    return '<div class="gallery-item">' +
                        '<video src="/media/' + f.name + '" controls preload="metadata"></video>' +
                        '<div class="info">' +
                        '<div class="name">' + f.name + '</div>' +
                        '<div class="meta">' + f.size + ' - ' + f.date + '</div>' +
                        '<div class="actions">' +
                        '<a href="/media/' + f.name + '" download><button class="btn-secondary">Download</button></a>' +
                        '<button class="btn-danger" onclick="deleteFile(\'' + f.name + '\')">Delete</button>' +
                        '</div></div></div>';
                }
            }).join('');
        }

        async function deleteFile(name) {
            if (confirm('Delete ' + name + '?')) {
                await api('delete/' + name);
                refreshGallery();
            }
        }

        async function checkStatus() {
            const data = await api('status', 'GET');
            if (data.recording) {
                setStatus('Recording...', true);
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
            }
        }

        refreshGallery();
        checkStatus();
    </script>
</body>
</html>
'''

def gen_frames():
    """Generate MJPEG stream frames"""
    process = subprocess.Popen([
        'rpicam-vid', '-t', '0', '--width', '640', '--height', '480',
        '--framerate', '15', '--codec', 'mjpeg', '-o', '-', '-v', '0'
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    try:
        data = b''
        while True:
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            data += chunk
            while b'\xff\xd9' in data:
                idx = data.index(b'\xff\xd9') + 2
                frame = data[:idx]
                data = data[idx:]
                # Find start of JPEG
                if b'\xff\xd8' in frame:
                    start = frame.index(b'\xff\xd8')
                    frame = frame[start:]
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        process.terminate()

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/stream')
def stream():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/media/<path:filename>')
def media(filename):
    return send_from_directory(CAM_DIR, filename)

@app.route('/api/snap', methods=['POST'])
def api_snap():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = CAM_DIR / f'photo_{ts}.jpg'
    subprocess.run(['rpicam-still', '-t', '500', '--width', '1920', '--height', '1080',
                   '-o', str(path), '-v', '0'], capture_output=True)
    return jsonify({'message': f'Saved: {path.name}', 'file': path.name})

@app.route('/api/record/<int:duration>', methods=['POST'])
def api_record(duration):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    h264 = CAM_DIR / f'video_{ts}.h264'
    mp4 = CAM_DIR / f'video_{ts}.mp4'

    subprocess.run(['rpicam-vid', '-t', str(duration * 1000), '--width', '1920', '--height', '1080',
                   '--framerate', '30', '-o', str(h264), '-v', '0'], capture_output=True)
    subprocess.run(['ffmpeg', '-y', '-framerate', '30', '-i', str(h264), '-c', 'copy', str(mp4), '-v', 'quiet'])
    if h264.exists():
        h264.unlink()

    return jsonify({'message': f'Saved: {mp4.name}', 'file': mp4.name})

@app.route('/api/start', methods=['POST'])
def api_start():
    global stream_process
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    stream_process = subprocess.Popen([
        'rpicam-vid', '-t', '0', '--width', '1920', '--height', '1080', '--framerate', '30',
        '--segment', '600000', '-o', str(CAM_DIR / f'video_{ts}_%04d.h264'), '-v', '0'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({'message': 'Recording started'})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    global stream_process
    if stream_process:
        stream_process.terminate()
        stream_process = None
    # Convert h264 files
    for h264 in CAM_DIR.glob('*.h264'):
        mp4 = h264.with_suffix('.mp4')
        subprocess.run(['ffmpeg', '-y', '-framerate', '30', '-i', str(h264), '-c', 'copy', str(mp4), '-v', 'quiet'])
        h264.unlink()
    return jsonify({'message': 'Recording stopped'})

@app.route('/api/status', methods=['GET'])
def api_status():
    global stream_process
    recording = stream_process is not None and stream_process.poll() is None
    return jsonify({'recording': recording})

@app.route('/api/list', methods=['GET'])
def api_list():
    files = []
    for f in sorted(CAM_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix in ['.jpg', '.mp4']:
            stat = f.stat()
            size = f'{stat.st_size / 1024 / 1024:.1f}MB' if stat.st_size > 1024*1024 else f'{stat.st_size / 1024:.0f}KB'
            files.append({
                'name': f.name,
                'type': 'photo' if f.suffix == '.jpg' else 'video',
                'size': size,
                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
            })
    return jsonify({'files': files})

@app.route('/api/delete/<filename>', methods=['POST'])
def api_delete(filename):
    path = CAM_DIR / filename
    if path.exists() and path.parent == CAM_DIR:
        path.unlink()
        return jsonify({'message': 'Deleted'})
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    print("Camera Web Server starting on http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, threaded=True)
