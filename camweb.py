#!/usr/bin/env python3
from flask import Flask, Response, send_from_directory
import subprocess
from datetime import datetime
from pathlib import Path
import time

app = Flask(__name__)
CAM_DIR = Path.home() / "recordings"
CAM_DIR.mkdir(exist_ok=True)

@app.route("/")
def index():
    files = []
    for ext in ["*.jpg", "*.mp4"]:
        files.extend(list(CAM_DIR.glob(ext)))
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    gallery_html = ""
    for f in files[:20]:
        name = f.name
        if f.suffix == ".jpg":
            gallery_html += f'<div class="item"><img src="/file/{name}" onclick="window.open(this.src)"><div class="fname">{name}</div><button class="delbtn" onclick="deleteFile(\'{name}\')">DELETE</button></div>'
        else:
            gallery_html += f'<div class="item"><video controls width="200"><source src="/file/{name}"></video><div class="fname">{name}</div><button class="delbtn" onclick="deleteFile(\'{name}\')">DELETE</button></div>'
    
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>Pi Camera</title>
    <style>
        body {{ font-family: sans-serif; background: #1a1a2e; color: #fff; padding: 20px; text-align: center; }}
        h1 {{ color: #0f9; }}
        #preview {{ max-width: 100%; max-height: 400px; border: 2px solid #333; }}
        .btn {{ padding: 15px 30px; font-size: 18px; margin: 10px; border: none; border-radius: 8px; cursor: pointer; }}
        .green {{ background: #0f9; color: #000; }}
        .red {{ background: #f55; color: #fff; }}
        .blue {{ background: #59f; color: #fff; }}
        #msg {{ padding: 15px; margin: 15px; font-size: 18px; }}
        .gallery {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; margin-top: 20px; }}
        .item {{ background: #2a2a4e; padding: 10px; border-radius: 8px; }}
        .item img {{ width: 200px; cursor: pointer; border-radius: 4px; }}
        .fname {{ font-size: 11px; color: #888; margin: 5px 0; word-break: break-all; }}
        .delbtn {{ background: #f33; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; width: 100%; }}
        .delbtn:hover {{ background: #d00; }}
    </style>
</head>
<body>
    <h1>Pi Camera</h1>
    <img id="preview" src="/preview?t={int(time.time())}">
    <div id="msg"></div>
    <div>
        <button class="btn green" onclick="snap()">SNAP PHOTO</button>
        <button class="btn red" onclick="record()">RECORD 10s</button>
        <button class="btn blue" onclick="location.reload()">REFRESH</button>
    </div>
    <h2>Gallery</h2>
    <div class="gallery">{gallery_html}</div>
    <script>
        setInterval(function() {{ document.getElementById("preview").src = "/preview?t=" + Date.now(); }}, 2000);
        
        function snap() {{
            document.getElementById("msg").innerHTML = "Taking photo...";
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/snap", true);
            xhr.onload = function() {{ document.getElementById("msg").innerHTML = xhr.responseText; setTimeout(function() {{ location.reload(); }}, 1000); }};
            xhr.send();
        }}
        
        function record() {{
            document.getElementById("msg").innerHTML = "Recording 10 seconds...";
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/record", true);
            xhr.onload = function() {{ document.getElementById("msg").innerHTML = xhr.responseText; setTimeout(function() {{ location.reload(); }}, 1000); }};
            xhr.send();
        }}
        
        function deleteFile(name) {{
            if (!confirm("Delete " + name + "?")) return;
            document.getElementById("msg").innerHTML = "Deleting...";
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/delete/" + encodeURIComponent(name), true);
            xhr.onload = function() {{ document.getElementById("msg").innerHTML = xhr.responseText; setTimeout(function() {{ location.reload(); }}, 500); }};
            xhr.send();
        }}
    </script>
</body>
</html>'''

@app.route("/preview")
def preview():
    result = subprocess.run(["rpicam-still", "-t", "300", "--width", "640", "--height", "480", "-o", "-", "-n"], capture_output=True, timeout=5)
    return Response(result.stdout, mimetype="image/jpeg")

@app.route("/snap")
def snap():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = CAM_DIR / f"photo_{ts}.jpg"
    subprocess.run(["rpicam-still", "-t", "500", "--width", "1920", "--height", "1080", "-o", str(path), "-n"], timeout=10)
    if path.exists():
        return f"Saved: {path.name}"
    return "Failed"

@app.route("/record")
def record():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    h264 = CAM_DIR / f"video_{ts}.h264"
    mp4 = CAM_DIR / f"video_{ts}.mp4"
    subprocess.run(["rpicam-vid", "-t", "10000", "--width", "1920", "--height", "1080", "-o", str(h264), "-n"], timeout=20)
    if h264.exists():
        subprocess.run(["ffmpeg", "-y", "-i", str(h264), "-c", "copy", str(mp4)], capture_output=True, timeout=30)
        if mp4.exists():
            h264.unlink()
            return f"Saved: {mp4.name}"
    return "Failed"

@app.route("/delete/<name>")
def delete(name):
    path = CAM_DIR / name
    if path.exists() and path.parent == CAM_DIR:
        path.unlink()
        return f"Deleted: {name}"
    return "Not found"

@app.route("/file/<name>")
def get_file(name):
    return send_from_directory(CAM_DIR, name)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
