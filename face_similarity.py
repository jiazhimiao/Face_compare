import os
import pickle
import numpy as np
import cv2
from insightface.app import FaceAnalysis
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ==================== 配置部分 ====================
MODEL_NAME = 'buffalo_l'          # 可选 buffalo_l（高精度）、buffalo_s（轻量）,antelopev2
DEVICE_ID = -1                    # -1 表示 CPU，0 表示第一块 GPU
DET_THRESH = 0.5                  # 人脸检测置信度阈值
INPUT_SIZE = (640, 640)           # 检测输入尺寸，越大越准但越慢
FEATURE_DIR = './features'        # 保存特征的目录
OUTPUT_DIR = './output'           # 保存标记后的图片
BLACKLIST_DIR = './blacklist'     # 黑名单照片目录

# 相似度阈值设置
ID_CARD_FACE_THRESHOLD = 0.60     # 身份证与人脸照片比对阈值
BLACKLIST_THRESHOLD = 0.65        # 黑名单比对阈值
# =================================================

# 全局变量
app = None

# 初始化模型
def init_model():
    """
    初始化人脸分析模型
    返回: bool - 初始化是否成功
    """
    global app
    try:
        print(f"初始化 {MODEL_NAME} 模型...")
        app = FaceAnalysis(name=MODEL_NAME, root='~/.insightface')
        app.prepare(ctx_id=DEVICE_ID, det_thresh=DET_THRESH, det_size=INPUT_SIZE)
        print("模型初始化成功！")
        return True
    except Exception as e:
        print(f"模型初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def draw_face_box(image, face, label=None, color=(0,255,0), thickness=2):
    """在图片上绘制人脸框和关键点（可选），并添加标签"""
    bbox = face.bbox.astype(int)
    cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, thickness)
    # 绘制关键点（5个点）
    if hasattr(face, 'kps') and face.kps is not None:
        for x, y in face.kps.astype(int):
            cv2.circle(image, (x, y), 2, (0,255,255), -1)
    # 添加标签
    if label:
        cv2.putText(image, label, (bbox[0], bbox[1]-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    return image
def extract_face_features(image_path):
    """
    从单张图片中提取最大人脸的归一化特征向量。
    返回: (特征向量, 人脸框) 或 (None, None) 如果没有检测到人脸。
    """
    global app
    if app is None:
        print("错误：模型未初始化")
        return None, None
    
    img = cv2.imread(image_path)
    if img is None:
        print(f"无法读取图片: {image_path}")
        return None, None
    
    try:
        faces = app.get(img)
        if len(faces) == 0:
            print(f"未检测到人脸: {image_path}")
            return None, None

        # 选择面积最大的人脸（通常也是主要人脸）
        largest_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
        embedding = largest_face.normed_embedding  # 已经 L2 归一化
        bbox = largest_face.bbox.astype(int).tolist()
        return embedding, bbox
    except Exception as e:
        print(f"提取特征时出错: {e}")
        return None, None

def has_face(image_path):
    """
    判断图片中是否有人脸。
    返回: bool - 如果检测到人脸返回True，否则返回False
    """
    emb, bbox = extract_face_features(image_path)
    return emb is not None

def verify_identity(id_card_image_path, face_image_path, threshold=ID_CARD_FACE_THRESHOLD):
    """
    判断身份证正面和人脸照片是否是同一人。
    参数:
        id_card_image_path: 身份证正面照片路径
        face_image_path: 人脸照片路径
        threshold: 相似度阈值，默认为0.65
    返回: (bool, float) - (是否是同一人, 相似度)
    """
    # 提取身份证上的人脸特征
    id_card_emb, id_card_bbox = extract_face_features(id_card_image_path)
    if id_card_emb is None:
        print("身份证正面未检测到人脸")
        return False, 0.0
    
    # 提取人脸照片的特征
    face_emb, face_bbox = extract_face_features(face_image_path)
    if face_emb is None:
        print("人脸照片未检测到人脸")
        return False, 0.0
    
    # 计算相似度
    similarity = cosine_similarity(id_card_emb, face_emb)
    print(f"身份证与人脸照片的相似度: {similarity:.4f}")
    
    # 根据阈值判断是否是同一人
    is_same_person = similarity >= threshold
    return is_same_person, similarity

def check_blacklist(face_image_path, blacklist_features, threshold=BLACKLIST_THRESHOLD):
    """
    判断人脸是否在黑名单库中。
    参数:
        face_image_path: 待检测人脸照片路径
        blacklist_features: 黑名单人脸特征字典，格式为 {name: (embedding, bbox)}
        threshold: 相似度阈值，默认为BLACKLIST_THRESHOLD
    返回: (bool, str, float) - (是否在黑名单中, 匹配的黑名单名称, 最大相似度)
    """
    # 提取待检测人脸的特征
    face_emb, face_bbox = extract_face_features(face_image_path)
    if face_emb is None:
        print("待检测照片未检测到人脸")
        return False, "", 0.0
    
    # 计算与黑名单中所有人脸的相似度
    max_similarity = 0.0
    matched_name = ""
    
    for name, (emb, bbox) in blacklist_features.items():
        similarity = cosine_similarity(face_emb, emb)
        if similarity > max_similarity:
            max_similarity = similarity
            matched_name = name
    
    print(f"与黑名单的最大相似度: {max_similarity:.4f}")
    
    # 根据阈值判断是否在黑名单中
    is_in_blacklist = max_similarity >= threshold
    return is_in_blacklist, matched_name, max_similarity

def process_user(id_card_front_path, face_photo_path, blacklist_features):
    """
    处理单个用户的照片，包括人脸检测、身份验证和黑名单检查。
    参数:
        id_card_front_path: 身份证正面照片路径
        face_photo_path: 人脸照片路径
        blacklist_features: 黑名单人脸特征字典
    返回: dict - 处理结果
    """
    result = {
        'id_card_face_detected': False,
        'face_photo_face_detected': False,
        'identity_verified': False,
        'identity_similarity': 0.0,
        'in_blacklist': False,
        'blacklist_match': "",
        'blacklist_similarity': 0.0
    }
    
    # 1. 检测身份证正面是否有人脸
    result['id_card_face_detected'] = has_face(id_card_front_path)
    
    # 2. 检测人脸照片是否有人脸
    result['face_photo_face_detected'] = has_face(face_photo_path)
    
    # 3. 验证身份
    if result['id_card_face_detected'] and result['face_photo_face_detected']:
        is_verified, similarity = verify_identity(id_card_front_path, face_photo_path)
        result['identity_verified'] = is_verified
        result['identity_similarity'] = similarity
        
        # 4. 检查黑名单
        is_blacklist, matched_name, blacklist_similarity = check_blacklist(face_photo_path, blacklist_features)
        result['in_blacklist'] = is_blacklist
        result['blacklist_match'] = matched_name
        result['blacklist_similarity'] = blacklist_similarity
    
    return result

def visualize_user_result(user_id, id_card_front_path, face_photo_path, result):
    """
    可视化单个用户的处理结果。
    参数:
        user_id: 用户ID
        id_card_front_path: 身份证正面照片路径
        face_photo_path: 人脸照片路径
        result: 处理结果字典
    """
    # 创建输出目录
    user_output_dir = os.path.join(OUTPUT_DIR, f'user_{user_id}')
    os.makedirs(user_output_dir, exist_ok=True)
    
    # 读取图片
    id_card_img = cv2.imread(id_card_front_path)
    face_img = cv2.imread(face_photo_path)
    
    # 调整图片大小以适合显示
    if id_card_img is not None:
        id_card_img = cv2.resize(id_card_img, (400, 250))
    if face_img is not None:
        face_img = cv2.resize(face_img, (400, 400))
    
    # 创建结果图像（增加高度以显示更多信息）
    result_img = np.ones((620, 900, 3), dtype=np.uint8) * 255
    
    # 放置身份证图片
    if id_card_img is not None:
        result_img[20:270, 20:420] = id_card_img
    
    # 放置人脸照片
    if face_img is not None:
        result_img[20:420, 480:880] = face_img
    
    # 转换为PIL图像以绘制中文
    result_pil = Image.fromarray(cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(result_pil)
    
    # 尝试加载中文字体
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 20)
        except:
            font = ImageFont.load_default()
    
    # 添加文字信息
    text_y = 440
    texts = [
        f"用户ID: {user_id}",
        f"身份证正面人脸检测: {'成功' if result['id_card_face_detected'] else '失败'}",
        f"人脸照片人脸检测: {'成功' if result['face_photo_face_detected'] else '失败'}",
        f"身份验证: {'通过' if result['identity_verified'] else '失败'} (相似度: {result['identity_similarity']:.4f})",
        f"黑名单检查: {'命中黑名单!' if result['in_blacklist'] else '未命中黑名单'}"
    ]
    
    if result['in_blacklist']:
        texts.append(f"匹配的黑名单: {result['blacklist_match']} (相似度: {result['blacklist_similarity']:.4f})")
    
    for text in texts:
        if result['in_blacklist'] and '黑名单检查' in text:
            draw.text((20, text_y), text, font=font, fill=(255, 0, 0))
        else:
            draw.text((20, text_y), text, font=font, fill=(0, 0, 0))
        text_y += 30
    
    # 转换回OpenCV格式
    result_img = cv2.cvtColor(np.array(result_pil), cv2.COLOR_RGB2BGR)
    
    # 保存结果图像
    output_path = os.path.join(user_output_dir, f'result_{user_id}.jpg')
    # 如果文件已存在，先删除
    if os.path.exists(output_path):
        os.remove(output_path)
    cv2.imwrite(output_path, result_img)
    print(f"用户 {user_id} 的处理结果已保存至: {output_path}")

def visualize_batch_results(all_results, users_data):
    """
    可视化批量处理结果。
    参数:
        all_results: 所有用户的处理结果字典
        users_data: 用户数据列表
    """
    # 创建汇总报告目录
    report_dir = os.path.join(OUTPUT_DIR, 'batch_report')
    os.makedirs(report_dir, exist_ok=True)
    
    # 生成每个用户的可视化结果
    for user_data in users_data:
        user_id = user_data.get('id')
        if user_id in all_results:
            id_card_front = user_data.get('id_card_front')
            face_photo = user_data.get('face_photo')
            result = all_results[user_id]
            visualize_user_result(user_id, id_card_front, face_photo, result)
    
    # 生成汇总统计
    total_users = len(all_results)
    identity_verified_count = sum(1 for r in all_results.values() if r['identity_verified'])
    in_blacklist_count = sum(1 for r in all_results.values() if r['in_blacklist'])
    
    # 创建汇总报告图像
    report_img = np.ones((400, 800, 3), dtype=np.uint8) * 255
    
    # 转换为PIL图像以绘制中文
    report_pil = Image.fromarray(cv2.cvtColor(report_img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(report_pil)
    
    # 尝试加载中文字体
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 24)
        except:
            font = ImageFont.load_default()
    
    # 添加汇总信息
    text_y = 50
    texts = [
        "批量处理结果汇总",
        f"总处理用户数: {total_users}",
        f"身份验证通过数: {identity_verified_count}",
        f"黑名单匹配数: {in_blacklist_count}",
        f"身份验证通过率: {identity_verified_count/total_users*100:.1f}%",
        f"黑名单匹配率: {in_blacklist_count/total_users*100:.1f}%"
    ]
    
    for text in texts:
        draw.text((20, text_y), text, font=font, fill=(0, 0, 0))
        text_y += 40
    
    # 转换回OpenCV格式
    report_img = cv2.cvtColor(np.array(report_pil), cv2.COLOR_RGB2BGR)
    
    # 保存汇总报告
    report_path = os.path.join(report_dir, 'batch_report.jpg')
    # 如果文件已存在，先删除
    if os.path.exists(report_path):
        os.remove(report_path)
    cv2.imwrite(report_path, report_img)
    print(f"批量处理汇总报告已保存至: {report_path}")

def batch_process_users(users_data, blacklist_features):
    """
    批量处理多个用户的照片。
    参数:
        users_data: 用户数据列表，每个元素为字典 {'id': 用户ID, 'id_card_front': 身份证正面路径, 'face_photo': 人脸照片路径}
        blacklist_features: 黑名单人脸特征字典
    返回: dict - 所有用户的处理结果，键为用户ID，值为处理结果
    """
    all_results = {}
    
    for user_data in users_data:
        user_id = user_data.get('id')
        id_card_front = user_data.get('id_card_front')
        face_photo = user_data.get('face_photo')
        
        if not user_id or not id_card_front or not face_photo:
            print(f"用户 {user_id} 数据不完整，跳过处理")
            continue
        
        print(f"\n处理用户: {user_id}")
        result = process_user(id_card_front, face_photo, blacklist_features)
        all_results[user_id] = result
        
        # 打印处理结果
        print(f"身份证正面人脸检测: {'成功' if result['id_card_face_detected'] else '失败'}")
        print(f"人脸照片人脸检测: {'成功' if result['face_photo_face_detected'] else '失败'}")
        print(f"身份验证: {'通过' if result['identity_verified'] else '失败'} (相似度: {result['identity_similarity']:.4f})")
        print(f"黑名单检查: {'在黑名单中' if result['in_blacklist'] else '不在黑名单中'}")
        if result['in_blacklist']:
            print(f"匹配的黑名单: {result['blacklist_match']} (相似度: {result['blacklist_similarity']:.4f})")
    
    # 可视化结果
    visualize_batch_results(all_results, users_data)
    
    return all_results

def auto_scan_and_process_users(base_folder, blacklist_features):
    """
    自动扫描文件夹并批量处理所有用户。
    参数:
        base_folder: 基础文件夹路径，包含各个客户的子文件夹
        blacklist_features: 黑名单人脸特征字典
    返回: dict - 所有用户的处理结果
    """
    users_data = []
    
    # 检查是否是子文件夹结构还是平铺文件结构
    has_subfolders = False
    for item in os.listdir(base_folder):
        item_path = os.path.join(base_folder, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            has_subfolders = True
            break
    
    if has_subfolders:
        # 子文件夹结构：每个用户一个子文件夹
        for user_folder in os.listdir(base_folder):
            user_folder_path = os.path.join(base_folder, user_folder)
            
            # 跳过非文件夹
            if not os.path.isdir(user_folder_path):
                continue
            
            # 跳过系统文件夹
            if user_folder.startswith('.'):
                continue
            
            # 扫描用户文件夹中的图片
            id_card_front = None
            face_photo = None
            
            for file_name in os.listdir(user_folder_path):
                file_path = os.path.join(user_folder_path, file_name)
                
                # 跳过非文件
                if not os.path.isfile(file_path):
                    continue
                
                # 根据文件名识别图片类型
                if file_name.endswith('_card_front.jpeg') or file_name.endswith('_card_front.jpg'):
                    id_card_front = file_path
                elif file_name.endswith('_face_photo_list.jpeg') or file_name.endswith('_face_photo_list.jpg'):
                    face_photo = file_path
            
            # 如果找到了身份证正面和人脸照片，添加到用户数据列表
            if id_card_front and face_photo:
                users_data.append({
                    'id': user_folder,
                    'id_card_front': id_card_front,
                    'face_photo': face_photo
                })
                print(f"发现用户: {user_folder}")
                print(f"  身份证正面: {os.path.basename(id_card_front)}")
                print(f"  人脸照片: {os.path.basename(face_photo)}")
            else:
                print(f"用户 {user_folder} 数据不完整，跳过")
                if not id_card_front:
                    print(f"  缺少身份证正面照片")
                if not face_photo:
                    print(f"  缺少人脸照片")
    else:
        # 平铺文件结构：根据文件名前缀分组
        user_files = {}
        
        for file_name in os.listdir(base_folder):
            file_path = os.path.join(base_folder, file_name)
            
            # 跳过非文件
            if not os.path.isfile(file_path):
                continue
            
            # 跳过系统文件
            if file_name.startswith('.'):
                continue
            
            # 提取用户ID（文件名前缀）
            user_id = file_name.split('_')[0]
            
            if user_id not in user_files:
                user_files[user_id] = {}
            
            # 根据文件名识别图片类型
            if file_name.endswith('_card_front.jpeg') or file_name.endswith('_card_front.jpg'):
                user_files[user_id]['id_card_front'] = file_path
            elif file_name.endswith('_face_photo_list.jpeg') or file_name.endswith('_face_photo_list.jpg'):
                user_files[user_id]['face_photo'] = file_path
        
        # 为每个用户创建数据
        for user_id, files in user_files.items():
            id_card_front = files.get('id_card_front')
            face_photo = files.get('face_photo')
            
            if id_card_front and face_photo:
                users_data.append({
                    'id': user_id,
                    'id_card_front': id_card_front,
                    'face_photo': face_photo
                })
                print(f"发现用户: {user_id}")
                print(f"  身份证正面: {os.path.basename(id_card_front)}")
                print(f"  人脸照片: {os.path.basename(face_photo)}")
            else:
                print(f"用户 {user_id} 数据不完整，跳过")
                if not id_card_front:
                    print(f"  缺少身份证正面照片")
                if not face_photo:
                    print(f"  缺少人脸照片")
    
    if not users_data:
        print("未发现完整的用户数据")
        return {}
    
    print(f"\n总共发现 {len(users_data)} 个用户，开始批量处理...")
    
    # 批量处理所有用户
    return batch_process_users(users_data, blacklist_features)

def batch_extract(image_folder, save_path=None):
    """
    批量提取文件夹下所有图片的人脸特征。
    参数:
        image_folder: 包含图片的文件夹路径
        save_path: 保存特征字典的 pickle 文件路径（可选）
    返回:
        features_dict: {文件名: (特征向量, 人脸框)}
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_paths = [p for p in Path(image_folder).iterdir() if p.suffix.lower() in image_extensions]

    features_dict = {}
    for img_path in image_paths:
        emb, bbox = extract_face_features(str(img_path))
        if emb is not None:
            features_dict[img_path.name] = (emb, bbox)
            print(f"已提取: {img_path.name}, 人脸框: {bbox}")

    print(f"\n总共处理 {len(image_paths)} 张图片，成功提取 {len(features_dict)} 张人脸。")

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump(features_dict, f)
        print(f"特征已保存至: {save_path}")

    return features_dict

def load_features(feature_path):
    """从 pickle 文件加载特征字典"""
    try:
        with open(feature_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"加载特征文件时出错: {e}")
        return {}

def get_or_update_features(image_dir, feature_file, force_update=False):
    """
    获取或更新特征文件，自动检测目录变化
    参数:
        image_dir: 图片目录路径
        feature_file: 特征文件路径
        force_update: 是否强制更新
    返回:
        features_dict: 特征字典 {文件名: (特征向量, 人脸框)}
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    
    current_files = set(f for f in os.listdir(image_dir) 
                       if f.lower().endswith(image_extensions) and not f.startswith('.'))
    
    if force_update:
        print(f"强制更新特征文件: {feature_file}")
        return batch_extract(image_dir, save_path=feature_file)
    
    if not os.path.exists(feature_file):
        print(f"特征文件不存在，开始提取: {feature_file}")
        return batch_extract(image_dir, save_path=feature_file)
    
    existing_features = load_features(feature_file)
    existing_files = set(existing_features.keys())
    
    added_files = current_files - existing_files
    removed_files = existing_files - current_files
    
    if added_files or removed_files:
        print(f"检测到目录变化:")
        if added_files:
            print(f"  新增文件: {len(added_files)} 个")
        if removed_files:
            print(f"  删除文件: {len(removed_files)} 个")
        print(f"重新提取特征...")
        return batch_extract(image_dir, save_path=feature_file)
    
    print(f"特征文件已是最新，直接加载: {feature_file}")
    return existing_features

def cosine_similarity(vec1, vec2):
    """计算两个归一化向量的余弦相似度（即点积）"""
    return np.dot(vec1, vec2)

def search_similar(query_image_path, features_dict, top_k=5):
    """
    给定查询图片，在特征库中查找最相似的 top_k 个人脸。
    返回: 列表 [(文件名, 相似度, 人脸框), ...]
    """
    query_emb, query_bbox = extract_face_features(query_image_path)
    if query_emb is None:
        print("查询图片中未检测到人脸，无法匹配。")
        return []

    similarities = []
    for name, (emb, bbox) in features_dict.items():
        sim = cosine_similarity(query_emb, emb)
        similarities.append((name, sim, bbox))

    # 按相似度降序排序
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]

def compute_similarity_matrix(features_dict):
    """
    计算库中所有人脸之间的相似度矩阵（可选）。
    返回: (names, sim_matrix)
        names: 文件名列表（顺序对应矩阵行列）
        sim_matrix: N x N 相似度矩阵
    """
    names = list(features_dict.keys())
    embs = np.array([features_dict[n][0] for n in names])
    # 归一化向量点积 = 余弦相似度
    sim_matrix = np.dot(embs, embs.T)
    return names, sim_matrix
def visualize_query_result(query_image_path, results, features_dict, image_folder, output_path=None):
    """
    将查询图片和 top_k 匹配图片分别绘制人脸框，并拼接显示，或保存单独图片。
    results 格式: [(name, sim, bbox), ...] 来自 search_similar 的返回值。
    """
    global app
    if app is None:
        print("错误：模型未初始化")
        return
    
    # 读取查询图片
    query_img = cv2.imread(query_image_path)
    if query_img is None:
        print("无法读取查询图片")
        return

    # 在查询图片上绘制人脸框（假设只有一个人脸，或取最大）
    try:
        query_faces = app.get(query_img)
        if len(query_faces) > 0:
            largest_face = max(query_faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
            query_img = draw_face_box(query_img, largest_face, label="Query", color=(255,0,0))
    except Exception as e:
        print(f"绘制查询人脸框时出错: {e}")

    # 保存查询图片
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    query_save_path = os.path.join(OUTPUT_DIR, 'query_marked.jpg')
    cv2.imwrite(query_save_path, query_img)
    print(f"查询图片已保存至: {query_save_path}")

    # 对每个匹配结果，从库中读取原图并绘制框
    for rank, (name, sim, bbox) in enumerate(results, 1):
        # 构造库图片的完整路径（假设库图片在 image_folder 下）
        img_path = os.path.join(image_folder, name)
        if not os.path.exists(img_path):
            print(f"库图片不存在: {img_path}")
            continue
        img = cv2.imread(img_path)
        if img is None:
            continue

        # 在图片上绘制人脸框（注意 bbox 是之前提取时保存的，但为了准确可重新检测）
        # 方法1：使用保存的 bbox（如果确信原图未修改）
        cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0,255,0), 2)
        label = f"Match #{rank}: {sim:.3f}"
        cv2.putText(img, label, (bbox[0], bbox[1]-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

        # 保存标记后的图片
        out_path = os.path.join(OUTPUT_DIR, f'match_{rank}_{name}')
        cv2.imwrite(out_path, img)
        print(f"匹配结果 #{rank} 已保存: {out_path}")

    # 可选：生成一张拼接图（查询 + 前三匹配）
    # 这里简单处理，将图片缩放至统一高度然后水平拼接
    # match_imgs = [cv2.imread(os.path.join(OUTPUT_DIR, f'match_{i}_{results[i-1][0]}')) for i in range(1, min(4, len(results)+1))]
    # if match_imgs and query_img is not None:
    #     # 统一高度（例如 400 像素）
    #     target_h = 400
    #     query_resized = cv2.resize(query_img, (int(query_img.shape[1] * target_h / query_img.shape[0]), target_h))
    #     match_resized = [cv2.resize(m, (int(m.shape[1] * target_h / m.shape[0]), target_h)) for m in match_imgs]
    #     combined = np.hstack([query_resized] + match_resized)
    #     cv2.imwrite(os.path.join(OUTPUT_DIR, 'combined_result.jpg'), combined)
    #     print("拼接结果已保存: combined_result.jpg")
# ==================== 使用示例 ====================
if __name__ == '__main__':
    try:
        print("开始执行人脸相似度分析...")
        # 1. 初始化模型
        if not init_model():
            print("模型初始化失败，退出程序")
            exit(1)
        
        # 2. 批量提取特征（假设图片存放在 './photos' 目录）
        image_folder = './photos'           # 请修改为实际路径
        feature_file = './features/photo_features.pkl'
        print(f"图片文件夹: {image_folder}")
        print(f"特征文件: {feature_file}")

        features = get_or_update_features(image_folder, feature_file)
        print(f"成功加载/提取 {len(features)} 个人脸特征")

        # 3. 测试单个用户处理
        print("\n测试单个用户处理...")
        id_card_front = './photos/588391_card_front.jpeg'
        face_photo = './photos/588391_face_photo_list.jpeg'
        
        # 4. 测试人脸检测
        print(f"检测身份证正面人脸: {has_face(id_card_front)}")
        print(f"检测人脸照片人脸: {has_face(face_photo)}")
        
        # 5. 测试身份验证
        is_verified, similarity = verify_identity(id_card_front, face_photo)
        print(f"身份验证结果: {'通过' if is_verified else '失败'} (相似度: {similarity:.4f})")
        
        # 6. 测试黑名单检查
        print("\n测试黑名单检查...")
        blacklist_feature_file = './features/blacklist_features.pkl'
        blacklist_features = get_or_update_features(BLACKLIST_DIR, blacklist_feature_file)
        
        is_blacklist, matched_name, blacklist_similarity = check_blacklist(face_photo, blacklist_features)
        print(f"黑名单检查结果: {'在黑名单中' if is_blacklist else '不在黑名单中'}")
        if is_blacklist:
            print(f"匹配的黑名单: {matched_name} (相似度: {blacklist_similarity:.4f})")
        
        # 7. 测试批量处理
        print("\n测试批量处理...")
        
        # 自动扫描photos文件夹中的所有用户
        base_folder = './photos'
        all_results = auto_scan_and_process_users(base_folder, blacklist_features)
        
        print("\n人脸相似度分析完成！")
    except Exception as e:
        print(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()