# 大众点评 YOLO 视觉导航 Plan v3

> 基于「端侧 AI 视觉导航」方案（三角洲行动）迁移而来
> 日期：2026-05-25
> 前序方案：vl_navigation_v2.md（废弃）

---

## 核心架构

```
训练阶段（离线）：
  录屏 → FFmpeg 抽帧 → VL 标注 → YOLO 训练集 → YOLOv8n 训练

运行阶段（手机端）：
  YOLO 实时识别元素位置 → 状态机决定操作 → 执行（点击/滑动/输入）
```

**三个角色：**

| 组件 | 角色 | 说明 |
|------|------|------|
| YOLOv8n | 导航器 | 本地实时识别 UI 元素，返回归一化 bbox |
| 状态机 | 大脑 | 根据当前页面+业务目标决定下一步操作 |
| VL (Qwen2.5-VL) | 标注员 | 只在训练阶段用，标注截图生成 YOLO 训练数据 |

**关键约束：大众点评用自绘控件，无障碍服务拿不到内容节点。视觉是唯一的交互通道。**

---

## YOLO 标签体系（大众点评）

```yaml
# data.yaml
names:
  0: search_bar        # 搜索栏
  1: content_card      # 内容卡片（图文/视频）
  2: bottom_nav        # 底部导航栏
  3: nav_home          # 底部-首页
  4: nav_map           # 底部-地图
  5: nav_publish       # 底部-发布按钮
  6: nav_message       # 底部-消息
  7: nav_me            # 底部-我的
  8: like_button       # 点赞按钮
  9: comment_button    # 评论按钮
  10: share_button     # 分享按钮
  11: back_button      # 返回按钮
  12: publish_entry    # 发布入口（首页+号）
```

~13 类，远少于三角洲的 126 类。训练数据需求：200-500 张标注图。

---

## Phase 划分

### Phase 0：训练数据采集

**目标：** 收集大众点评各页面的截图/录屏，用 VL 标注生成 YOLO 训练集。

**动作：**
1. 手动录屏：操作大众点评各页面（首页、笔记详情、发布页、搜索结果、个人中心）
2. FFmpeg 抽帧：场景变动 > 5% 才抽，去模糊
3. VL 标注：每张图调 Qwen2.5-VL，输出 YOLO 格式 bbox
4. 人工抽检：10-20% 确认框准确率 > 85%
5. 数据集划分：train 80% / val 20%

**需要覆盖的页面：**
- 首页（双列瀑布流）
- 笔记详情页
- 发布页
- 搜索结果页
- 个人中心

**验收标准：**
- [ ] ≥ 300 张标注图片
- [ ] VL 标注准确率抽检 > 85%
- [ ] YOLO 格式数据集就绪

---

### Phase 1：YOLO 训练

**目标：** 训练 YOLOv8n 模型，导出 ONNX 用于手机端推理。

**动作：**
1. 训练：`yolo train data=dianping.yaml model=yolov8n.pt epochs=100`
2. 评估：val mAP50 > 0.7
3. 导出：ONNX + INT8 量化，模型 < 5MB
4. 手机端部署测试：确认推理延迟 < 40ms

**验收标准：**
- [ ] val mAP50 > 0.7（核心类别：content_card, search_bar, bottom_nav）
- [ ] ONNX 模型 < 5MB
- [ ] 手机端推理 < 40ms

---

### Phase 2：手机端推理引擎

**目标：** 在 AutoJs6 中集成 YOLO 推理，实时识别 UI 元素。

**动作：**
1. 加载 ONNX 模型（用 OpenCV DNN 或 NCNN）
2. 每帧截图 → YOLO 推理 → 返回元素列表（类别 + 归一化 bbox）
3. 验证：首页识别出 ≥ 6 个 content_card

**验收标准：**
- [ ] 首页 content_card 识别 ≥ 6 个
- [ ] 底部导航 5 个 tab 全部识别
- [ ] 搜索栏识别准确
- [ ] 单帧推理 < 40ms

---

### Phase 3：状态机 + 自动操作

**目标：** 基于 YOLO 识别结果，用状态机驱动自动操作。

**页面状态机：**
```
[首页] → 点击 content_card → [笔记详情]
[首页] → 点击 search_bar → [搜索页]
[首页] → 点击 nav_publish → [发布页]
[笔记详情] → 点击 like_button → 点赞
[笔记详情] → 点击 back_button → [首页]
```

**操作逻辑：**
```python
def on_frame(yolo_results):
    page = identify_page(yolo_results)  # 根据识别到的元素组合判断页面
    action = state_machine.decide(page)  # 状态机决定下一步
    execute(action)  # 点击/滑动/输入
```

**验收标准：**
- [ ] 页面识别准确率 > 90%
- [ ] 连续 20 次操作无崩溃
- [ ] 养号浏览闭环：首页→进详情→点赞→返回→滑动→重复

---

### Phase 4：业务逻辑

叠加具体业务：
- 养号浏览（自动浏览+点赞，7天）
- 发布笔记（导航到发布页→输入→提交）
- 定时执行

---

## 与三角洲方案的复用关系

| 模块 | 三角洲 | 大众点评 | 复用度 |
|------|--------|---------|--------|
| FFmpeg 抽帧 | ✅ scripts/frame_extractor.py | 直接复用 | 100% |
| VL 标注 | ✅ scripts/vlm_annotator.py | 改 prompt+标签 | 80% |
| YOLO 训练 | ✅ scripts/train_pipeline.py | 改 data.yaml | 90% |
| ONNX 推理 | ✅ src/yolo_engine.py | 直接复用 | 95% |
| 状态机 | ✅ src/fsm.py | 简化版 | 60% |
| 反作弊/伪装 | ✅ Phase 0 全部 | 不需要 | 0% |
| NavMesh/寻路 | ✅ navmesh.py | 不需要 | 0% |

---

## 技术栈

| 工具 | 用途 |
|------|------|
| YOLOv8n (Ultralytics) | 目标检测训练+推理 |
| ONNX + INT8 | 模型导出量化 |
| OpenCV DNN / NCNN | 手机端推理引擎 |
| FFmpeg | 视频抽帧 |
| Qwen2.5-VL-72B | 训练数据标注 |
| AutoJs6 | 手机端脚本 |

---

## 今天已完成的基础设施（可复用）

- ✅ 截图上传链路（base64 JSON → 服务器保存）
- ✅ VL API 连通（Qwen2.5-VL-72B，中国移动云 endpoint）
- ✅ 服务器常驻运行（run.sh 自动重启）
- ✅ SQLite 采集记录（collect_db.py）
