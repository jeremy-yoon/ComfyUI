import os
import folder_paths

print("[startup.py] 시작: 필요한 폴더 경로 등록")

model_path = folder_paths.models_dir

# 폴더 경로 등록 함수
def add_folder_path_and_extensions(folder_name, full_folder_paths, extensions):
    # 각 폴더 경로에 대해 반복
    for full_folder_path in full_folder_paths:
        # 폴더가 없는 경우 생성
        if not os.path.exists(full_folder_path):
            print(f"[startup.py] 폴더 생성: {full_folder_path}")
            os.makedirs(full_folder_path, exist_ok=True)
        
        # 모델 폴더 경로 추가
        folder_paths.add_model_folder_path(folder_name, full_folder_path)

    # 폴더 이름이 이미 등록되어 있으면 확장자 업데이트
    if folder_name in folder_paths.folder_names_and_paths:
        # 현재 경로와 확장자 가져오기
        current_paths, current_extensions = folder_paths.folder_names_and_paths[folder_name]
        # 확장자 세트 업데이트
        updated_extensions = current_extensions | extensions
        # 업데이트된 튜플을 사전에 다시 할당
        folder_paths.folder_names_and_paths[folder_name] = (current_paths, updated_extensions)
    else:
        # 폴더 이름이 없으면 추가
        folder_paths.folder_names_and_paths[folder_name] = (full_folder_paths, extensions)

# 필요한 폴더 등록
folders_to_register = [
    ("sams", [os.path.join(model_path, "sams")], folder_paths.supported_pt_extensions),
    ("onnx", [os.path.join(model_path, "onnx")], {'.onnx'}),
    ("ultralytics_bbox", [os.path.join(model_path, "ultralytics", "bbox")], folder_paths.supported_pt_extensions),
    ("ultralytics_segm", [os.path.join(model_path, "ultralytics", "segm")], folder_paths.supported_pt_extensions),
    ("ultralytics", [os.path.join(model_path, "ultralytics")], folder_paths.supported_pt_extensions)
]

for folder_name, paths, extensions in folders_to_register:
    add_folder_path_and_extensions(folder_name, paths, extensions)
    print(f"[startup.py] 등록 완료: {folder_name}")

print("[startup.py] 완료: 모든 폴더 경로 등록됨") 