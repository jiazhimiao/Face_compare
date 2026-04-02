import os
import pickle
import numpy as np
import cv2
from insightface.app import FaceAnalysis
from pathlib import Path
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from collections import defaultdict

# ==================== 配置部分 ====================
MODEL_NAME = 'buffalo_l'
DEVICE_ID = -1
DET_THRESH = 0.5
INPUT_SIZE = (640, 640)
FEATURE_DIR = './features'
OUTPUT_DIR = './output'
SAME_PERSON_DIR = './same_person'      # 同一人照片目录
DIFFERENT_PERSON_DIR = './different_person'  # 不同人照片目录

# 数据集大小配置（可调整）
MAX_SAME_PERSON_PAIRS = 200    # 同一人配对数量（每对2张照片，共400张）
MAX_DIFFERENT_PERSON_PAIRS = 200  # 不同人配对数量（每对2张照片，共400张）
# 设置为 None 表示使用全部数据，设置为数字表示使用指定数量的配对

# 全局变量
app = None

# 初始化模型
def init_model():
    global app
    try:
        app = FaceAnalysis(name=MODEL_NAME, root='~/.insightface')
        app.prepare(ctx_id=DEVICE_ID, det_thresh=DET_THRESH, det_size=INPUT_SIZE)
        print("模型初始化成功！")
        return True
    except Exception as e:
        print(f"模型初始化失败: {e}")
        return False

def extract_face_features(image_path):
    global app
    if app is None:
        return None, None
    
    img = cv2.imread(image_path)
    if img is None:
        return None, None
    
    try:
        faces = app.get(img)
        if len(faces) == 0:
            return None, None

        largest_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
        embedding = largest_face.normed_embedding
        bbox = largest_face.bbox.astype(int).tolist()
        return embedding, bbox
    except Exception as e:
        return None, None

def calculate_similarity(emb1, emb2):
    """计算两个特征向量的余弦相似度"""
    return np.dot(emb1, emb2)

def prepare_dataset(same_dir, different_dir):
    """
    准备数据集
    返回: (same_pairs, different_pairs)
        same_pairs: [(emb1, emb2, label=1, similarity, file1, file2), ...] 同一人对
        different_pairs: [(emb1, emb2, label=0, similarity, file1, file2), ...] 不同人对
    """
    print("正在准备数据集...")
    print(f"\n配置参数:")
    print(f"  同一人配对数量: {MAX_SAME_PERSON_PAIRS if MAX_SAME_PERSON_PAIRS else '全部'}")
    print(f"  不同人配对数量: {MAX_DIFFERENT_PERSON_PAIRS if MAX_DIFFERENT_PERSON_PAIRS else '全部'}")
    
    # 处理同一人照片
    same_pairs = []
    same_files = list(Path(same_dir).glob('*.jpg')) + list(Path(same_dir).glob('*.jpeg'))
    
    # 根据用户ID分组照片
    user_photos = {}
    for file_path in same_files:
        file_name = file_path.name
        # 提取用户ID（文件名格式：{用户ID}_card_front.jpeg 或 {用户ID}_face_photo_list.jpeg）
        user_id = file_name.split('_')[0]
        
        if user_id not in user_photos:
            user_photos[user_id] = {}
        
        if '_card_front' in file_name:
            user_photos[user_id]['card_front'] = file_path
        elif '_face_photo_list' in file_name:
            user_photos[user_id]['face_photo'] = file_path
    
    # 筛选同时有身份证正面和人脸照片的用户
    valid_users = []
    for user_id, photos in user_photos.items():
        if 'card_front' in photos and 'face_photo' in photos:
            valid_users.append(user_id)
    
    # 根据配置限制用户数量
    if MAX_SAME_PERSON_PAIRS is not None:
        valid_users = valid_users[:MAX_SAME_PERSON_PAIRS]
    
    print(f"\n找到 {len(valid_users)} 个有效的同一人配对")
    print(f"开始处理同一人照片配对...")
    
    # 为同一人创建配对
    total_pairs = len(valid_users)
    for idx, user_id in enumerate(valid_users, 1):
        photos = user_photos[user_id]
        card_front = photos['card_front']
        face_photo = photos['face_photo']
        
        print(f"\n[{idx}/{total_pairs}] 处理同一人配对 (用户ID: {user_id}):")
        print(f"  身份证正面: {card_front.name}")
        print(f"  人脸照片: {face_photo.name}")
        
        emb1, bbox1 = extract_face_features(str(card_front))
        emb2, bbox2 = extract_face_features(str(face_photo))
        
        if emb1 is not None and emb2 is not None:
            similarity = calculate_similarity(emb1, emb2)
            same_pairs.append((emb1, emb2, 1, similarity, card_front.name, face_photo.name))
            print(f"  ✓ 相似度: {similarity:.4f} (标签: 1-同一人)")
        else:
            print(f"  ✗ 跳过: 无法提取人脸特征")
        
        # 显示进度
        if idx % 10 == 0:
            progress = (idx / total_pairs) * 100
            print(f"\n进度: {progress:.1f}% ({idx}/{total_pairs})")
    
    print(f"\n创建了 {len(same_pairs)} 对同一人配对")
    
    # 处理不同人照片
    different_pairs = []
    different_files = list(Path(different_dir).glob('*.jpg')) + list(Path(different_dir).glob('*.jpeg'))
    
    # 根据配置限制照片数量
    if MAX_DIFFERENT_PERSON_PAIRS is not None:
        max_files = MAX_DIFFERENT_PERSON_PAIRS * 2  # 每对需要2张照片
        different_files = different_files[:max_files]
    
    print(f"\n找到 {len(different_files)} 张不同人照片")
    print(f"开始处理不同人照片配对...")
    
    # 为不同人创建配对
    total_pairs = len(different_files) // 2
    for i in range(0, len(different_files), 2):
        if i+1 >= len(different_files):
            break
        
        current_pair = (i // 2) + 1
        file1 = different_files[i]
        file2 = different_files[i+1]
        
        print(f"\n[{current_pair}/{total_pairs}] 处理不同人配对:")
        print(f"  照片1: {file1.name}")
        print(f"  照片2: {file2.name}")
        
        emb1, bbox1 = extract_face_features(str(file1))
        emb2, bbox2 = extract_face_features(str(file2))
        
        if emb1 is not None and emb2 is not None:
            similarity = calculate_similarity(emb1, emb2)
            different_pairs.append((emb1, emb2, 0, similarity, file1.name, file2.name))
            print(f"  ✓ 相似度: {similarity:.4f} (标签: 0-不同人)")
        else:
            print(f"  ✗ 跳过: 无法提取人脸特征")
        
        # 显示进度
        if current_pair % 10 == 0:
            progress = (current_pair / total_pairs) * 100
            print(f"\n进度: {progress:.1f}% ({current_pair}/{total_pairs})")
    
    print(f"\n创建了 {len(different_pairs)} 对不同人配对")
    
    return same_pairs, different_pairs

def analyze_roc(same_pairs, different_pairs):
    """
    分析ROC曲线
    返回: (fpr, tpr, thresholds, auc_score, optimal_thresholds)
    """
    print("\n正在分析ROC曲线...")
    
    # 合并所有配对
    all_pairs = same_pairs + different_pairs
    
    # 提取标签和相似度
    labels = np.array([pair[2] for pair in all_pairs])
    similarities = np.array([pair[3] for pair in all_pairs])
    
    print(f"\n数据集统计:")
    print(f"  总配对数: {len(all_pairs)}")
    print(f"  同一人配对: {len(same_pairs)} (正样本)")
    print(f"  不同人配对: {len(different_pairs)} (负样本)")
    
    # 显示相似度分布
    same_similarities = [pair[3] for pair in same_pairs]
    different_similarities = [pair[3] for pair in different_pairs]
    
    print(f"\n相似度分布:")
    print(f"  同一人配对:")
    print(f"    平均相似度: {np.mean(same_similarities):.4f}")
    print(f"    最小相似度: {np.min(same_similarities):.4f}")
    print(f"    最大相似度: {np.max(same_similarities):.4f}")
    print(f"    标准差: {np.std(same_similarities):.4f}")
    
    print(f"  不同人配对:")
    print(f"    平均相似度: {np.mean(different_similarities):.4f}")
    print(f"    最小相似度: {np.min(different_similarities):.4f}")
    print(f"    最大相似度: {np.max(different_similarities):.4f}")
    print(f"    标准差: {np.std(different_similarities):.4f}")
    
    # 计算ROC曲线
    fpr, tpr, thresholds = roc_curve(labels, similarities)
    auc_score = auc(fpr, tpr)
    
    print(f"\n模型性能:")
    print(f"  AUC分数: {auc_score:.4f}")
    print(f"  (AUC越接近1.0，模型性能越好)")
    
    # 过滤掉inf和-inf的阈值
    valid_indices = np.isfinite(thresholds)
    valid_thresholds = thresholds[valid_indices]
    valid_fpr = fpr[valid_indices]
    valid_tpr = tpr[valid_indices]
    
    if len(valid_thresholds) == 0:
        print("\n警告：无法计算有效的阈值！")
        print("可能原因：")
        print("  1. 数据量太少（建议至少100对照片）")
        print("  2. 所有相似度都相同或非常接近")
        print("  3. 数据质量问题")
        print("\n建议：增加数据量或检查数据质量")
        return fpr, tpr, thresholds, auc_score, {}
    
    print(f"\n阈值范围:")
    print(f"  最小阈值: {np.min(valid_thresholds):.4f}")
    print(f"  最大阈值: {np.max(valid_thresholds):.4f}")
    print(f"  有效阈值数量: {len(valid_thresholds)}")
    
    # 计算不同FAR要求下的最优阈值
    print(f"\n阈值设置说明:")
    print(f"  FAR (False Accept Rate): 误识率，即错误接受不同人的概率")
    print(f"  TPR (True Positive Rate): 通过率，即正确接受同一人的概率")
    print(f"  阈值越高，安全性越高，但通过率越低")
    print(f"  阈值越低，通过率越高，但安全性越低")
    
    optimal_thresholds = {}
    
    # FAR = 1e-4 (高安全场景，如金融支付)
    print(f"\n1. 高安全场景（金融支付、银行开户）:")
    print(f"   要求: FAR ≤ 0.0001 (万分之一误识率)")
    print(f"   说明: 极高的安全性要求，宁可拒绝合法用户，也不能接受非法用户")
    
    # 检查是否有足够的FPR范围
    if np.min(valid_fpr) <= 1e-4 <= np.max(valid_fpr):
        far_1e4_idx = np.argmin(np.abs(valid_fpr - 1e-4))
        optimal_thresholds['FAR_1e-4'] = {
            'threshold': valid_thresholds[far_1e4_idx],
            'tpr': valid_tpr[far_1e4_idx],
            'fpr': valid_fpr[far_1e4_idx],
            'description': '高安全场景（金融支付）'
        }
        print(f"   推荐阈值: {valid_thresholds[far_1e4_idx]:.4f}")
        print(f"   通过率: {valid_tpr[far_1e4_idx]:.4f} ({valid_tpr[far_1e4_idx]*100:.2f}%)")
        print(f"   误识率: {valid_fpr[far_1e4_idx]:.6f} ({valid_fpr[far_1e4_idx]*100:.4f}%)")
    else:
        print(f"   ⚠️  警告: 当前数据无法满足FAR ≤ 0.0001的要求")
        print(f"   当前FPR范围: [{np.min(valid_fpr):.6f}, {np.max(valid_fpr):.6f}]")
        print(f"   建议: 增加数据量以获得更准确的阈值")
    
    # FAR = 1e-3 (中等安全场景，如门禁）
    print(f"\n2. 中等安全场景（门禁系统、考勤系统）:")
    print(f"   要求: FAR ≤ 0.001 (千分之一误识率)")
    print(f"   说明: 平衡安全性和便利性，适合日常使用")
    
    if np.min(valid_fpr) <= 1e-3 <= np.max(valid_fpr):
        far_1e3_idx = np.argmin(np.abs(valid_fpr - 1e-3))
        optimal_thresholds['FAR_1e-3'] = {
            'threshold': valid_thresholds[far_1e3_idx],
            'tpr': valid_tpr[far_1e3_idx],
            'fpr': valid_fpr[far_1e3_idx],
            'description': '中等安全场景（门禁）'
        }
        print(f"   推荐阈值: {valid_thresholds[far_1e3_idx]:.4f}")
        print(f"   通过率: {valid_tpr[far_1e3_idx]:.4f} ({valid_tpr[far_1e3_idx]*100:.2f}%)")
        print(f"   误识率: {valid_fpr[far_1e3_idx]:.6f} ({valid_fpr[far_1e3_idx]*100:.4f}%)")
    else:
        print(f"   ⚠️  警告: 当前数据无法满足FAR ≤ 0.001的要求")
        print(f"   当前FPR范围: [{np.min(valid_fpr):.6f}, {np.max(valid_fpr):.6f}]")
        print(f"   建议: 增加数据量以获得更准确的阈值")
    
    # FAR = 1e-2 (一般安全场景)
    print(f"\n3. 一般安全场景（社交应用、一般身份验证）:")
    print(f"   要求: FAR ≤ 0.01 (百分之一误识率)")
    print(f"   说明: 注重用户体验，允许一定的误识")
    
    if np.min(valid_fpr) <= 1e-2 <= np.max(valid_fpr):
        far_1e2_idx = np.argmin(np.abs(valid_fpr - 1e-2))
        optimal_thresholds['FAR_1e-2'] = {
            'threshold': valid_thresholds[far_1e2_idx],
            'tpr': valid_tpr[far_1e2_idx],
            'fpr': valid_fpr[far_1e2_idx],
            'description': '一般安全场景'
        }
        print(f"   推荐阈值: {valid_thresholds[far_1e2_idx]:.4f}")
        print(f"   通过率: {valid_tpr[far_1e2_idx]:.4f} ({valid_tpr[far_1e2_idx]*100:.2f}%)")
        print(f"   误识率: {valid_fpr[far_1e2_idx]:.6f} ({valid_fpr[far_1e2_idx]*100:.4f}%)")
    else:
        print(f"   ⚠️  警告: 当前数据无法满足FAR ≤ 0.01的要求")
        print(f"   当前FPR范围: [{np.min(valid_fpr):.6f}, {np.max(valid_fpr):.6f}]")
        print(f"   建议: 增加数据量以获得更准确的阈值")
    
    # Youden指数（平衡点）
    print(f"\n4. 平衡点（Youden指数）:")
    print(f"   要求: 最大化 TPR + (1 - FAR)")
    print(f"   说明: 自动找到最优平衡点，平衡误识率和通过率")
    youden_idx = np.argmax(valid_tpr - valid_fpr)
    optimal_thresholds['Youden'] = {
        'threshold': valid_thresholds[youden_idx],
        'tpr': valid_tpr[youden_idx],
        'fpr': valid_fpr[youden_idx],
        'description': '平衡点（Youden指数）'
    }
    print(f"   推荐阈值: {valid_thresholds[youden_idx]:.4f}")
    print(f"   通过率: {valid_tpr[youden_idx]:.4f} ({valid_tpr[youden_idx]*100:.2f}%)")
    print(f"   误识率: {valid_fpr[youden_idx]:.6f} ({valid_fpr[youden_idx]*100:.4f}%)")
    
    return fpr, tpr, thresholds, auc_score, optimal_thresholds

def plot_roc_curve(fpr, tpr, thresholds, auc_score, optimal_thresholds, output_path):
    """
    绘制ROC曲线
    """
    print("正在绘制ROC曲线...")
    
    # 设置中文字体
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
    except:
        pass
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 左图：ROC曲线
    ax1.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC Curve (AUC = {auc_score:.4f})')
    ax1.plot([0, 1], [0, 1], color='navy', lw=1, linestyle='--')
    
    # 标记最优阈值点
    colors = ['red', 'blue', 'green', 'purple']
    markers = ['o', 's', '^', 'D']
    
    descriptions = {
        'FAR_1e-4': 'High Security (Fintech)',
        'FAR_1e-3': 'Medium Security (Access Control)',
        'FAR_1e-2': 'General Security',
        'Youden': 'Balance Point'
    }
    
    for idx, (key, opt_threshold) in enumerate(optimal_thresholds.items()):
        desc = descriptions.get(key, key)
        ax1.scatter(opt_threshold['fpr'], opt_threshold['tpr'], 
                   color=colors[idx], marker=markers[idx], s=100, 
                   label=f"{key}: threshold={opt_threshold['threshold']:.3f} ({desc})")
    
    ax1.set_xlim([0.0, 0.1])
    ax1.set_ylim([0.0, 1.05])
    ax1.set_xlabel('False Accept Rate (FAR)', fontsize=12)
    ax1.set_ylabel('True Accept Rate (TPR)', fontsize=12)
    ax1.set_title('Face Similarity ROC Curve Analysis', fontsize=14, fontweight='bold')
    ax1.legend(loc="lower right", fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # 添加参考线
    ax1.axvline(x=1e-4, color='red', linestyle=':', alpha=0.5)
    ax1.axvline(x=1e-3, color='blue', linestyle=':', alpha=0.5)
    
    # 右图：阈值表格
    ax2.axis('off')
    ax2.set_title('Threshold Performance Table', fontsize=14, fontweight='bold', pad=20)
    
    # 创建表格数据
    table_data = []
    headers = ['Threshold', 'TPR (%)', 'FAR (%)', 'Description']
    
    # 添加关键阈值点
    for key, opt in optimal_thresholds.items():
        table_data.append([
            f"{opt['threshold']:.4f}",
            f"{opt['tpr']*100:.2f}%",
            f"{opt['fpr']*100:.4f}%",
            opt['description']
        ])
    
    # 添加更多阈值点（从ROC曲线中选取）
    valid_indices = np.isfinite(thresholds)
    valid_thresholds = thresholds[valid_indices]
    valid_fpr = fpr[valid_indices]
    valid_tpr = tpr[valid_indices]
    
    # 选择一些代表性的阈值点
    sample_indices = np.linspace(0, len(valid_thresholds)-1, 10, dtype=int)
    for idx in sample_indices:
        threshold = valid_thresholds[idx]
        tpr_val = valid_tpr[idx]
        fpr_val = valid_fpr[idx]
        
        # 跳过已经在optimal_thresholds中的点
        is_duplicate = False
        for opt in optimal_thresholds.values():
            if abs(threshold - opt['threshold']) < 0.001:
                is_duplicate = True
                break
        
        if not is_duplicate:
            table_data.append([
                f"{threshold:.4f}",
                f"{tpr_val*100:.2f}%",
                f"{fpr_val*100:.4f}%",
                ''
            ])
    
    # 按阈值排序
    table_data.sort(key=lambda x: float(x[0]), reverse=True)
    
    # 绘制表格
    table = ax2.table(cellText=table_data, colLabels=headers, 
                     loc='center', cellLoc='center',
                     colWidths=[0.2, 0.15, 0.15, 0.35])
    
    # 设置表格样式
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    
    # 设置表头颜色
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#404666')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # 设置关键阈值点的颜色
    for i in range(len(optimal_thresholds)):
        for j in range(len(headers)):
            if i < len(table_data):
                table[(i+1, j)].set_facecolor('#f0f0f0')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"ROC曲线已保存至: {output_path}")
    
    # 打印阈值建议
    print("\n=== 阈值建议 ===")
    for key, opt_threshold in optimal_thresholds.items():
        print(f"{key}:")
        print(f"  阈值: {opt_threshold['threshold']:.4f}")
        print(f"  通过率: {opt_threshold['tpr']:.4f}")
        print(f"  误识率: {opt_threshold['fpr']:.4f}")
        print(f"  描述: {opt_threshold['description']}")
        print()

def save_results(fpr, tpr, thresholds, auc_score, optimal_thresholds, output_path):
    """
    保存分析结果到文件
    """
    results = {
        'auc_score': float(auc_score),
        'optimal_thresholds': {
            key: {
                'threshold': float(value['threshold']),
                'tpr': float(value['tpr']),
                'fpr': float(value['fpr']),
                'description': value['description']
            }
            for key, value in optimal_thresholds.items()
        },
        'threshold_analysis': [
            {
                'threshold': float(threshold),
                'tpr': float(tpr),
                'fpr': float(fpr)
            }
            for threshold, tpr, fpr in zip(thresholds, tpr, fpr)
        ]
    }
    
    # 保存为JSON
    import json
    json_path = output_path.replace('.png', '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"分析结果已保存至: {json_path}")

def main():
    """
    主函数
    """
    print("=== 人脸相似度ROC曲线分析工具 ===")
    
    # 1. 初始化模型
    if not init_model():
        print("模型初始化失败，退出程序")
        return
    
    # 2. 检查数据目录
    os.makedirs(SAME_PERSON_DIR, exist_ok=True)
    os.makedirs(DIFFERENT_PERSON_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 3. 准备数据集
    same_pairs, different_pairs = prepare_dataset(SAME_PERSON_DIR, DIFFERENT_PERSON_DIR)
    
    if len(same_pairs) == 0 and len(different_pairs) == 0:
        print("错误：未找到有效的配对数据")
        print("请确保以下目录包含图片：")
        print(f"  同一人照片: {SAME_PERSON_DIR}")
        print(f"  不同人照片: {DIFFERENT_PERSON_DIR}")
        print("文件命名格式：任意名称.jpg 或 .jpeg")
        return
    
    # 4. 分析ROC曲线
    fpr, tpr, thresholds, auc_score, optimal_thresholds = analyze_roc(same_pairs, different_pairs)
    
    # 5. 绘制ROC曲线
    roc_output_path = os.path.join(OUTPUT_DIR, 'roc_curve.png')
    plot_roc_curve(fpr, tpr, thresholds, auc_score, optimal_thresholds, roc_output_path)
    
    # 6. 保存结果
    save_results(fpr, tpr, thresholds, auc_score, optimal_thresholds, roc_output_path)
    
    print("\n=== 分析完成 ===")
    print(f"ROC曲线图: {roc_output_path}")
    print("请查看ROC曲线图以选择合适的阈值")

if __name__ == '__main__':
    main()
