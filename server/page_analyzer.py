"""
大众点评 — 页面分析引擎
处理探索模式收集的截图+节点数据，自动识别页面结构
"""
import json
import os
import base64
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCREENSHOT_DIR = BASE_DIR / "output" / "screenshots"
EXPLORE_LOG = BASE_DIR / "logs" / "explore_log.jsonl"
ANALYSIS_OUTPUT = BASE_DIR / "output" / "page_map.json"

# 截图 -> base64
def screenshot_to_base64(filepath):
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_frame(screenshot_path, nodes, activity, depth, action):
    """
    分析单帧截图 + 节点数据
    返回页面结构描述
    """
    # 提取关键 UI 元素
    key_elements = []
    for n in (nodes or []):
        if n.get("t") or n.get("d"):
            key_elements.append({
                "text": n.get("t", ""),
                "desc": n.get("d", ""),
                "clickable": n.get("c", False),
                "bounds": n.get("b", ""),
                "type": n.get("cls", ""),
            })

    return {
        "screenshot": os.path.basename(screenshot_path),
        "activity": activity,
        "depth": depth,
        "action": action,
        "element_count": len(key_elements),
        "elements": key_elements[:30],  # 只保留前30个关键元素
    }


def build_page_map():
    """
    从探索日志构建页面地图
    按页面分组，识别页面类型和导航关系
    """
    if not EXPLORE_LOG.exists():
        print("没有探索日志")
        return None

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
        return None

    print(f"共 {len(frames)} 帧数据")

    # 按 activity 分组
    pages_by_activity = {}
    for frame in frames:
        act = frame.get("activity", "unknown")
        if act not in pages_by_activity:
            pages_by_activity[act] = []
        pages_by_activity[act].append(frame)

    # 构建页面地图
    page_map = {
        "generated_at": datetime.now().isoformat(),
        "total_frames": len(frames),
        "total_activities": len(pages_by_activity),
        "pages": [],
    }

    for act, act_frames in pages_by_activity.items():
        # 收集这个 activity 下所有出现过的元素
        all_elements = {}
        for f in act_frames:
            for n in f.get("nodes", []):
                key = n.get("t", "") + "|" + n.get("d", "")
                if key and key not in all_elements:
                    all_elements[key] = n

        page_info = {
            "activity": act,
            "frame_count": len(act_frames),
            "screenshots": [f.get("screenshot", "") for f in act_frames[:5]],
            "elements": list(all_elements.values())[:50],
            "clickable_elements": [
                n for n in all_elements.values()
                if n.get("c") and (n.get("t") or n.get("d"))
            ][:20],
        }
        page_map["pages"].append(page_info)

        print(f"\n页面: {act}")
        print(f"  帧数: {len(act_frames)}")
        print(f"  可点击元素: {len(page_info['clickable_elements'])}")
        for el in page_info["clickable_elements"][:10]:
            print(f"    [{el.get('cls','')}] {el.get('t','')} / {el.get('d','')} @ {el.get('b','')}")

    # 保存
    with open(ANALYSIS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(page_map, f, ensure_ascii=False, indent=2)

    print(f"\n页面地图已保存到: {ANALYSIS_OUTPUT}")
    return page_map


def get_analysis_summary():
    """返回分析摘要"""
    if ANALYSIS_OUTPUT.exists():
        with open(ANALYSIS_OUTPUT, "r") as f:
            return json.load(f)
    return {"status": "no data yet"}


if __name__ == "__main__":
    build_page_map()
