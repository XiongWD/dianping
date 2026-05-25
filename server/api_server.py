"""
大众点评内容工厂 — HTTP API 服务
供手机端 AutoJs6 拉取内容 + 上报结果 + 截图分析
"""
import json
import os
import cgi
import uuid
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from content_pack import get_pending_packs, update_pack_status, batch_generate

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = BASE_DIR / "logs"
SCREENSHOT_DIR = BASE_DIR / "output" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class DianpingAPIHandler(BaseHTTPRequestHandler):
    """HTTP API"""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/api/packs":
            limit = int(params.get("limit", ["5"])[0])
            packs = get_pending_packs(limit=limit)
            self._json_response({
                "count": len(packs),
                "packs": packs
            })

        elif parsed.path == "/api/status":
            packs = get_pending_packs(limit=100)
            self._json_response({
                "status": "ok",
                "pending_count": len(packs),
                "time": datetime.now().isoformat()
            })

        elif parsed.path == "/api/generate":
            count = int(params.get("count", ["15"])[0])
            pack_ids = batch_generate(count)
            self._json_response({
                "generated": len(pack_ids),
                "pack_ids": pack_ids
            })

        elif parsed.path.startswith("/api/screenshots/"):
            # 查看截图
            filename = parsed.path.split("/")[-1]
            filepath = SCREENSHOT_DIR / filename
            if filepath.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._json_response({"error": "not found"}, 404)

        else:
            self._json_response({"error": "unknown endpoint"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/report":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            pack_id = data.get("pack_id")
            status = data.get("status", "published")
            result = data.get("result", {})

            if pack_id:
                update_pack_status(pack_id, status, result)
                self._json_response({"ok": True, "pack_id": pack_id})
            else:
                self._json_response({"error": "missing pack_id"}, 400)

        elif parsed.path == "/api/eyes":
            # 接收手机截图 + 控件dump
            self._handle_eyes()

        elif parsed.path == "/api/explore":
            # 探索模式数据接收
            self._handle_explore()
        else:
            self._json_response({"error": "unknown endpoint"}, 404)

    def _handle_eyes(self):
        """处理截图上传"""
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))

        if "multipart/form-data" not in content_type:
            # 简单 JSON 模式
            body = self.rfile.read(content_length)
            data = json.loads(body)
            desc = data.get("description", "unknown")
            ui_tree = data.get("ui_tree", "")
            self._json_response({
                "ok": True,
                "summary": f"收到控件数据 ({len(ui_tree)} chars), 无截图",
                "screenshot_url": None,
            })
            return

        # multipart 解析
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            }
        )

        desc = form.getvalue("description", "unknown")
        ui_tree = form.getvalue("ui_tree", "")

        # 保存截图
        screenshot_url = None
        file_item = form["screenshot"] if "screenshot" in form else None
        if file_item and file_item.filename:
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.png"
            filepath = SCREENSHOT_DIR / filename
            with open(filepath, "wb") as f:
                f.write(file_item.file.read())
            screenshot_url = f"/api/screenshots/{filename}"
            print(f"[eyes] 截图已保存: {filename} (desc: {desc})")

        # 解析控件树
        node_count = 0
        if ui_tree:
            try:
                nodes = json.loads(ui_tree)
                node_count = len(nodes)
                print(f"[eyes] 控件节点: {node_count}")
                # 打印关键控件
                for n in nodes[:20]:
                    txt = n.get("text", "")
                    dsc = n.get("desc", "")
                    if txt or dsc:
                        print(f"  [{n.get('className','')}] text={txt} desc={dsc} clickable={n.get('clickable')} bounds={n.get('bounds')}")
            except:
                pass

        self._json_response({
            "ok": True,
            "summary": f"截图已保存, {node_count} 个控件节点",
            "screenshot_url": screenshot_url,
            "description": desc,
        })

    def _handle_explore(self):
        """处理探索模式数据"""
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))

        if "multipart/form-data" not in content_type:
            body = self.rfile.read(content_length)
            data = json.loads(body)
            self._json_response({"ok": True, "msg": "json only"})
            return

        form = cgi.FieldStorage(
            fp=self.rfile, headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type}
        )

        action = form.getvalue("action", "unknown")
        activity = form.getvalue("activity", "")
        ui_json = form.getvalue("ui_json", "[]")
        ts = form.getvalue("ts", "0")

        # 保存截图
        filename = f"explore_{ts}_{uuid.uuid4().hex[:4]}.png"
        filepath = SCREENSHOT_DIR / filename
        file_item = form["screen"] if "screen" in form else None
        if file_item and hasattr(file_item, 'file'):
            with open(filepath, "wb") as f:
                f.write(file_item.file.read())

        # 解析节点
        nodes = []
        try:
            nodes = json.loads(ui_json)
        except:
            pass

        # 记录到探索日志
        explore_log = LOG_DIR / "explore_log.jsonl"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": ts,
            "action": action,
            "activity": activity,
            "screenshot": filename,
            "node_count": len(nodes),
            "nodes": nodes[:50],  # 只保存前50个关键节点
        }
        with open(explore_log, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        print(f"[explore] {action} | {activity} | {len(nodes)} nodes | {filename}")

        self._json_response({"ok": True, "frame": filename})

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def run_server(host="0.0.0.0", port=8090):
    server = HTTPServer((host, port), DianpingAPIHandler)
    print(f"大众点评内容工厂 API 运行在 http://{host}:{port}")
    print(f"  GET  /api/packs           — 获取待发布内容")
    print(f"  GET  /api/status          — 服务状态")
    print(f"  GET  /api/generate        — 触发批量生成")
    print(f"  POST /api/report          — 上报发布结果")
    print(f"  POST /api/eyes            — 截图+控件分析")
    print(f"  GET  /api/screenshots/xxx — 查看截图")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    run_server(port=port)
