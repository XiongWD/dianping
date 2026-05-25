"""
大众点评 YOLO 模型验证和测试脚本
训练完成后用这个脚本验证模型效果
"""

import os
import sys
from ultralytics import YOLO
import cv2

# ============ 配置 ============
MODEL_PATH = os.path.join(os.path.dirname(__file__), "runs", "dianping_v1", "weights", "best.pt")
TEST_IMAGE_DIR = os.path.join(os.path.dirname(__file__), "yolo_dataset", "images", "train")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_results")


def validate():
    """验证模型"""
    if not os.path.exists(MODEL_PATH):
        print(f"模型不存在: {MODEL_PATH}")
        print("请先运行 train.py 训练模型")
        return

    model = YOLO(MODEL_PATH)

    # 在数据集上验证
    print("验证中...")
    metrics = model.val(data=os.path.join(os.path.dirname(__file__), "yolo_dataset", "dataset.yaml"))
    print(f"\nmAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")

    # 按类别打印
    print("\n各类别精度:")
    class_names = model.names
    for i, (map50, map_val) in enumerate(zip(metrics.box.maps50, metrics.box.maps)):
        print(f"  {class_names[i]}: mAP50={map50:.4f}, mAP50-95={map_val:.4f}")


def test_on_images():
    """在测试图片上可视化检测结果"""
    if not os.path.exists(MODEL_PATH):
        print(f"模型不存在: {MODEL_PATH}")
        return

    if not os.path.exists(TEST_IMAGE_DIR):
        print(f"测试图片目录不存在: {TEST_IMAGE_DIR}")
        return

    model = YOLO(MODEL_PATH)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    images = [f for f in os.listdir(TEST_IMAGE_DIR) if f.endswith(('.png', '.jpg'))][:10]

    for img_name in images:
        img_path = os.path.join(TEST_IMAGE_DIR, img_name)
        results = model(img_path, conf=0.3)

        for r in results:
            # 画框并保存
            annotated = r.plot()
            out_path = os.path.join(OUTPUT_DIR, f"det_{img_name}")
            cv2.imwrite(out_path, annotated)
            print(f"{img_name}: 检测到 {len(r.boxes)} 个目标")

    print(f"\n结果保存在: {OUTPUT_DIR}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_on_images()
    else:
        validate()
