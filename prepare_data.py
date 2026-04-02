import os
import shutil
from pathlib import Path

def prepare_same_person_data():
    """
    从all_photo文件夹中提取1000对照片（人脸照片和身份证正面）
    复制到same_person文件夹
    """
    source_dir = './all_photo'
    target_dir = './same_person'
    
    # 创建目标目录
    os.makedirs(target_dir, exist_ok=True)
    
    # 扫描all_photo文件夹，找到身份证正面和人脸照片
    card_front_files = {}
    face_photo_files = {}
    
    print("正在扫描all_photo文件夹...")
    for file_name in os.listdir(source_dir):
        if file_name.endswith('_card_front.jpeg'):
            # 提取用户ID
            user_id = file_name.replace('_card_front.jpeg', '')
            card_front_files[user_id] = file_name
        elif file_name.endswith('_face_photo_list.jpeg'):
            # 提取用户ID
            user_id = file_name.replace('_face_photo_list.jpeg', '')
            face_photo_files[user_id] = file_name
    
    print(f"找到 {len(card_front_files)} 张身份证正面照片")
    print(f"找到 {len(face_photo_files)} 张人脸照片")
    
    # 找到同时有身份证正面和人脸照片的用户
    matched_users = set(card_front_files.keys()) & set(face_photo_files.keys())
    print(f"找到 {len(matched_users)} 个匹配的用户")
    
    if len(matched_users) == 0:
        print("错误：未找到匹配的用户数据")
        print("请确保all_photo文件夹中包含以下格式的文件：")
        print("  - {用户ID}_card_front.jpeg (身份证正面)")
        print("  - {用户ID}_face_photo_list.jpeg (人脸照片)")
        return
    
    # 选择前1000个用户
    selected_users = list(matched_users)[:1000]
    print(f"选择了 {len(selected_users)} 个用户")
    
    # 复制文件
    copied_count = 0
    for user_id in selected_users:
        # 复制身份证正面
        card_front_src = os.path.join(source_dir, card_front_files[user_id])
        card_front_dst = os.path.join(target_dir, f"{user_id}_card_front.jpeg")
        shutil.copy2(card_front_src, card_front_dst)
        
        # 复制人脸照片
        face_photo_src = os.path.join(source_dir, face_photo_files[user_id])
        face_photo_dst = os.path.join(target_dir, f"{user_id}_face_photo_list.jpeg")
        shutil.copy2(face_photo_src, face_photo_dst)
        
        copied_count += 1
        if copied_count % 100 == 0:
            print(f"已复制 {copied_count} 对照片...")
    
    print(f"\n完成！共复制了 {copied_count} 对照片（{copied_count * 2} 张）到 {target_dir} 文件夹")

def prepare_different_person_data():
    """
    从all_photo文件夹中提取2000张人脸照片
    复制到different_person文件夹
    """
    source_dir = './all_photo'
    target_dir = './different_person'
    
    # 创建目标目录
    os.makedirs(target_dir, exist_ok=True)
    
    # 扫描all_photo文件夹，找到人脸照片
    face_photo_files = []
    
    print("正在扫描all_photo文件夹...")
    for file_name in os.listdir(source_dir):
        if file_name.endswith('_face_photo_list.jpeg'):
            face_photo_files.append(file_name)
    
    print(f"找到 {len(face_photo_files)} 张人脸照片")
    
    if len(face_photo_files) == 0:
        print("错误：未找到人脸照片")
        print("请确保all_photo文件夹中包含以下格式的文件：")
        print("  - {用户ID}_face_photo_list.jpeg (人脸照片)")
        return
    
    # 选择前2000张人脸照片
    selected_files = face_photo_files[:2000]
    print(f"选择了 {len(selected_files)} 张人脸照片")
    
    # 复制文件
    copied_count = 0
    for file_name in selected_files:
        # 复制人脸照片
        src_path = os.path.join(source_dir, file_name)
        dst_path = os.path.join(target_dir, file_name)
        shutil.copy2(src_path, dst_path)
        
        copied_count += 1
        if copied_count % 100 == 0:
            print(f"已复制 {copied_count} 张人脸照片...")
    
    print(f"\n完成！共复制了 {copied_count} 张人脸照片到 {target_dir} 文件夹")

if __name__ == '__main__':
    print("=== 数据准备工具 ===")
    print("1. 准备同一人照片数据（same_person）")
    print("2. 准备不同人照片数据（different_person）")
    print("3. 同时准备两种数据")
    
    choice = input("请选择操作（1/2/3）: ").strip()
    
    if choice == '1':
        prepare_same_person_data()
    elif choice == '2':
        prepare_different_person_data()
    elif choice == '3':
        prepare_same_person_data()
        print()
        prepare_different_person_data()
    else:
        print("无效的选择，退出程序")
