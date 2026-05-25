"""
大众点评 — 视觉分析引擎
用 Qwen2.5-VL-72B 分析截图，自动识别页面结构、按钮、操作入口
"""
import json
import os
import base64
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCREENSHOT_DIR = BASE_DIR / "output" / "screenshots"
EXPLORE_LOG = BASE_DIR / "logs" / "explore_log.jsonl"
PAGE_MAP_FILE = BASE_DIR / "output" / "page_map.json"
ANALYSIS_DIR = BASE_DIR / "output" / "analysis"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# 视觉模型配置（从环境变量读取）
VL_API_URL = os.environ.get("VL_API_URL", "http://zhenze-huhehaote.cmecloud.cn/v1/chat/completions")
VL_API_KEY = os.environ.get("VL_API_KEY", "")
VL_MODEL = os.environ.get("VL_MODEL", "qwen2.5-vl-72b-instruct")


def screenshot_to_base64_url(filepath):
    """截图文件转 base64 data URL"""
    ext = os.path.splitext(filepath)[1].lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def analyze_screenshot(screenshot_path, nodes_info=None, prompt=None):
    """
    用视觉模型分析单张截图
    返回结构化页面描述
    """
    if not VL_API_KEY:
        return {"error": "VL_API_KEY not set"}

    if not prompt:
        nodes_hint = ""
        if nodes_info:
            # 把节点信息也给模型参考
            key_nodes = []
            for n in nodes_info[:30]:
                parts = []
                if n.get("t"): parts.append(f'text="{n["t"]}"')
                if n.get("d"): parts.append(f'desc="{n["d"]}"')
                if n.get("c"): parts.append("clickable")
                if n.get("s"): parts.append("scrollable")
                if n.get("b"): parts.append(f'bounds={n["b"]}')
                if n.get("cls"): parts.append(f'type={n["cls"]}')
                if parts:
                    key_nodes.append("  - " + ", ".join(parts))
            if key_nodes:
                nodes_hint = "\n\n控件节点数据（参考）：\n" + "\n".join(key_nodes)

        prompt = f"""分析这个手机APP截图，这是大众点评APP的界面。

请识别并返回以下信息（JSON格式）：
1. page_type: 页面类型（如：首页、搜索页、店铺详情、发布笔记、个人中心、笔记详情、话题页等）
2. main_content: 页面主要内容描述（一句话）
3. buttons: 可点击的按钮/入口列表，每个包含 name(名称) 和 purpose(功能描述)
4. navigation: 底部导航栏有哪些tab（如果有）
5. key_areas: 页面关键区域（如：搜索栏、内容流、底部栏、顶部栏）
6. publish_entry: 是否有"发笔记"/"发布"入口，如果有描述其位置
{nodes_hint}

只返回JSON，不要其他文字。"""

    img_url = screenshot_to_base64_url(screenshot_path)

    data = {
        "model": VL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_url}},
                    {"type": "text", "text": prompt}
                ]
            }
        ],
        "stream": False
    }

    try:
        resp = requests.post(
            VL_API_URL,
            headers={
                "Authorization": f"Bearer {VL_API_KEY}",
                "Content-Type": "application/json"
            },
            json=data,
            timeout=60
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            # 尝试解析 JSON
            try:
                # 去掉可能的 markdown 代码块标记
                clean = content.strip()
                if clean.startswith("```"):
                    clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                    clean = clean.rsplit("```", 1)[0]
                return json.loads(clean)
            except json.JSONDecodeError:
                return {"raw_response": content}
        else:
            return {"error": f"API error {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def batch_analyze_explore(limit=50):
    """
    批量分析探索模式收集的截图
    """
    if not EXPLORE_LOG.exists():
        print("没有探索日志")
        return

    frames = []
    with open(EXPLORE_LOG, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    frames.append(json.loads(line))
                except:
                    pass

    if not frames:
        print("探索日志为空")
        return

    print(f"共 {len(frames)} 帧数据")

    # 按 activity 去重，每个 activity 只分析代表性帧（第一个）
    analyzed = {}
    for frame in frames:
        act = frame.get("activity", "unknown")
        if act in analyzed:
            continue

        screenshot = frame.get("screenshot", "")
        if not screenshot:
            continue

        filepath = SCREENSHOT_DIR / screenshot
        if not filepath.exists():
            continue

        print(f"\n分析: {act} ({screenshot})")
        result = analyze_screenshot(str(filepath), frame.get("nodes"))

        result["activity"] = act
        result["screenshot"] = screenshot
        result["depth"] = frame.get("depth", 0)
        result["action"] = frame.get("action", "")
        result["node_count"] = frame.get("node_count", 0)

        analyzed[act] = result
        print(f"  → {result.get('page_type', 'unknown')}: {result.get('main_content', '')[:60]}")

        if len(analyzed) >= limit:
            break

    # 保存分析结果
    output = {
        "generated_at": datetime.now().isoformat(),
        "model": VL_MODEL,
        "total_analyzed": len(analyzed),
        "pages": list(analyzed.values()),
    }

    output_file = ANALYSIS_DIR / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 同时更新 page_map
    with open(PAGE_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n分析完成: {len(analyzed)} 个页面")
    print(f"结果保存: {output_file}")
    return output


def get_analysis_summary():
    """返回最新的分析结果"""
    if PAGE_MAP_FILE.exists():
        with open(PAGE_MAP_FILE, "r") as f:
            return json.load(f)
    
    # 没有 page_map，尝试找最新的 analysis 文件
    if ANALYSIS_DIR.exists():
        files = sorted(ANALYSIS_DIR.glob("analysis_*.json"), reverse=True)
        if files:
            with open(files[0], "r") as f:
                return json.load(f)
    
    return {"status": "no analysis data yet", "hint": "run explore.js first, then trigger analysis"}


if __name__ == "__main__":
    batch_analyze_explore()
