"""
大众点评内容工厂 — 图片处理模块
小红书图片抓取 + 去水印 + 二创
"""
import os
import random
import hashlib
import requests
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter


OUTPUT_DIR = Path(os.path.dirname(os.path.dirname(__file__))) / "output"
ORIGINAL_DIR = OUTPUT_DIR / "original"
PROCESSED_DIR = OUTPUT_DIR / "processed"


def ensure_dirs():
    for d in [ORIGINAL_DIR, PROCESSED_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def download_image(url, filename=None):
    """下载图片到本地"""
    ensure_dirs()
    if not filename:
        filename = hashlib.md5(url.encode()).hexdigest()[:12] + ".jpg"
    filepath = ORIGINAL_DIR / filename

    try:
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36"
        })
        if resp.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return str(filepath)
    except Exception as e:
        print(f"下载失败: {e}")
    return None


def process_image(input_path, output_path=None, style="random"):
    """
    图片二创处理
    style: random / warm / cool / bright / vintage
    """
    ensure_dirs()
    if not output_path:
        name = Path(input_path).stem + "_p" + random.randint(1000, 9999)
        output_path = PROCESSED_DIR / f"{name}.jpg"

    try:
        img = Image.open(input_path).convert("RGB")

        # 随机裁剪（去掉边角水印）
        w, h = img.size
        crop_pct = random.uniform(0.02, 0.08)
        left = int(w * crop_pct)
        top = int(h * crop_pct)
        right = int(w * (1 - crop_pct))
        bottom = int(h * (1 - crop_pct))
        img = img.crop((left, top, right, bottom))

        # 随机调色
        if style == "random":
            style = random.choice(["warm", "cool", "bright", "vintage"])

        if style == "warm":
            img = ImageEnhance.Color(img).enhance(1.1)
            img = ImageEnhance.Brightness(img).enhance(1.05)
        elif style == "cool":
            img = ImageEnhance.Color(img).enhance(0.9)
            img = ImageEnhance.Brightness(img).enhance(1.1)
        elif style == "bright":
            img = ImageEnhance.Brightness(img).enhance(1.15)
            img = ImageEnhance.Contrast(img).enhance(1.05)
        elif style == "vintage":
            img = ImageEnhance.Color(img).enhance(0.8)
            img = ImageEnhance.Brightness(img).enhance(0.95)
            img = ImageEnhance.Contrast(img).enhance(1.1)

        # 轻微锐化
        img = ImageEnhance.Sharpness(img).enhance(1.1)

        # 随机微调尺寸（打破图片指纹）
        new_w = int(w * random.uniform(0.95, 1.0))
        new_h = int(h * random.uniform(0.95, 1.0))
        img = img.resize((new_w, new_h), Image.LANCZOS)

        # 质量随机（85-95，改变文件指纹）
        quality = random.randint(85, 95)
        img.save(output_path, "JPEG", quality=quality)

        return str(output_path)
    except Exception as e:
        print(f"处理失败: {e}")
        return None


def create_collage(image_paths, output_path=None, cols=2):
    """拼图（多图合一，增加原创度）"""
    ensure_dirs()
    if not output_path:
        name = f"collage_{hashlib.md5(str(image_paths).encode()).hexdigest()[:8]}.jpg"
        output_path = PROCESSED_DIR / name

    try:
        images = [Image.open(p).convert("RGB") for p in image_paths[:4]]
        if not images:
            return None

        # 统一尺寸
        min_w = min(img.width for img in images)
        min_h = min(img.height for img in images)
        target_size = min(min_w, min_h, 800)
        images = [img.resize((target_size, target_size), Image.LANCZOS) for img in images]

        rows = (len(images) + cols - 1) // cols
        canvas_w = cols * target_size + (cols - 1) * 10
        canvas_h = rows * target_size + (rows - 1) * 10
        canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))

        for i, img in enumerate(images):
            x = (i % cols) * (target_size + 10)
            y = (i // cols) * (target_size + 10)
            canvas.paste(img, (x, y))

        canvas.save(output_path, "JPEG", quality=90)
        return str(output_path)
    except Exception as e:
        print(f"拼图失败: {e}")
        return None


if __name__ == "__main__":
    # 测试：下载一些测试图片
    test_urls = [
        "https://picsum.photos/800/600?random=1",
        "https://picsum.photos/800/600?random=2",
        "https://picsum.photos/800/600?random=3",
    ]

    downloaded = []
    for url in test_urls:
        path = download_image(url)
        if path:
            downloaded.append(path)
            processed = process_image(path)
            print(f"原始: {path}")
            print(f"二创: {processed}")

    if len(downloaded) >= 2:
        collage = create_collage(downloaded[:2])
        print(f"拼图: {collage}")
