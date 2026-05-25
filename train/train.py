"""
大众点评 YOLO 训练脚本
在 GPU/CPU 训练环境上运行，不在采集服务器上运行

用法:
    1. 先把采集服务器的 yolo_dataset 拷贝过来
    2. 确认 dataset.yaml 路径正确
    3. python train.py
"""

from ultralytics import YOLO
import os
import sys

# ============ 配置 ============
DATASET_YAML = os.path.join(os.path.dirname(__file__), "yolo_dataset", "dataset.yaml")
EPOCHS = 50
IMGSZ = 640
BATCH_GPU = 16
BATCH_CPU = 4
PROJECT = os.path.join(os.path.dirname(__file__), "runs")
NAME = "dianping_v1"


def detect_device():
    """检测可用设备"""
    import torch
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB")
        return "0", BATCH_GPU
    else:
        print("未检测到 GPU，使用 CPU 训练")
        return "cpu", BATCH_CPU


def train():
    if not os.path.exists(DATASET_YAML):
        print(f"数据集配置不存在: {DATASET_YAML}")
        print("请先从采集服务器拷贝 yolo_dataset/ 目录")
        sys.exit(1)

    device, batch = detect_device()

    print(f"\n训练配置:")
    print(f"  数据集: {DATASET_YAML}")
    print(f"  设备: {device}")
    print(f"  Epochs: {EPOCHS}")
    print(f"  Batch: {batch}")
    print(f"  图片尺寸: {IMGSZ}")
    print()

    model = YOLO("yolov8n.pt")

    results = model.train(
        data=DATASET_YAML,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=batch,
        device=device,
        project=PROJECT,
        name=NAME,
        patience=10,       # 早停
        save_period=10,     # 每10个epoch保存一次
    )

    print("\n训练完成!")
    print(f"最佳权重: {PROJECT}/{NAME}/weights/best.pt")

    # 自动导出
    best_model = YOLO(f"{PROJECT}/{NAME}/weights/best.pt")

    print("\n导出 ONNX...")
    best_model.export(format="onnx", imgsz=IMGSZ)
    print("导出完成")

    # 验证
    print("\n运行验证...")
    metrics = best_model.val(data=DATASET_YAML)
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")


if __name__ == "__main__":
    train()
