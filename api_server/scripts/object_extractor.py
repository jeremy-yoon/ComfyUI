import cv2
import numpy as np
def mask_to_binary(mask_path, image_shape):
    """
    마스크 이미지를 불러와서 처리할 영역을 이진화된 마스크로 변환하는 함수.
    :param mask_path: 마스크 이미지 경로 (PNG, 알파 채널 포함)
    :param image_shape: 원본 이미지 크기 (h, w)
    :return: 0 또는 1로 구성된 마스크 (1: 처리할 영역, 0: 유지할 영역)
    """
    # 마스크 이미지 로드
    mask = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
    # 크기 체크 (자동 리사이징)
    if mask.shape[:2] != image_shape[:2]:
        mask = cv2.resize(mask, (image_shape[1], image_shape[0]), interpolation=cv2.INTER_NEAREST)
    # 알파 채널이 있는 경우, 투명한 부분(0)을 유사 픽셀 제거 영역으로 설정
    if mask.shape[2] == 4:
        alpha_channel = mask[:, :, 3]  # 알파 채널 추출
        binary_mask = (alpha_channel == 0).astype(np.uint8)  # 투명한 부분을 1로 변환 (처리 영역)
    else:
        raise ValueError("마스크 이미지에는 반드시 알파 채널이 포함되어 있어야 합니다!")
    return binary_mask
def remove_background_grabcut(image_path, removal_strength=50):
    """
    배경 제거 강도를 하나의 수치로 조절할 수 있는 함수.
    메인 배경색을 찾아서 그와 연결된 유사한 색상 영역을 제거합니다.
    removal_strength가 높을수록 더 넓은 색상 범위를 배경으로 처리합니다.
    :param image_path: 이미지 경로
    :param removal_strength: 배경 제거 강도 (0~100, 높을수록 더 넓은 색상 범위를 배경으로 처리)
    :return: 배경이 제거된 이미지 (RGBA 형태)
    """
    # 강도 값을 0~100 범위로 제한
    removal_strength = max(0, min(100, removal_strength))
    # 이미지 로드
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    # RGBA가 아닐 경우 변환
    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    # 이미지 전처리
    h, w = img.shape[:2]
    # HSV 색공간으로 변환
    hsv = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2HSV)
    # 가장자리 픽셀에서 메인 배경색 찾기
    edge_pixels = np.concatenate([
        hsv[0, :],      # 위쪽 가장자리
        hsv[-1, :],     # 아래쪽 가장자리
        hsv[:, 0],      # 왼쪽 가장자리
        hsv[:, -1]      # 오른쪽 가장자리
    ])
    # 메인 배경색 계산 (가장자리 픽셀들의 중앙값)
    main_bg_color = np.median(edge_pixels, axis=0)
    # 색상 차이 허용 범위 계산 (removal_strength에 따라 조정)
    h_tolerance = int(5 + (removal_strength * 0.3))  # 색상 허용 범위
    s_tolerance = int(10 + (removal_strength * 0.5))  # 채도 허용 범위
    v_tolerance = int(15 + (removal_strength * 0.7))  # 명도 허용 범위
    # 메인 배경색과의 차이 계산
    h_diff = np.minimum(np.abs(hsv[:,:,0] - main_bg_color[0]),
                       180 - np.abs(hsv[:,:,0] - main_bg_color[0]))  # 색상은 원형이므로 특별 처리
    s_diff = np.abs(hsv[:,:,1] - main_bg_color[1])
    v_diff = np.abs(hsv[:,:,2] - main_bg_color[2])
    # 배경 후보 영역 식별
    bg_candidate = (h_diff <= h_tolerance) & \
                  (s_diff <= s_tolerance) & \
                  (v_diff <= v_tolerance)
    # 외곽에서 연결된 배경 영역 찾기
    bg_mask = np.zeros((h+2, w+2), np.uint8)
    flood_mask = np.zeros((h+2, w+2), np.uint8)
    # 가장자리에서 시작하여 연결된 배경 찾기
    for x in range(0, w, 2):  # 간격을 2로 줄여 더 많은 시작점 사용
        if bg_candidate[0, x]:  # 위쪽
            cv2.floodFill(bg_candidate.astype(np.uint8), flood_mask, (x, 0), 1)
        if bg_candidate[h-1, x]:  # 아래쪽
            cv2.floodFill(bg_candidate.astype(np.uint8), flood_mask, (x, h-1), 1)
    for y in range(0, h, 2):  # 간격을 2로 줄여 더 많은 시작점 사용
        if bg_candidate[y, 0]:  # 왼쪽
            cv2.floodFill(bg_candidate.astype(np.uint8), flood_mask, (0, y), 1)
        if bg_candidate[y, w-1]:  # 오른쪽
            cv2.floodFill(bg_candidate.astype(np.uint8), flood_mask, (w-1, y), 1)
    # 초기 마스크 생성
    mask = np.zeros((h, w), np.uint8) + cv2.GC_PR_FGD
    # 배경으로 판단된 영역을 GrabCut 마스크에 반영
    mask[bg_candidate] = cv2.GC_PR_BGD  # 배경 후보
    mask[flood_mask[1:-1,1:-1] > 0] = cv2.GC_BGD  # 확실한 배경
    # grabCut 모델 초기화
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    # grabCut 적용 (반복 횟수도 강도에 따라 조정)
    iterations = int(3 + (removal_strength * 0.1))
    cv2.grabCut(img[:, :, :3], mask, None, bgd_model, fgd_model, iterations, cv2.GC_INIT_WITH_MASK)
    # 배경 픽셀을 0으로 설정
    mask_output = np.where((mask == cv2.GC_BGD) | (mask == cv2.GC_PR_BGD), 0, 1).astype(np.uint8)
    # 후처리: 작은 홀 제거
    kernel = np.ones((3, 3), np.uint8)
    mask_output = cv2.morphologyEx(mask_output, cv2.MORPH_CLOSE, kernel)
    # 알파 채널 적용
    img[:, :, 3] = img[:, :, 3] * mask_output
    return img
def calculate_pixel_similarity(hsv1, hsv2, weights):
    """
    두 HSV 픽셀 간의 유사도를 계산하는 함수.
    다양한 특성에 대한 가중치를 적용할 수 있습니다.
    :param hsv1: 첫 번째 HSV 이미지
    :param hsv2: 두 번째 HSV 이미지
    :param weights: 각 특성별 가중치 딕셔너리
    :return: 전체 차이값
    """
    h1, s1, v1 = hsv1[:, :, 0], hsv1[:, :, 1], hsv1[:, :, 2]
    h2, s2, v2 = hsv2[:, :, 0], hsv2[:, :, 1], hsv2[:, :, 2]
    # 1. 기본 HSV 차이
    h_diff = np.minimum(np.abs(h1 - h2), 180 - np.abs(h1 - h2))
    s_diff = np.abs(s1 - s2)
    v_diff = np.abs(v1 - v2)
    # 2. 채도에 따른 색상 가중치 조정 (채도가 높을수록 색상이 더 중요)
    avg_saturation = (s1 + s2) / 2
    h_importance = weights['h_base'] + (weights['h_sat_bonus'] * (avg_saturation / 255))
    # 3. 채도 차이의 비선형 처리
    s_diff_weighted = s_diff * (1 + weights['s_nonlinear'] * (s_diff / 255))
    # 4. 명도 차이의 비선형 처리
    v_diff_weighted = v_diff * (1 + weights['v_nonlinear'] * (v_diff / 255))
    # 5. 채도가 매우 낮은 경우 (무채색) 처리
    is_grayscale = (s1 < weights['gray_threshold']) & (s2 < weights['gray_threshold'])
    h_diff = np.where(is_grayscale, 0, h_diff)  # 무채색인 경우 색상 차이 무시
    # 6. 전체 차이 계산
    total_diff = (h_diff * h_importance +
                 s_diff_weighted * weights['s_base'] +
                 v_diff_weighted * weights['v_base'])
    return total_diff
def remove_similar_pixels_with_mask(target_image_path, comparison_image_path, mask_image_path, output_path, similarity_threshold=30, removal_strength=10):
    """
    1. 배경을 먼저 제거하고
    2. 마스크 이미지에서 지정한 투명한 영역에서만 유사한 픽셀을 찾아 투명하게 변경하는 함수.
    HSV 색공간에서 다양한 특성을 고려하여 유사도를 계산합니다.
    :param target_image_path: 처리할 대상 이미지 경로
    :param comparison_image_path: 비교할 이미지 경로
    :param mask_image_path: 처리할 영역을 정의한 마스크 이미지 경로
    :param output_path: 결과 저장 경로
    :param similarity_threshold: 픽셀 비교 허용 오차 (값이 클수록 더 유사한 픽셀을 투명하게 함)
    :param removal_strength: 배경 제거 강도 (0~100, 높을수록 더 넓은 색상 범위를 배경으로 처리)
    """
    # 배경 제거 후 이미지 로드
    img1 = remove_background_grabcut(target_image_path, removal_strength)
    img2 = remove_background_grabcut(comparison_image_path, removal_strength)
    # 크기 체크
    if img1.shape != img2.shape:
        raise ValueError("두 이미지의 크기가 같아야 합니다.")
    # 마스크 이미지 로드
    mask = mask_to_binary(mask_image_path, img1.shape)
    # HSV 색공간으로 변환
    hsv1 = cv2.cvtColor(img1[:, :, :3], cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2[:, :, :3], cv2.COLOR_BGR2HSV)
    # 유사도 계산을 위한 가중치 설정
    weights = {
        'h_base': -0.6,          # 기본 색상 가중치
        'h_sat_bonus': 0.0,     # 채도에 따른 색상 가중치 보너스
        's_base': 1.4,          # 기본 채도 가중치
        's_nonlinear': -1.0,     # 채도 차이의 비선형 가중치
        'v_base': 1.2,          # 기본 명도 가중치
        'v_nonlinear': -1.0,     # 명도 차이의 비선형 가중치
        'gray_threshold': 80,    # 무채색 판단 임계값
    }
    # 픽셀 유사도 계산
    total_diff = calculate_pixel_similarity(hsv1, hsv2, weights)
    # 알파 채널이 0인 픽셀은 제외
    valid_pixels = (img1[:, :, 3] > 0) & (img2[:, :, 3] > 0)
    # 가중치 합계 계산 (임계값 조정용)
    total_weights = weights['h_base'] + weights['s_base'] + weights['v_base']
    # 유사한 픽셀 마스크 생성
    adjusted_threshold = similarity_threshold * total_weights / 3
    pixel_mask = (total_diff <= adjusted_threshold) & (mask == 1) & valid_pixels
    # 연결된 영역만 처리하기 위한 후처리
    kernel = np.ones((3, 3), np.uint8)
    pixel_mask = cv2.morphologyEx(pixel_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    pixel_mask = cv2.morphologyEx(pixel_mask, cv2.MORPH_OPEN, kernel)
    # 겹치는 부분을 투명하게 변경
    img1[pixel_mask > 0] = [0, 0, 0, 0]
    # 결과 저장
    cv2.imwrite(output_path, img1)
    print(f"완료! 결과가 {output_path} 에 저장되었습니다.")



