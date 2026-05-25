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
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    timeout = 60
    daemon_threads = True

from content_pack import get_pending_packs, update_pack_status, batch_generate
from page_analyzer import build_page_map, get_analysis_summary
from vision_analyzer import batch_analyze_explore, get_analysis_summary as get_vision_analysis

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = BASE_DIR / "logs"
SCREENSHOT_DIR = BASE_DIR / "output" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class DianpingAPIHandler(BaseHTTPRequestHandler):
    """HTTP API"""

    # 允许最大 10MB 请求体
    max_body_length = 10 * 1024 * 1024

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

        elif parsed.path == "/api/explore_done":
            # 探索完成，触发分析
            result = build_page_map()
            self._json_response({
                "ok": True,
                "pages_found": len(result.get("pages", [])) if result else 0,
                "total_frames": result.get("total_frames", 0) if result else 0,
            })

        elif parsed.path == "/api/page_map":
            # 查看视觉分析结果
            data = get_vision_analysis()
            self._json_response(data)

        elif parsed.path == "/api/analyze":
            # 手动触发视觉分析
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", ["50"])[0])
            result = batch_analyze_explore(limit=limit)
            self._json_response({
                "ok": True,
                "pages_analyzed": result.get("total_analyzed", 0) if result else 0,
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
        """处理截图上传（JSON base64 或 multipart）"""
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # JSON 模式（base64 截图）
        if "application/json" in content_type or content_type.startswith("text/") or not content_type:
            raw = json.loads(body)
            # AutoJs6 可能传了双重 JSON 字符串
            if isinstance(raw, str):
                raw = json.loads(raw)
            data = raw if isinstance(raw, dict) else {}
            desc = data.get("description", "unknown")
            ui_tree = data.get("ui_tree", "[]")
            screenshot_b64 = data.get("screenshot_b64", "")

            # 解码 base64 截图
            screenshot_file = None
            if screenshot_b64:
                try:
                    import base64 as b64mod
                    img_bytes = b64mod.b64decode(screenshot_b64)
                    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.png"
                    filepath = SCREENSHOT_DIR / filename
                    with open(filepath, "wb") as f:
                        f.write(img_bytes)
                    screenshot_file = filename
                    import sys
                    print(f"[eyes] 截图已保存(base64): {filename} ({len(img_bytes)//1024}KB)", flush=True)
                except Exception as e:
                    print(f"[eyes] base64解码失败: {e}", flush=True)

            # 解析节点
            node_count = 0
            try:
                nodes = json.loads(ui_tree)
                node_count = len(nodes)
                print(f"[eyes] {desc} | {node_count} nodes", flush=True + (f" | {screenshot_file}" if screenshot_file else " | 无截图"))
                for n in nodes[:10]:
                    if n.get("t") or n.get("d"):
                        print(f"  [{n.get('cls','')}] {n.get('t','')} / {n.get('d','')} @ {n.get('b','')}")
            except:
                pass

            # VL 视觉分析（后台执行，不阻塞响应）
            if screenshot_file:
                try:
                    import threading
                    def _vl_task():
                        try:
                            from vision_analyzer import analyze_for_yolo
                            vl_result = analyze_for_yolo(str(filepath))
                            page_type = vl_result.get("page_type", "unknown")
                            main_content = vl_result.get("main_content", "")[:200]
                            print(f"[eyes] VL分析: {page_type} | {main_content}", flush=True)
                        except Exception as e:
                            print(f"[eyes] VL分析失败: {e}", flush=True)
                    threading.Thread(target=_vl_task, daemon=True).start()
                except Exception as e:
                    print(f"[eyes] VL启动失败: {e}")

            self._json_response({
                "ok": True,
                "summary": f"截图已保存, {node_count} 个控件节点",
                "screenshot": screenshot_file,
                "description": desc,
            })
            return

        # multipart 模式（兼容旧版）
        if "multipart/form-data" in content_type:
            form = cgi.FieldStorage(
                fp=None,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type}
            )
            # ... multipart fallback
            self._json_response({"ok": True, "summary": "multipart received"})
            return

        self._json_response({"ok": True, "summary": "unknown format"})

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
    server = ThreadedHTTPServer((host, port), DianpingAPIHandler)
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
