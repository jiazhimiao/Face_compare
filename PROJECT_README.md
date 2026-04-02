# 人脸相似度分析系统

基于 InsightFace 的人脸相似度分析系统，支持人脸检测、身份验证、黑名单检查等功能。

## 项目结构

```
Face_compare/
├── roc_analysis.py      # ROC曲线分析，确定最优阈值
├── prepare_data.py      # 数据准备工具
├── face_similarity.py   # 核心功能实现
├── face_api.py          # API服务接口
├── photos/              # 原始照片目录
├── same_person/         # 同一人照片配对（ROC训练用）
├── different_person/    # 不同人照片配对（ROC训练用）
├── blacklist/           # 黑名单照片目录
├── features/            # 特征文件存储
└── output/              # 输出结果目录
```

---

## 一、ROC曲线分析 (roc_analysis.py)

### 功能说明

通过ROC曲线分析确定人脸相似度的最优阈值，支持不同安全场景的阈值推荐。

### 核心流程

```
准备数据集 → 计算相似度 → 生成ROC曲线 → 计算最优阈值 → 输出结果
```

### 主要函数

| 函数名 | 功能描述 |
|--------|----------|
| `init_model()` | 初始化 InsightFace 模型 |
| `extract_face_features(image_path)` | 提取单张图片的人脸特征向量 |
| `calculate_similarity(emb1, emb2)` | 计算两个特征向量的余弦相似度 |
| `prepare_dataset(same_dir, different_dir)` | 准备训练数据集 |
| `analyze_roc(same_pairs, different_pairs)` | 分析ROC曲线，计算最优阈值 |
| `plot_roc_curve(...)` | 绘制ROC曲线和阈值表格 |
| `save_results(...)` | 保存分析结果到JSON文件 |

### 配置参数

```python
MODEL_NAME = 'buffalo_l'              # 模型名称
DEVICE_ID = -1                        # -1=CPU, 0=GPU
MAX_SAME_PERSON_PAIRS = 200           # 同一人配对数量
MAX_DIFFERENT_PERSON_PAIRS = 200      # 不同人配对数量
SAME_PERSON_DIR = './same_person'     # 同一人照片目录
DIFFERENT_PERSON_DIR = './different_person'  # 不同人照片目录
```

### 输出结果

- **roc_curve.png**: ROC曲线图（左图曲线 + 右图阈值表格）
- **roc_curve.json**: 详细分析结果

### 阈值类型说明

| 阈值类型 | FAR要求 | 适用场景 | 说明 |
|----------|---------|----------|------|
| FAR_1e-4 | ≤ 0.01% | 金融支付、银行开户 | 极高安全性 |
| FAR_1e-3 | ≤ 0.1% | 门禁系统、考勤系统 | 平衡安全与便利 |
| FAR_1e-2 | ≤ 1% | 社交应用、一般验证 | 注重用户体验 |
| Youden | 自动计算 | 通用场景 | TPR-FAR最大平衡点 |

### 运行方式

```bash
python roc_analysis.py
```

### 数据文件命名要求

**同一人照片** (same_person目录):
```
{用户ID}_card_front.jpeg    # 身份证正面
{用户ID}_face_photo_list.jpeg  # 人脸照片
```

**不同人照片** (different_person目录):
```
任意命名.jpg 或 .jpeg
```

---

## 二、数据准备工具 (prepare_data.py)

### 功能说明

从原始照片库中提取训练数据，用于ROC曲线分析。

### 主要函数

| 函数名 | 功能描述 |
|--------|----------|
| `prepare_same_person_data()` | 提取同一人照片配对 |
| `prepare_different_person_data()` | 提取不同人照片 |

### 数据来源

从 `all_photo` 目录读取原始照片，按命名规则自动匹配。

### 运行方式

```bash
python prepare_data.py
```

交互式菜单：
```
1. 准备同一人照片数据（same_person）
2. 准备不同人照片数据（different_person）
3. 同时准备两种数据
```

### 输出目录

- **same_person/**: 同一人配对照片（每对2张）
- **different_person/**: 不同人照片（用于配对比较）

---

## 三、核心功能实现 (face_similarity.py)

### 功能说明

实现人脸相似度分析的核心功能，包括人脸检测、身份验证、黑名单检查、批量处理和可视化输出。

### 核心功能

| 功能 | 函数 | 说明 |
|------|------|------|
| 人脸检测 | `has_face(image_path)` | 判断图片中是否有人脸 |
| 身份验证 | `verify_identity(id_card, face, threshold)` | 比对身份证与人脸照片 |
| 黑名单检查 | `check_blacklist(face, blacklist, threshold)` | 检查是否在黑名单中 |
| 特征提取 | `extract_face_features(image_path)` | 提取人脸特征向量 |
| 特征更新 | `get_or_update_features(image_dir, feature_file)` | 自动检测目录变化更新特征 |

### 配置参数

```python
MODEL_NAME = 'buffalo_l'              # 模型：buffalo_l(高精度)/buffalo_s(轻量)
DEVICE_ID = -1                        # 设备：-1=CPU, 0=GPU
DET_THRESH = 0.5                      # 人脸检测置信度阈值
INPUT_SIZE = (640, 640)               # 检测输入尺寸

ID_CARD_FACE_THRESHOLD = 0.60         # 身份证与人脸比对阈值
BLACKLIST_THRESHOLD = 0.65            # 黑名单比对阈值
```

### 主要函数详解

#### 特征提取与更新

```python
def extract_face_features(image_path):
    """
    提取人脸特征向量
    参数: image_path - 图片路径
    返回: (embedding, bbox) - (特征向量, 人脸框坐标)
    """

def get_or_update_features(image_dir, feature_file, force_update=False):
    """
    获取或更新特征文件，自动检测目录变化
    - 检测新增/删除文件
    - 有变化时自动重新提取
    - 无变化时直接加载缓存
    """
```

#### 人脸检测

```python
def has_face(image_path):
    """
    判断图片中是否有人脸
    参数: image_path - 图片路径
    返回: bool - 是否检测到人脸
    """
```

#### 身份验证

```python
def verify_identity(id_card_image_path, face_image_path, threshold=0.60):
    """
    验证身份证与人脸照片是否同一人
    参数:
        id_card_image_path: 身份证正面路径
        face_image_path: 人脸照片路径
        threshold: 相似度阈值
    返回: (is_same_person, similarity)
    """
```

#### 黑名单检查

```python
def check_blacklist(face_image_path, blacklist_features, threshold=0.65):
    """
    检查人脸是否在黑名单中
    参数:
        face_image_path: 待检测人脸照片
        blacklist_features: 黑名单特征字典
        threshold: 相似度阈值
    返回: (is_in_blacklist, matched_name, similarity)
    """
```

#### 批量处理

```python
def batch_process_users(users_data, blacklist_features):
    """
    批量处理多个用户
    参数:
        users_data: 用户数据列表
        blacklist_features: 黑名单特征
    返回: dict - 所有用户的处理结果
    """

def auto_scan_and_process_users(base_folder, blacklist_features):
    """
    自动扫描文件夹并批量处理
    支持子文件夹结构和平铺文件结构
    """
```

#### 可视化输出

```python
def visualize_user_result(user_id, id_card_front_path, face_photo_path, result):
    """
    可视化单个用户的处理结果
    - 显示身份证和人脸照片
    - 显示人脸检测结果
    - 显示身份验证结果
    - 显示黑名单检查结果（命中时红色高亮）
    """

def visualize_batch_results(all_results, users_data):
    """
    可视化批量处理结果
    - 生成每个用户的可视化结果
    - 生成汇总统计报告
    """
```

### 运行方式

```bash
python face_similarity.py
```

### 目录结构要求

```
photos/
├── {用户ID}_card_front.jpeg      # 身份证正面
├── {用户ID}_face_photo_list.jpeg # 人脸照片
└── ...

blacklist/
├── 黑名单用户1.jpg
├── 黑名单用户2.jpg
└── ...
```

### 输出结果

```
output/
├── user_{用户ID}/
│   └── result_{用户ID}.jpg    # 单用户处理结果图
├── batch_report/
│   └── batch_report.jpg       # 批量处理汇总报告
└── ...
```

---

## 四、API服务接口 (face_api.py)

### 功能说明

提供JSON格式的API接口，支持系统集成。包含自动特征更新功能。

### 主要函数

| 函数名 | 功能描述 |
|--------|----------|
| `process_request(request_data)` | 处理API请求 |
| `get_or_update_features(image_dir, feature_file)` | 自动检测更新黑名单特征 |
| `batch_extract(image_folder, save_path)` | 批量提取特征 |

### 请求格式

```json
{
    "order_id": "ORDER_001",
    "check_face": true,
    "verify_identity": true,
    "check_blacklist": true,
    "id_card_front": "./photos/588391_card_front.jpeg",
    "face_photo": "./photos/588391_face_photo_list.jpeg"
}
```

### 请求参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | string | 否 | 订单号，用于追踪 |
| check_face | bool | 否 | 是否执行人脸检测 |
| verify_identity | bool | 否 | 是否执行身份验证 |
| check_blacklist | bool | 否 | 是否执行黑名单检查 |
| id_card_front | string | 条件必填 | 身份证正面路径 |
| face_photo | string | 条件必填 | 人脸照片路径 |

### 响应格式

```json
{
    "order_id": "ORDER_001",
    "success": true,
    "message": "处理成功",
    "data": {
        "face_detection": {
            "id_card_face_detected": true,
            "face_photo_detected": true
        },
        "identity_verification": {
            "verified": true,
            "similarity": 0.6234,
            "message": "验证成功"
        },
        "blacklist_check": {
            "in_blacklist": false,
            "matched_name": "",
            "similarity": 0.1234,
            "message": "检查成功"
        }
    }
}
```

### 运行方式

**方式一：标准输入**

```bash
echo '{"order_id":"001","verify_identity":true,"id_card_front":"./photos/588391_card_front.jpeg","face_photo":"./photos/588391_face_photo_list.jpeg"}' | python face_api.py
```

**方式二：文件输入**

```bash
python face_api.py < request.json
```

**方式三：代码调用**

```python
import json
from face_api import process_request

request_data = {
    "order_id": "ORDER_001",
    "verify_identity": True,
    "id_card_front": "./photos/588391_card_front.jpeg",
    "face_photo": "./photos/588391_face_photo_list.jpeg"
}

result = process_request(request_data)
print(json.dumps(result, ensure_ascii=False, indent=2))
```

---

## 五、阈值选择指南

### 相似度范围

InsightFace 使用余弦相似度，范围：**-1 到 1**

| 相似度范围 | 含义 |
|------------|------|
| > 0.7 | 大概率是同一人 |
| 0.5 - 0.7 | 需要进一步确认 |
| < 0.5 | 大概率不是同一人 |

### 场景推荐阈值

| 应用场景 | 推荐阈值 | 说明 |
|----------|----------|------|
| 金融支付 | ≥ 0.70 | 极高安全性，宁可拒绝 |
| 银行开户 | ≥ 0.65 | 高安全性要求 |
| 门禁考勤 | ≥ 0.55 | 平衡安全与便利 |
| 社交应用 | ≥ 0.45 | 注重用户体验 |

### 如何选择阈值

1. 运行 `roc_analysis.py` 获取ROC分析结果
2. 查看 `output/roc_curve.png` 中的阈值表格
3. 根据业务场景选择合适的FAR要求
4. 在 `face_similarity.py` 中修改阈值配置

---

## 六、技术架构

### 模型说明

- **模型**: InsightFace buffalo_l
- **特征维度**: 512维向量
- **相似度计算**: 余弦相似度（点积）
- **人脸检测**: 基于深度学习的多任务人脸检测

### 依赖库

```
insightface
opencv-python
numpy
scikit-learn
matplotlib
Pillow
```

### 性能指标

- **AUC**: ~0.95（优秀）
- **人脸检测速度**: ~50ms/张（CPU）
- **特征提取速度**: ~30ms/张（CPU）

---

## 七、使用流程

### 完整流程

```
1. 准备数据
   └── python prepare_data.py

2. 分析阈值
   └── python roc_analysis.py
   └── 查看 output/roc_curve.png 选择阈值

3. 配置阈值
   └── 修改 face_similarity.py 中的阈值参数

4. 运行功能
   └── python face_similarity.py

5. API集成
   └── 使用 face_api.py 进行系统对接
```

### 快速开始

```bash
# 1. 安装依赖
pip install insightface opencv-python numpy scikit-learn matplotlib Pillow

# 2. 准备照片到 photos/ 目录

# 3. 运行核心功能
python face_similarity.py

# 4. API调用
echo '{"verify_identity":true,"id_card_front":"./photos/test_card_front.jpeg","face_photo":"./photos/test_face_photo.jpeg"}' | python face_api.py
```

---

## 八、系统优化建议

### 数据采集规范

**前端引导**

- 清晰度提示：前端提示"请确保脸部清晰、光线均匀"
- 拍摄引导：提供人脸框引导，帮助用户对准位置
- 实时预览：上传前显示预览，让用户确认照片质量

**自动质量检测**

| 质量指标 | 要求 | 不合格提示 |
|----------|------|------------|
| 人脸检测得分 | ≥ 0.8 | "未检测到清晰人脸，请重新拍摄" |
| 人脸尺寸 | ≥ 图片20% | "人脸过小，请靠近摄像头" |
| 模糊度 | 清晰度评分 ≥ 60 | "照片模糊，请保持稳定" |
| 光照 | 均匀无阴影 | "光线不均匀，请调整光源" |

### 多维度综合判断

**结合证件信息**

| OCR匹配 | 人脸相似度 | 判定结果 |
|---------|------------|----------|
| ✅ 匹配 | ≥ 0.60 | 自动通过 |
| ✅ 匹配 | 0.40 - 0.60 | 人工复核 |
| ❌ 不匹配 | 任意 | 自动拒绝 |
| ⚠️ 无法识别 | ≥ 0.70 | 自动通过 |
| ⚠️ 无法识别 | < 0.70 | 人工复核 |

**活体检测**

| 检测方式 | 说明 | 实现难度 |
|----------|------|----------|
| 眨眼检测 | 要求用户眨眼 | 低 |
| 张嘴检测 | 要求用户张嘴 | 低 |
| 点头摇头 | 要求用户做动作 | 中 |
| 3D深度检测 | 使用深度摄像头 | 高 |

### 黑名单管理

**定期更新机制**

| 照片年龄 | 处理方式 |
|----------|----------|
| 0-6个月 | 正常使用 |
| 6-12个月 | 标记警告，建议更新 |
| > 12个月 | 降低匹配权重，强制更新提醒 |

**多人脸注册**

| 照片类型 | 数量 | 说明 |
|----------|------|------|
| 正面照 | 1-2张 | 标准证件照 |
| 生活照 | 1-2张 | 不同角度、表情 |
| 历史照片 | 1张 | 较早时期的照片 |

### 阈值动态调整

**场景化阈值配置**

| 场景 | 阈值 | 说明 |
|------|------|------|
| 登录 | 0.50 | 注重用户体验 |
| 支付 | 0.65 | 高安全性要求 |
| 注册 | 0.55 | 平衡安全与便利 |
| 黑名单 | 0.70 | 宁可漏检不可误报 |

**监控指标**

| 指标 | 计算方式 | 目标值 |
|------|----------|--------|
| FAR（误识率） | 错误接受数 / 总负样本数 | < 0.1% |
| FRR（拒识率） | 错误拒绝数 / 总正样本数 | < 5% |
| 通过率 | 自动通过数 / 总请求数 | > 90% |
| 人工复核率 | 人工复核数 / 总请求数 | < 10% |

### 人工复核机制

**可疑队列设置**

```
相似度 < 0.30  →  自动拒绝
相似度 0.30-0.60  →  人工复核队列
相似度 ≥ 0.60  →  自动通过
```

**反馈数据用途**

| 用途 | 说明 |
|------|------|
| 训练数据扩充 | 人工确认的样本可作为新训练数据 |
| 阈值优化 | 根据反馈调整阈值 |
| 模型迭代 | 用于模型微调 |
| 审计追溯 | 记录所有人工决策 |

---

## 九、系统优缺点分析

### 优点

| 优点 | 说明 |
|------|------|
| ✅ 高精度模型 | 使用InsightFace buffalo_l模型，AUC达0.95 |
| ✅ 灵活阈值配置 | 支持不同场景的阈值设置 |
| ✅ 自动特征更新 | 检测目录变化自动更新特征文件 |
| ✅ 批量处理能力 | 支持批量处理和自动扫描 |
| ✅ 可视化输出 | 生成带标注的结果图片，黑名单命中红色高亮 |
| ✅ API接口完善 | JSON格式接口，易于系统集成 |
| ✅ ROC分析支持 | 提供阈值优化工具 |

### 缺点与改进方向

| 缺点 | 改进建议 |
|------|----------|
| ❌ 无活体检测 | 增加眨眼、张嘴等活体检测功能 |
| ❌ 无OCR集成 | 集成身份证OCR，多维度验证 |
| ❌ 单一阈值 | 实现场景化动态阈值配置 |
| ❌ 无质量检测 | 增加图片质量自动检测 |
| ❌ 黑名单管理简单 | 增加多照片注册、时效管理 |
| ❌ 无人工复核流程 | 增加可疑队列和反馈机制 |
| ❌ 无A/B测试 | 增加阈值A/B测试框架 |
| ❌ CPU性能瓶颈 | 支持GPU加速，优化推理速度 |
| ❌ 无日志审计 | 增加操作日志和审计功能 |
| ❌ 无分布式支持 | 增加分布式部署能力 |

### 性能优化建议

| 优化方向 | 具体措施 |
|----------|----------|
| 推理加速 | 使用GPU、TensorRT、ONNX优化 |
| 批量处理 | 支持批量推理，减少模型加载开销 |
| 缓存优化 | 特征向量缓存，避免重复计算 |
| 异步处理 | 使用消息队列异步处理请求 |
| 负载均衡 | 多实例部署，负载均衡 |

### 安全性建议

| 安全措施 | 说明 |
|----------|------|
| 数据加密 | 特征文件加密存储 |
| 传输安全 | API使用HTTPS加密传输 |
| 访问控制 | 增加API鉴权机制 |
| 日志审计 | 记录所有操作日志 |
| 隐私保护 | 敏感信息脱敏处理 |

---

## 十、版本规划

### v1.0（当前版本）

- ✅ 基础人脸检测和比对
- ✅ 黑名单检查
- ✅ ROC曲线分析
- ✅ API接口
- ✅ 自动特征更新
- ✅ 可视化输出（含黑名单高亮）

### v1.1（计划中）

- 📋 图片质量检测
- 📋 场景化阈值配置
- 📋 黑名单多照片支持

### v1.2（计划中）

- 📋 活体检测
- 📋 OCR集成
- 📋 人工复核队列

### v2.0（远期规划）

- 📋 GPU加速
- 📋 分布式部署
- 📋 模型微调平台
