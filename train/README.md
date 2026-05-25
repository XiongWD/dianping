# YOLOv8n 训练环境部署指南

## 环境要求

### GPU 环境（推荐）
| 项目 | 要求 |
|---|---|
| GPU | NVIDIA GPU，显存 ≥ 4GB |
| CUDA | 11.8+ |
| Python | 3.8 - 3.12 |
| 内存 | ≥ 8GB |
| 磁盘 | ≥ 5GB |
| 训练时长 | ~5-10 分钟 / 100张图 / 50 epochs |

### CPU 环境（可用但慢）
| 项目 | 要求 |
|---|---|
| CPU | 4核+ |
| 内存 | ≥ 4GB |
| 磁盘 | ≥ 5GB |
| 训练时长 | ~30-60 分钟 / 100张图 / 50 epochs |

## 安装步骤

```bash
# 1. 创建虚拟环境（推荐）
python3 -m venv yolo-env
source yolo-env/bin/activate

# 2. 安装 ultralytics
pip install ultralytics

# GPU 环境额外安装（如果 pip install ultralytics 没自动装 torch）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 3. 验证
python -c "from ultralytics import YOLO; print('YOLO OK')"
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

## 数据集准备

采集完成后，将服务器上的数据集拷贝到训练机器：

```bash
# 在训练机器上
scp -r user@192.168.0.107:~/work/dianping/output/yolo_dataset ./
```

数据集目录结构：
```
yolo_dataset/
├── dataset.yaml          # 数据集配置
├── images/
│   └── train/
│       ├── dp_0000.png
│       ├── dp_0001.png
│       └── ...
└── labels/
    └── train/
        ├── dp_0000.txt
        ├── dp_0001.txt
        └── ...
```

标注格式（YOLO）：
```
class_id x_center y_center width height
```
所有值为归一化坐标（0-1）。

## 类别定义

| ID | 类别名 | 说明 |
|---|---|---|
| 0 | btn_publish | 发笔记按钮 |
| 1 | btn_submit | 发布/提交按钮 |
| 2 | btn_back | 返回按钮 |
| 3 | btn_search | 搜索按钮 |
| 4 | btn_like | 点赞按钮 |
| 5 | btn_comment | 评论按钮 |
| 6 | btn_share | 分享按钮 |
| 7 | btn_follow | 关注按钮 |
| 8 | btn_collect | 收藏按钮 |
| 9 | btn_topic | 话题按钮 |
| 10 | btn_shop | 关联门店按钮 |
| 11 | input_title | 标题输入框 |
| 12 | input_content | 内容输入框 |
| 13 | input_search | 搜索输入框 |
| 14 | nav_home | 底部导航-首页 |
| 15 | nav_explore | 底部导航-发现 |
| 16 | nav_message | 底部导航-消息 |
| 17 | nav_me | 底部导航-我的 |
| 18 | card_shop | 店铺卡片 |
| 19 | card_note | 笔记卡片 |
| 20 | image_content | 内容图片区域 |
| 21 | tab_bar | 底部标签栏 |
| 22 | popup_dialog | 弹窗 |
| 23 | toast | 提示信息 |
| 24 | other | 其他 |

## 训练

```bash
# 激活环境
source yolo-env/bin/activate

# 运行训练脚本
python train.py

# 或手动训练
python -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')  # 预训练权重
model.train(
    data='yolo_dataset/dataset.yaml',
    epochs=50,
    imgsz=640,
    batch=16,         # GPU用16，CPU用4
    device='0',       # GPU用'0'，CPU用'cpu'
    project='runs/train',
    name='dianping_v1',
)
"
```

## 导出

```python
from ultralytics import YOLO

# 加载最佳模型
model = YOLO('runs/train/dianping_v1/weights/best.pt')

# 导出 ONNX（手机端推理用）
model.export(format='onnx', imgsz=640)

# 导出 NCNN（Android端最优）
model.export(format='ncnn', imgsz=640)

# 导出 TFLite（Android备选）
model.export(format='tflite', imgsz=640)
```

导出后的模型部署到手机端，配合 AutoJs6 使用。

## 手机端推理方案

训练完成后，在手机端使用以下方案之一运行 YOLO 检测：

1. **ONNX Runtime (推荐)**: AutoJs6 可加载 ONNX 模型
2. **NCNN**: 腾讯开源移动端推理框架，ARM优化好
3. **TFLite**: Google 移动端方案，兼容性好

推理流程：
```
截图 → YOLO检测 → 获取按钮位置 → AutoJs6 点击
```
