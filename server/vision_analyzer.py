"""
大众点评 — 视觉分析 + YOLO 标注生成
Qwen2.5-VL-72B 识别截图 → 结构化描述 + YOLO 标注
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
YOLO_DIR = BASE_DIR / "output" / "yolo_dataset"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# YOLO 类别定义
YOLO_CLASSES = [
    "btn_publish",       # 发笔记按钮
    "btn_submit",        # 发布/提交按钮
    "btn_back",          # 返回按钮
    "btn_search",        # 搜索按钮
    "btn_like",          # 点赞按钮
    "btn_comment",       # 评论按钮
    "btn_share",         # 分享按钮
    "btn_follow",        # 关注按钮
    "btn_collect",       # 收藏按钮
    "btn_topic",         # 话题按钮
    "btn_shop",          # 关联门店按钮
    "input_title",       # 标题输入框
    "input_content",     # 内容输入框
    "input_search",      # 搜索输入框
    "nav_home",          # 底部导航-首页
    "nav_explore",       # 底部导航-发现/探索
    "nav_message",       # 底部导航-消息
    "nav_me",            # 底部导航-我的
    "card_shop",         # 店铺卡片
    "card_note",         # 笔记卡片
    "image_content",     # 内容图片区域
    "tab_bar",           # 底部标签栏
    "popup_dialog",      # 弹窗
    "toast",             # 提示信息
    "other",             # 其他
]

# 视觉模型配置
VL_API_URL = os.environ.get("VL_API_URL", "http://zhenze-huhehaote.cmecloud.cn/v1/chat/completions")
VL_API_KEY = os.environ.get("VL_API_KEY", "")
VL_MODEL = os.environ.get("VL_MODEL", "qwen2.5-vl-72b-instruct")


def screenshot_to_base64_url(filepath):
    ext = os.path.splitext(filepath)[1].lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def get_image_size(filepath):
    """获取图片尺寸"""
    from PIL import Image
    with Image.open(filepath) as img:
        return img.size  # (width, height)


def analyze_for_yolo(screenshot_path, nodes_info=None):
    """
    用视觉模型分析截图，同时输出：
    1. 页面结构描述
    2. YOLO 标注（每个元素的 bbox + 类别）
    """
    if not VL_API_KEY:
        return {"error": "VL_API_KEY not set"}

    # 构造节点信息提示
    nodes_hint = ""
    if nodes_info:
        key_nodes = []
        for n in nodes_info[:40]:
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
            nodes_hint = "\n\n控件节点数据（辅助定位）：\n" + "\n".join(key_nodes)

    classes_str = ", ".join(f'"{c}"' for c in YOLO_CLASSES)

    prompt = f"""分析这个大众点评APP截图。

请识别界面中所有可交互元素和关键区域，返回JSON：

{{
  "page_type": "页面类型（首页/店铺详情/发布笔记/搜索结果/笔记详情/个人中心/话题页/其他）",
  "main_content": "一句话描述页面内容",
  "navigation": ["底部导航栏的tab名称列表，如无填空数组"],
  "publish_entry": "是否有发笔记入口，描述位置，null表示没有",
  "elements": [
    {{
      "label": "类别（必须是以下之一: [{classes_str}]）",
      "text": "元素上的文字",
      "x_center": 0.5,
      "y_center": 0.5,
      "width": 0.2,
      "height": 0.05,
      "description": "功能描述"
    }}
  ]
}}

坐标规则：
- 所有坐标都是归一化的（0-1），相对于图片宽高
- x_center, y_center: 元素中心点
- width, height: 元素占图片的比例
- 用像素坐标除以图片尺寸得到归一化值
- 参考"控件节点数据"中的bounds值来精确定位

只返回JSON，不要其他文字。{nodes_hint}"""

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
            clean = content.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
                clean = clean.rsplit("```", 1)[0]
            return json.loads(clean)
        else:
            return {"error": f"API {resp.status_code}: {resp.text[:200]}"}
    except json.JSONDecodeError:
        return {"raw_response": content, "parse_error": True}
    except Exception as e:
        return {"error": str(e)}


def generate_yolo_labels(analysis_result, img_width, img_height):
    """
    从视觉分析结果生成 YOLO 格式标注
    YOLO format: class_id x_center y_center width height (归一化)
    """
    labels = []
    elements = analysis_result.get("elements", [])

    for elem in elements:
        label = elem.get("label", "other")
        # 映射到类别ID
        class_id = YOLO_CLASSES.index(label) if label in YOLO_CLASSES else YOLO_CLASSES.index("other")

        xc = elem.get("x_center", 0.5)
        yc = elem.get("y_center", 0.5)
        w = elem.get("width", 0.1)
        h = elem.get("height", 0.05)

        labels.append(f"{class_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

    return labels


def batch_analyze_explore(limit=100):
    """
    批量处理探索数据：视觉分析 + YOLO标注生成
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

    # 准备 YOLO 数据集目录
    yolo_images_dir = YOLO_DIR / "images" / "train"
    yolo_labels_dir = YOLO_DIR / "labels" / "train"
    yolo_images_dir.mkdir(parents=True, exist_ok=True)
    yolo_labels_dir.mkdir(parents=True, exist_ok=True)

    # 按 activity 去重
    analyzed = {}
    yolo_count = 0

    for frame in frames:
        act = frame.get("activity", "unknown")
        screenshot = frame.get("screenshot", "")
        if not screenshot:
            continue

        filepath = SCREENSHOT_DIR / screenshot
        if not filepath.exists():
            continue

        # 每个 activity 只分析一次（选帧数最多的那个截图）
        if act in analyzed:
            continue

        print(f"\n分析: {act} ({screenshot})")

        # 视觉分析
        result = analyze_for_yolo(str(filepath), frame.get("nodes"))

        if "error" in result:
            print(f"  ✗ {result['error']}")
            continue

        result["activity"] = act
        result["screenshot"] = screenshot
        result["depth"] = frame.get("depth", 0)
        result["node_count"] = frame.get("node_count", 0)

        # 生成 YOLO 标注
        try:
            img_w, img_h = get_image_size(str(filepath))
            yolo_labels = generate_yolo_labels(result, img_w, img_h)

            if yolo_labels:
                # 复制图片到 YOLO 数据集
                import shutil
                yolo_img_name = f"dp_{len(analyzed):04d}.png"
                shutil.copy2(str(filepath), yolo_images_dir / yolo_img_name)

                # 写标注文件
                yolo_label_name = f"dp_{len(analyzed):04d}.txt"
                with open(yolo_labels_dir / yolo_label_name, "w") as f:
                    f.write("\n".join(yolo_labels))

                result["yolo_labels"] = yolo_labels
                result["yolo_image"] = yolo_img_name
                yolo_count += 1
                print(f"  ✓ {result.get('page_type', '?')}: {len(yolo_labels)} labels")
            else:
                print(f"  ~ {result.get('page_type', '?')}: no labels")
        except Exception as e:
            print(f"  ✗ YOLO生成失败: {e}")

        analyzed[act] = result

        if len(analyzed) >= limit:
            break

    # 保存分析结果
    output = {
        "generated_at": datetime.now().isoformat(),
        "model": VL_MODEL,
        "total_analyzed": len(analyzed),
        "yolo_samples": yolo_count,
        "yolo_classes": YOLO_CLASSES,
        "pages": list(analyzed.values()),
    }

    output_file = ANALYSIS_DIR / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    with open(PAGE_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 生成 YOLO 数据集配置
    yaml_content = f"""path: {YOLO_DIR.absolute()}
train: images/train
val: images/train

nc: {len(YOLO_CLASSES)}
names: {YOLO_CLASSES}
"""
    with open(YOLO_DIR / "dataset.yaml", "w") as f:
        f.write(yaml_content)

    print(f"\n=== 完成 ===")
    print(f"分析页面: {len(analyzed)}")
    print(f"YOLO样本: {yolo_count}")
    print(f"数据集: {YOLO_DIR}")
    print(f"结果: {output_file}")
    return output


def get_analysis_summary():
    if PAGE_MAP_FILE.exists():
        with open(PAGE_MAP_FILE, "r") as f:
            return json.load(f)
    if ANALYSIS_DIR.exists():
        files = sorted(ANALYSIS_DIR.glob("analysis_*.json"), reverse=True)
        if files:
            with open(files[0], "r") as f:
                return json.load(f)
    return {"status": "no data", "hint": "run explore.js first"}


if __name__ == "__main__":
    batch_analyze_explore()
