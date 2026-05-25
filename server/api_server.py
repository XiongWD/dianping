"""
大众点评内容工厂 — HTTP API 服务
供手机端 AutoX.js 拉取内容 + 上报结果
"""
import json
import os
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from content_pack import get_pending_packs, update_pack_status, batch_generate

BASE_DIR = Path(os.path.dirname(os.path.dirname(__file__)))
LOG_DIR = BASE_DIR / "logs"


class DianpingAPIHandler(BaseHTTPRequestHandler):
    """简单的 HTTP API"""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/api/packs":
            # 获取待发布内容包
            limit = int(params.get("limit", ["5"])[0])
            packs = get_pending_packs(limit=limit)
            self._json_response({
                "count": len(packs),
                "packs": packs
            })

        elif parsed.path == "/api/status":
            # 服务状态
            packs = get_pending_packs(limit=100)
            self._json_response({
                "status": "ok",
                "pending_count": len(packs),
                "time": datetime.now().isoformat()
            })

        elif parsed.path == "/api/generate":
            # 触发批量生成
            count = int(params.get("count", ["15"])[0])
            pack_ids = batch_generate(count)
            self._json_response({
                "generated": len(pack_ids),
                "pack_ids": pack_ids
            })

        else:
            self._json_response({"error": "unknown endpoint"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/report":
            # 手机端上报发布结果
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
        else:
            self._json_response({"error": "unknown endpoint"}, 404)

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        # 简化日志
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def run_server(host="0.0.0.0", port=8090):
    server = HTTPServer((host, port), DianpingAPIHandler)
    print(f"大众点评内容工厂 API 运行在 http://{host}:{port}")
    print(f"  GET  /api/packs     — 获取待发布内容")
    print(f"  GET  /api/status    — 服务状态")
    print(f"  GET  /api/generate  — 触发批量生成")
    print(f"  POST /api/report    — 上报发布结果")
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
