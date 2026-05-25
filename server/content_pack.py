"""
大众点评内容工厂 — 内容打包模块
将文案+图片打包成待发布的内容包，供手机端拉取
"""
import json
import os
import time
import uuid
from pathlib import Path
from datetime import datetime

from content_gen import ContentGenerator
from image_process import download_image, process_image, create_collage

BASE_DIR = Path(os.path.dirname(os.path.dirname(__file__)))
OUTPUT_DIR = BASE_DIR / "output"
PACK_DIR = OUTPUT_DIR / "packs"
LOG_DIR = BASE_DIR / "logs"


def ensure_dirs():
    for d in [PACK_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# 默认店铺素材库（后续可以动态扩展）
DEFAULT_SHOPS = [
    {"name": "木屋烧烤(南山店)", "category": "food", "city": "深圳", "area": "南山"},
    {"name": "太二酸菜鱼(海岸城店)", "category": "food", "city": "深圳", "area": "南山"},
    {"name": "喜茶(万象天地店)", "category": "cafe", "city": "深圳", "area": "南山"},
    {"name": "瑞幸咖啡(科技园店)", "category": "cafe", "city": "深圳", "area": "科技园"},
    {"name": "海底捞火锅(华强北店)", "category": "food", "city": "深圳", "area": "福田"},
    {"name": "深圳湾公园", "category": "scenic", "city": "深圳", "area": "南山"},
    {"name": "人才公园", "category": "scenic", "city": "深圳", "area": "南山"},
    {"name": "莲山公园", "category": "scenic", "city": "深圳", "area": "福田"},
]


def create_content_pack(shop_info=None, image_urls=None):
    """
    创建一个待发布内容包
    返回 pack_id
    """
    ensure_dirs()

    if shop_info is None:
        import random
        shop_info = random.choice(DEFAULT_SHOPS)

    shop_name = shop_info.get("name", "未知店铺")
    category = shop_info.get("category", "food")
    city = shop_info.get("city", "深圳")
    area = shop_info.get("area", "")

    # 1. 生成文案
    gen = ContentGenerator()
    review = gen.generate_review(
        shop_name=shop_name,
        category=category,
        city=city,
        area=area,
    )
    if not review["success"]:
        print(f"文案生成失败: {review['error']}")
        return None

    title = gen.generate_title(shop_name=shop_name, category=category, city=city, area=area)

    # 2. 处理图片（如果有）
    processed_images = []
    if image_urls:
        for url in image_urls[:6]:
            path = download_image(url)
            if path:
                processed = process_image(path)
                if processed:
                    processed_images.append(processed)

    # 3. 打包
    pack_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    pack = {
        "pack_id": pack_id,
        "created_at": datetime.now().isoformat(),
        "status": "pending",  # pending → published → failed
        "shop_name": shop_name,
        "category": category,
        "city": city,
        "title": title,
        "content": review["content"],
        "char_count": review["char_count"],
        "images": processed_images,
        "image_count": len(processed_images),
        "tags": ["创作者赏金计划"],
        "publish_at": None,  # 建议发布时间
    }

    # 保存到文件
    pack_file = PACK_DIR / f"{pack_id}.json"
    with open(pack_file, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    print(f"内容包已创建: {pack_id}")
    print(f"  店铺: {shop_name}")
    print(f"  标题: {title}")
    print(f"  字数: {review['char_count']}")
    print(f"  图片: {len(processed_images)} 张")

    return pack_id


def get_pending_packs(limit=10):
    """获取待发布的内容包"""
    ensure_dirs()
    packs = []
    for f in sorted(PACK_DIR.glob("*.json")):
        with open(f, "r", encoding="utf-8") as fp:
            pack = json.load(fp)
        if pack.get("status") == "pending":
            packs.append(pack)
        if len(packs) >= limit:
            break
    return packs


def update_pack_status(pack_id, status, result=None):
    """更新内容包状态"""
    ensure_dirs()
    pack_file = PACK_DIR / f"{pack_id}.json"
    if not pack_file.exists():
        return False

    with open(pack_file, "r", encoding="utf-8") as f:
        pack = json.load(f)

    pack["status"] = status
    if result:
        pack["publish_result"] = result
    pack["updated_at"] = datetime.now().isoformat()

    with open(pack_file, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    return True


def batch_generate(count=15, shops=None):
    """批量生成内容包"""
    if shops is None:
        shops = DEFAULT_SHOPS

    pack_ids = []
    for i in range(count):
        import random
        shop = random.choice(shops)
        pack_id = create_content_pack(shop)
        if pack_id:
            pack_ids.append(pack_id)

        # 间隔避免 API 限频
        time.sleep(0.8)

    print(f"\n批量生成完成: {len(pack_ids)}/{count} 个内容包")
    return pack_ids


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "generate":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 15
            batch_generate(count)
        elif cmd == "list":
            packs = get_pending_packs()
            print(f"待发布: {len(packs)} 个")
            for p in packs:
                print(f"  {p['pack_id']} | {p['shop_name']} | {p['title']}")
        elif cmd == "single":
            create_content_pack()
    else:
        # 默认：生成 5 个测试
        batch_generate(5)
