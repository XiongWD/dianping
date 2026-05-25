"""
大众点评脚本 Web IDE
浏览器打开 http://192.168.0.107:8092
可以直接编辑、保存、推送到手机
"""
import http.server
import json
import os
import socket
import struct
import cgi
from urllib.parse import parse_qs

PORT = 8092
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mobile")
SCRIPTS_DIR = os.path.abspath(SCRIPTS_DIR)
DEVICE_HOST = "192.168.0.109"
DEVICE_PORT = 7347

HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>大众点评 - 脚本编辑器</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: monospace; background: #1e1e1e; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; }
.header { background: #2d2d2d; padding: 10px 15px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid #444; }
.header select, .header button { padding: 6px 12px; border: 1px solid #555; background: #3d3d3d; color: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; }
.header button:hover { background: #505050; }
.header .push { background: #0e639c; border-color: #1177bb; }
.header .push:hover { background: #1177bb; }
.header .run { background: #388a34; border-color: #45a049; }
.header .run:hover { background: #45a049; }
.header .status { margin-left: auto; font-size: 12px; color: #888; }
.files { display: flex; gap: 5px; padding: 5px 15px; background: #252526; }
.files button { padding: 4px 10px; border: 1px solid #444; background: #2d2d2d; color: #ccc; border-radius: 3px; cursor: pointer; font-size: 12px; }
.files button.active { background: #1e1e1e; border-bottom: 2px solid #007acc; color: #fff; }
textarea { flex: 1; background: #1e1e1e; color: #d4d4d4; border: none; padding: 15px; font-family: 'Consolas', monospace; font-size: 14px; resize: none; outline: none; line-height: 1.5; }
.log { height: 120px; background: #1a1a1a; border-top: 1px solid #444; padding: 8px 15px; overflow-y: auto; font-size: 12px; color: #6a9955; }
.log .err { color: #f44747; }
.log .info { color: #569cd6; }
</style></head>
<body>
<div class="header">
    <span style="font-size:16px;font-weight:bold;">📌 大众点评脚本</span>
    <button class="push" onclick="pushToDevice()">推送所有到手机</button>
    <button class="run" onclick="runOnDevice()">在手机上运行</button>
    <button onclick="saveCurrent()">保存</button>
    <span class="status" id="status">就绪</span>
</div>
<div class="files" id="fileTabs"></div>
<textarea id="editor" spellcheck="false"></textarea>
<div class="log" id="log"></div>
<script>
const SCRIPTS_DIR = '/api/files';
let currentFile = '';
let files = {};

function log(msg, cls) {
    const el = document.getElementById('log');
    const line = document.createElement('div');
    if (cls) line.className = cls;
    line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
    el.appendChild(line);
    el.scrollTop = el.scrollHeight;
}

async function loadFileList() {
    const resp = await fetch('/api/list');
    const data = await resp.json();
    const tabs = document.getElementById('fileTabs');
    tabs.innerHTML = '';
    data.files.forEach(f => {
        const btn = document.createElement('button');
        btn.textContent = f;
        if (f === currentFile) btn.className = 'active';
        btn.onclick = () => openFile(f);
        tabs.appendChild(btn);
    });
}

async function openFile(name) {
    if (currentFile && files[currentFile] !== undefined) {
        files[currentFile] = document.getElementById('editor').value;
    }
    if (!files[name]) {
        const resp = await fetch('/api/file?name=' + encodeURIComponent(name));
        const data = await resp.json();
        files[name] = data.content || '';
    }
    currentFile = name;
    document.getElementById('editor').value = files[name];
    loadFileList();
    log('打开: ' + name, 'info');
}

async function saveCurrent() {
    if (!currentFile) return;
    files[currentFile] = document.getElementById('editor').value;
    const resp = await fetch('/api/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: currentFile, content: files[currentFile]})
    });
    const data = await resp.json();
    log('已保存: ' + currentFile, 'info');
}

async function pushToDevice() {
    await saveCurrent();
    const resp = await fetch('/api/push');
    const data = await resp.json();
    if (data.ok) {
        log('推送成功! ' + (data.details || ''), 'info');
    } else {
        log('推送失败: ' + (data.error || ''), 'err');
    }
}

async function runOnDevice() {
    await saveCurrent();
    const resp = await fetch('/api/run?file=' + encodeURIComponent(currentFile));
    const data = await resp.json();
    if (data.ok) {
        log('运行命令已发送: ' + currentFile, 'info');
    } else {
        log('运行失败: ' + (data.error || ''), 'err');
    }
}

loadFileList();
if (!currentFile) openFile('main.js');

// Ctrl+S 保存
document.onkeydown = function(e) {
    if (e.ctrlKey && e.key === 's') { e.preventDefault(); saveCurrent(); }
};
</script>
</body></html>"""


class IDEHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self._html(HTML)
        elif self.path == '/api/list':
            fs = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.js')]
            self._json({"files": sorted(fs)})
        elif self.path.startswith('/api/file?'):
            qs = parse_qs(self.path.split('?', 1)[1])
            name = qs.get('name', [''])[0]
            if not name or '..' in name or '/' in name:
                return self._json({"error": "bad name"}, 400)
            path = os.path.join(SCRIPTS_DIR, name)
            content = open(path, 'r', encoding='utf-8').read() if os.path.exists(path) else ''
            self._json({"name": name, "content": content})
        elif self.path.startswith('/api/push'):
            self._do_push()
        elif self.path.startswith('/api/run?'):
            qs = parse_qs(self.path.split('?', 1)[1])
            name = qs.get('file', ['main.js'])[0]
            self._do_run(name)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path == '/api/save':
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length))
            name = data.get('name', '')
            if not name or '..' in name or '/' in name:
                return self._json({"error": "bad name"}, 400)
            path = os.path.join(SCRIPTS_DIR, name)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(data.get('content', ''))
            self._json({"ok": True, "name": name})
        else:
            self._json({"error": "not found"}, 404)

    def _do_push(self):
        """推送所有 js 文件到手机"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((DEVICE_HOST, DEVICE_PORT))

            # 握手
            self._send_json(sock, {"type": "hello", "id": 1, "data": {"name": "WebIDE"}})
            sock.settimeout(3)
            try:
                self._recv_frame(sock)
            except:
                pass

            # 推送所有文件
            pushed = []
            for fname in sorted(os.listdir(SCRIPTS_DIR)):
                if not fname.endswith('.js'):
                    continue
                path = os.path.join(SCRIPTS_DIR, fname)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._send_json(sock, {
                    "type": "command", "id": 10,
                    "data": {"\xa0cmd\xa0": "save", "path": fname, "content": content}
                })
                pushed.append(fname)

            sock.close()
            self._json({"ok": True, "details": f"{len(pushed)} files: {', '.join(pushed)}"})
        except Exception as e:
            self._json({"ok": False, "error": str(e)})

    def _do_run(self, fname):
        """在手机上运行脚本"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((DEVICE_HOST, DEVICE_PORT))
            self._send_json(sock, {"type": "hello", "id": 1, "data": {"name": "WebIDE"}})
            sock.settimeout(2)
            try:
                self._recv_frame(sock)
            except:
                pass
            self._send_json(sock, {
                "type": "command", "id": 20,
                "data": {"\xa0cmd\xa0": "run", "path": fname}
            })
            sock.close()
            self._json({"ok": True})
        except Exception as e:
            self._json({"ok": False, "error": str(e)})

    def _send_json(self, sock, data):
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        header = struct.pack('>ii', len(payload), 1)
        sock.sendall(header + payload)

    def _recv_frame(self, sock):
        header = self._recv_exact(sock, 8)
        length, dtype = struct.unpack('>ii', header)
        if length > 1048576:
            raise ValueError(f"frame too large: {length}")
        payload = self._recv_exact(sock, length)
        if dtype == 1:
            return json.loads(payload.decode('utf-8'))
        return None

    def _recv_exact(self, sock, n):
        buf = b''
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError()
            buf += chunk
        return buf

    def _html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), IDEHandler)
    print(f'Web IDE 运行在 http://192.168.0.107:{PORT}')
    print('手机浏览器打开即可编辑脚本 + 推送到手机 + 运行')
    server.serve_forever()
