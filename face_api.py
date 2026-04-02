import os
import pickle
import numpy as np
import cv2
import json
from insightface.app import FaceAnalysis
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import sys

# ==================== 配置部分 ====================
MODEL_NAME = 'buffalo_l'
DEVICE_ID = -1
DET_THRESH = 0.5
INPUT_SIZE = (640, 640)
FEATURE_DIR = './features'
OUTPUT_DIR = './output'
BLACKLIST_DIR = './blacklist'

# 相似度阈值设置
ID_CARD_FACE_THRESHOLD = 0.60
BLACKLIST_THRESHOLD = 0.65

# 全局变量
app = None

# 初始化模型
def init_model():
    global app
    try:
        app = FaceAnalysis(name=MODEL_NAME, root='~/.insightface')
        app.prepare(ctx_id=DEVICE_ID, det_thresh=DET_THRESH, det_size=INPUT_SIZE)
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

def has_face(image_path):
    emb, bbox = extract_face_features(image_path)
    return emb is not None

def verify_identity(id_card_image_path, face_image_path, threshold=ID_CARD_FACE_THRESHOLD):
    id_card_emb, id_card_bbox = extract_face_features(id_card_image_path)
    if id_card_emb is None:
        return False, 0.0, "身份证正面未检测到人脸"
    
    face_emb, face_bbox = extract_face_features(face_image_path)
    if face_emb is None:
        return False, 0.0, "人脸照片未检测到人脸"
    
    similarity = np.dot(id_card_emb, face_emb)
    is_same_person = similarity >= threshold
    return is_same_person, float(similarity), "验证成功"

def check_blacklist(face_image_path, blacklist_features, threshold=BLACKLIST_THRESHOLD):
    face_emb, face_bbox = extract_face_features(face_image_path)
    if face_emb is None:
        return False, "", 0.0, "待检测照片未检测到人脸"
    
    max_similarity = 0.0
    matched_name = ""
    
    for name, (emb, bbox) in blacklist_features.items():
        similarity = np.dot(face_emb, emb)
        if similarity > max_similarity:
            max_similarity = similarity
            matched_name = name
    
    is_in_blacklist = max_similarity >= threshold
    return is_in_blacklist, matched_name, float(max_similarity), "检查成功"

def load_features(feature_path):
    try:
        with open(feature_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"加载特征文件失败: {e}")
        return {}

def batch_extract(image_folder, save_path=None):
    """
    批量提取文件夹下所有图片的人脸特征
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_paths = [p for p in Path(image_folder).iterdir() if p.suffix.lower() in image_extensions]

    features_dict = {}
    for img_path in image_paths:
        emb, bbox = extract_face_features(str(img_path))
        if emb is not None:
            features_dict[img_path.name] = (emb, bbox)

    print(f"总共处理 {len(image_paths)} 张图片，成功提取 {len(features_dict)} 张人脸。")

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump(features_dict, f)
        print(f"特征已保存至: {save_path}")

    return features_dict

def get_or_update_features(image_dir, feature_file, force_update=False):
    """
    获取或更新特征文件，自动检测目录变化
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

def process_request(request_data):
    """
    处理API请求
    参数:
        request_data: dict，包含订单号、功能参数和图片路径
    返回: dict，包含处理结果
    """
    result = {
        'order_id': request_data.get('order_id', ''),
        'success': True,
        'message': '处理成功',
        'data': {}
    }
    
    try:
        # 初始化模型
        if not init_model():
            result['success'] = False
            result['message'] = '模型初始化失败'
            return result
        
        # 获取功能参数
        check_face = request_data.get('check_face', False)
        verify_identity_flag = request_data.get('verify_identity', False)
        check_blacklist_flag = request_data.get('check_blacklist', False)
        
        # 获取图片路径
        id_card_front = request_data.get('id_card_front', '')
        face_photo = request_data.get('face_photo', '')
        
        # 1. 人脸检测
        if check_face:
            id_card_has_face = has_face(id_card_front) if id_card_front else None
            face_photo_has_face = has_face(face_photo) if face_photo else None
            
            result['data']['face_detection'] = {
                'id_card_face_detected': id_card_has_face if id_card_has_face is not None else False,
                'face_photo_detected': face_photo_has_face if face_photo_has_face is not None else False
            }
        
        # 2. 身份验证
        if verify_identity_flag and id_card_front and face_photo:
            is_verified, similarity, message = verify_identity(id_card_front, face_photo)
            result['data']['identity_verification'] = {
                'verified': is_verified,
                'similarity': similarity,
                'message': message
            }
        
        # 3. 黑名单检查
        if check_blacklist_flag and face_photo:
            blacklist_feature_file = os.path.join(FEATURE_DIR, 'blacklist_features.pkl')
            blacklist_features = get_or_update_features(BLACKLIST_DIR, blacklist_feature_file)
            
            if not blacklist_features:
                result['data']['blacklist_check'] = {
                    'in_blacklist': False,
                    'matched_name': '',
                    'similarity': 0.0,
                    'message': '黑名单特征未加载'
                }
            else:
                is_blacklist, matched_name, similarity, message = check_blacklist(face_photo, blacklist_features)
                result['data']['blacklist_check'] = {
                    'in_blacklist': is_blacklist,
                    'matched_name': matched_name,
                    'similarity': similarity,
                    'message': message
                }
        
        # 如果没有执行任何功能
        if not any([check_face, verify_identity_flag, check_blacklist_flag]):
            result['success'] = False
            result['message'] = '未指定任何功能参数'
        
    except Exception as e:
        result['success'] = False
        result['message'] = f'处理出错: {str(e)}'
        import traceback
        traceback.print_exc()
    
    return result

def main():
    """
    主函数：从标准输入读取JSON请求并返回JSON响应
    """
    try:
        # 从标准输入读取JSON数据
        input_data = sys.stdin.read()
        request_data = json.loads(input_data)
        
        # 处理请求
        result = process_request(request_data)
        
        # 输出JSON结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except json.JSONDecodeError as e:
        error_result = {
            'success': False,
            'message': f'JSON解析错误: {str(e)}',
            'data': {}
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
    except Exception as e:
        error_result = {
            'success': False,
            'message': f'系统错误: {str(e)}',
            'data': {}
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
