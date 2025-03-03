import json
import copy
import os
import sys
import logging
import importlib.util
from typing import Dict, List, Any, Tuple, Optional, Union, Set

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("workflow_converter")

def load_comfy_nodes() -> Dict:
    """
    ComfyUI의 노드 정의를 동적으로 로드합니다.
    
    Returns:
        Dict: 노드 유형 -> 노드 클래스 매핑
    """
    try:
        # ComfyUI 경로 설정
        comfy_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if comfy_path not in sys.path:
            sys.path.append(comfy_path)
        
        # 노드 모듈 가져오기
        try:
            from comfy.nodes import NODE_CLASS_MAPPINGS
            logger.info(f"ComfyUI 노드 정의 로드 성공: {len(NODE_CLASS_MAPPINGS)} 노드 발견")
            return NODE_CLASS_MAPPINGS
        except ImportError:
            logger.warning("comfy.nodes 모듈을 가져올 수 없습니다.")
    except Exception as e:
        logger.warning(f"ComfyUI 노드 정의 로드 실패: {str(e)}")
    
    logger.warning("노드 정의 없이 변환을 진행합니다.")
    return {}

def get_default_node_mappings() -> Dict:
    """
    기본 노드 매핑 정보를 반환합니다.
    동적 로딩 실패 시 사용됩니다.
    
    Returns:
        Dict: 기본 노드 매핑 정보
    """
    default_mappings = {}
    
    # 일반적인 노드 클래스의 가상 스키마 정보 생성
    # 여기서는 스키마 대신 기본 입력값 매핑만 정의
    class DefaultNodeClass:
        def __init__(self, required_inputs=None):
            self.required_inputs = required_inputs or []
        
        def INPUT_TYPES(self):
            return {
                "required": {input_name: None for input_name in self.required_inputs}
            }
    
    # 자주 사용되는 노드 타입에 대한 필수 입력값 정의
    required_inputs = {
        "CheckpointLoaderSimple": ["ckpt_name"],
        "CLIPTextEncode": ["text"],
        "EmptyLatentImage": ["width", "height", "batch_size"],
        "KSampler": ["seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"],
        "SaveImage": ["filename_prefix"],
        "VAEDecode": [],
        "VAEEncode": []
    }
    
    # 가상 노드 클래스 생성
    for node_type, inputs in required_inputs.items():
        default_mappings[node_type] = DefaultNodeClass(inputs)
    
    return default_mappings

def extract_node_schema(node_class: Any) -> Dict:
    """
    노드 클래스에서 스키마 정보를 추출합니다.
    
    Args:
        node_class: 노드 클래스
        
    Returns:
        Dict: 노드 스키마 정보
    """
    schema = {
        "inputs": {},
        "outputs": {},
        "widgets": [],
        "required_inputs": []  # 필수 입력값 목록 추가
    }
    
    try:
        # 입력 정보 추출
        if hasattr(node_class, "INPUT_TYPES"):
            input_types = node_class.INPUT_TYPES()
            if "required" in input_types:
                for name, input_info in input_types["required"].items():
                    schema["inputs"][name] = input_info
                    schema["required_inputs"].append(name)  # 필수 입력값으로 추가
            if "optional" in input_types:
                for name, input_info in input_types["optional"].items():
                    schema["inputs"][name] = input_info
        
        # 위젯 정보 추출
        if hasattr(node_class, "WIDGETS"):
            schema["widgets"] = node_class.WIDGETS
        
        # 출력 정보 추출
        if hasattr(node_class, "RETURN_TYPES"):
            return_types = node_class.RETURN_TYPES
            return_names = getattr(node_class, "RETURN_NAMES", [None] * len(return_types))
            for i, (type_info, name) in enumerate(zip(return_types, return_names)):
                output_name = name if name else f"output_{i}"
                schema["outputs"][output_name] = type_info
    except Exception as e:
        logger.warning(f"노드 스키마 추출 중 오류: {str(e)}")
    
    return schema

def find_widget_input_names(node: Dict) -> List[str]:
    """
    노드에서 위젯 입력 이름을 찾습니다.
    
    Args:
        node: 노드 정보
        
    Returns:
        List[str]: 위젯 입력 이름 목록
    """
    widget_names = []
    
    # widgets 속성이 있는 경우 사용
    if "widgets" in node:
        for widget in node["widgets"]:
            if "name" in widget:
                widget_names.append(widget["name"])
    
    # widgets_values가 있지만 widgets가 없는 경우, 기본 이름 생성
    elif "widgets_values" in node and len(node["widgets_values"]) > 0:
        widget_count = len(node["widgets_values"])
        # 기본 이름 생성 (param_0, param_1, ...)
        widget_names = [f"param_{i}" for i in range(widget_count)]
    
    return widget_names

def map_widgets_to_inputs(node: Dict, node_schemas: Dict) -> Dict:
    """
    노드의 위젯 값을 입력 파라미터로 매핑합니다.
    
    Args:
        node: 노드 정보
        node_schemas: 노드 스키마 정보
        
    Returns:
        Dict: 입력 이름 -> 값 매핑
    """
    if "widgets_values" not in node:
        return {}
    
    widgets_values = node.get("widgets_values", [])
    node_type = node.get("type")
    inputs = {}
    
    # 위젯 입력 이름 찾기 시도
    widget_input_names = find_widget_input_names(node)
    
    # 위젯 값을 해당 입력 이름과 매핑
    for i, value in enumerate(widgets_values):
        # 입력 이름이 있으면 해당 이름 사용
        if i < len(widget_input_names):
            input_name = widget_input_names[i]
            inputs[input_name] = value
        # 입력 이름이 없으면 인덱스 기반 이름 사용
        else:
            input_name = f"param_{i}"
            inputs[input_name] = value
    
    return inputs

def get_node_title(node: Dict) -> str:
    """
    노드 제목을 가져옵니다.
    
    Args:
        node: 노드 정보
        
    Returns:
        str: 노드 제목
    """
    if "title" in node and node["title"]:
        return node["title"]
    return node.get("type", "Unknown Node")

def build_link_map(workflow: Dict) -> Dict:
    """
    워크플로우의 링크 정보를 매핑합니다.
    링크 ID를 키로 하고 [소스 노드 ID, 소스 출력 인덱스, 대상 노드 ID, 대상 입력 인덱스] 배열을 값으로 합니다.
    
    Args:
        workflow: 워크플로우 데이터
        
    Returns:
        Dict: 링크 ID -> [소스 노드 ID, 소스 출력 인덱스, 대상 노드 ID, 대상 입력 인덱스] 매핑
    """
    link_map = {}
    
    for link in workflow.get("links", []):
        link_id = link[0]
        src_node_id = link[1]
        src_output_idx = link[2]
        dst_node_id = link[3]
        dst_input_idx = link[4]
        
        link_map[link_id] = [src_node_id, src_output_idx, dst_node_id, dst_input_idx]
    
    return link_map

def build_input_name_map(workflow: Dict) -> Dict:
    """
    노드 입력 인덱스를 입력 이름으로 매핑합니다.
    (노드 ID, 입력 인덱스) 튜플을 키로 하고 입력 이름을 값으로 합니다.
    
    Args:
        workflow: 워크플로우 데이터
        
    Returns:
        Dict: (노드 ID, 입력 인덱스) -> 입력 이름 매핑
    """
    input_name_map = {}
    
    for node in workflow.get("nodes", []):
        node_id = node["id"]
        
        for i, inp in enumerate(node.get("inputs", [])):
            input_name = inp.get("name")
            if input_name:
                input_name_map[(node_id, i)] = input_name
    
    return input_name_map

def analyze_workflow_node_types(workflow: Dict) -> Dict:
    """
    워크플로우에서 노드 타입별 위젯 입력 매핑을 분석합니다.
    노드 구조와 연결 패턴을 분석하여 위젯 값의 의미를 유추합니다.
    
    Args:
        workflow: 워크플로우 정보
        
    Returns:
        Dict: 노드 타입 -> 위젯 입력 이름 목록 매핑
    """
    # 노드 타입별 위젯 매핑 정보
    node_type_widget_inputs = {}
    
    # 워크플로우 분석을 통한 패턴 인식
    link_map = build_link_map(workflow)
    input_name_map = build_input_name_map(workflow)
    
    # 각 노드 타입별 분석
    for node in workflow.get("nodes", []):
        node_type = node.get("type")
        widget_values = node.get("widgets_values", [])
        
        # 이미 해당 노드 타입이 분석되었으면 스킵
        if node_type in node_type_widget_inputs:
            continue
        
        # 위젯 값이 없으면 분석 불가
        if not widget_values:
            continue
        
        # 위젯 입력 이름 찾기
        widget_input_names = find_widget_input_names(node)
        
        # API 문서나 워크플로우에서 발견된 패턴 기반 입력 이름 추정
        if node_type == "CheckpointLoaderSimple":
            # 모델 로더는 일반적으로 첫번째 위젯이 체크포인트 이름
            node_type_widget_inputs[node_type] = ["ckpt_name"]
        
        elif node_type == "CLIPTextEncode":
            # CLIP 텍스트 인코더는 일반적으로 텍스트 입력
            node_type_widget_inputs[node_type] = ["text"]
        
        elif node_type == "EmptyLatentImage":
            # 비어있는 이미지는 일반적으로 width, height, batch_size 순서
            if len(widget_values) >= 3:
                node_type_widget_inputs[node_type] = ["width", "height", "batch_size"]
        
        elif node_type == "KSampler":
            # KSampler는 일반적인 입력 순서 분석
            if len(widget_values) >= 7:
                node_type_widget_inputs[node_type] = [
                    "seed", "control_after_generate", "steps", "cfg", 
                    "sampler_name", "scheduler", "denoise"
                ]
        
        elif node_type == "SaveImage":
            # 이미지 저장은 일반적으로 파일 이름 접두사
            node_type_widget_inputs[node_type] = ["filename_prefix"]
        
        else:
            # 기타 노드는 위젯 입력 이름 유추
            if widget_input_names:
                # 위젯 입력 이름 있으면 사용
                node_type_widget_inputs[node_type] = widget_input_names
            elif widget_values:
                # 일반적인 파라미터 이름 생성
                node_type_widget_inputs[node_type] = [f"param_{i}" for i in range(len(widget_values))]
    
    # 위젯 매핑 결과 로깅
    for node_type, mapping in node_type_widget_inputs.items():
        logger.debug(f"노드 타입 '{node_type}' 위젯 매핑: {mapping}")
    
    return node_type_widget_inputs

def convert_workflow_to_api(workflow: Dict, use_dynamic_loading: bool = True) -> Dict:
    """
    일반 ComfyUI 워크플로우 JSON을 API 워크플로우 JSON으로 변환합니다.
    
    Args:
        workflow: 일반 ComfyUI 워크플로우 JSON
        use_dynamic_loading: ComfyUI 노드 정의를 동적으로 로드할지 여부
        
    Returns:
        Dict: API 워크플로우 JSON
    """
    # 결과 API 워크플로우 초기화
    api_workflow = {}
    
    # ComfyUI 노드 정의 로드 (선택적)
    node_schemas = {}
    if use_dynamic_loading:
        node_classes = load_comfy_nodes()
        for node_type, node_class in node_classes.items():
            node_schemas[node_type] = extract_node_schema(node_class)
    
    # 링크 매핑 생성
    link_map = build_link_map(workflow)
    
    # 노드별 입력 이름 매핑 (노드ID, 링크ID) -> 입력이름
    input_name_map = build_input_name_map(workflow)
    
    # 워크플로우 분석을 통한 노드 타입별 위젯 입력 매핑 추출
    node_type_widget_inputs = analyze_workflow_node_types(workflow)
    
    # 노드 처리
    for node in workflow.get("nodes", []):
        node_id = node["id"]
        node_type = node["type"]
        
        # 노드 타이틀 결정
        node_title = get_node_title(node)
        
        # API 노드 생성
        api_node = {
            "inputs": {},
            "class_type": node_type,
            "_meta": {
                "title": node_title
            }
        }
        
        # 위젯 값 처리 - 워크플로우 분석 결과 활용
        if node_type in node_type_widget_inputs and "widgets_values" in node:
            widget_inputs = {}
            widgets_values = node.get("widgets_values", [])
            
            # 학습된 위젯-입력 매핑 사용
            param_names = node_type_widget_inputs[node_type]
            for i, value in enumerate(widgets_values):
                if i < len(param_names):
                    widget_inputs[param_names[i]] = value
            
            api_node["inputs"].update(widget_inputs)
        else:
            # 위젯 값을 직접 매핑 시도
            widget_inputs = map_widgets_to_inputs(node, node_schemas)
            api_node["inputs"].update(widget_inputs)
        
        # 입력 연결 처리
        for inp in node.get("inputs", []):
            input_name = inp.get("name")
            link_id = inp.get("link")
            
            if link_id is not None and link_id in link_map:
                src_node_id, src_output_idx = link_map[link_id][0:2]
                api_node["inputs"][input_name] = [str(src_node_id), src_output_idx]
        
        # API 워크플로우에 노드 추가
        api_workflow[str(node_id)] = api_node
    
    # 변환된 워크플로우 검증 및 로깅
    for node_id, api_node in api_workflow.items():
        node_type = api_node.get("class_type")
        logger.debug(f"변환된 노드 {node_id} ({node_type}): 입력 = {api_node.get('inputs', {})}")
    
    return api_workflow

def convert_api_to_workflow(api_workflow):
    """
    API 워크플로우 JSON을 일반 ComfyUI 워크플로우 JSON으로 변환합니다.
    
    Args:
        api_workflow (dict): API 워크플로우 JSON
        
    Returns:
        dict: 일반 ComfyUI 워크플로우 JSON
    """
    # 이 함수는 향후 구현 예정
    pass

def load_and_convert_workflow(workflow_path, use_dynamic_loading=True):
    """
    파일에서 워크플로우를 로드하고 API 형식으로 변환합니다.
    
    Args:
        workflow_path (str): 워크플로우 JSON 파일 경로
        use_dynamic_loading (bool): ComfyUI 노드 정의를 동적으로 로드할지 여부
        
    Returns:
        dict: 변환된 API 워크플로우
    """
    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    return convert_workflow_to_api(workflow, use_dynamic_loading)

def save_api_workflow(api_workflow, output_path):
    """
    변환된 API 워크플로우를 파일로 저장합니다.
    
    Args:
        api_workflow (dict): 변환된 API 워크플로우
        output_path (str): 저장할 파일 경로
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(api_workflow, f, indent=2, ensure_ascii=False)

def validate_workflow(api_workflow: Dict) -> List[str]:
    """
    API 워크플로우가 유효한지 검사합니다.
    모든 노드에 필수 입력이 있는지 확인합니다.
    
    Args:
        api_workflow: API 형식의 워크플로우
        
    Returns:
        List[str]: 누락된 필수 입력 목록 (비어있으면 모든 것이 유효함)
    """
    missing_inputs = []
    
    # 필수 입력이 잘 알려진 노드 타입
    known_required_inputs = {
        "CheckpointLoaderSimple": ["ckpt_name"],
        "CLIPTextEncode": ["text", "clip"],
        "EmptyLatentImage": ["width", "height", "batch_size"],
        "KSampler": ["seed", "steps", "cfg", "sampler_name", "scheduler", "latent_image", "model", "positive", "negative"],
        "VAEDecode": ["samples", "vae"],
        "VAEEncode": ["pixels", "vae"],
        "SaveImage": ["filename_prefix", "images"]
    }
    
    for node_id, node in api_workflow.items():
        node_type = node.get("class_type")
        node_inputs = node.get("inputs", {})
        
        # 이 노드 타입에 대한 필수 입력 확인
        if node_type in known_required_inputs:
            required_inputs = known_required_inputs[node_type]
            
            for req_input in required_inputs:
                if req_input not in node_inputs:
                    missing_inputs.append(f"노드 {node_id} ({node_type}): '{req_input}' 입력 누락")
    
    return missing_inputs

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ComfyUI 워크플로우 변환기")
    parser.add_argument("input_path", help="변환할 ComfyUI 워크플로우 JSON 파일 경로")
    parser.add_argument("-o", "--output", help="변환된 API 워크플로우 저장 경로")
    parser.add_argument("--no-dynamic", action="store_true", help="ComfyUI 노드 정의 동적 로딩 비활성화")
    args = parser.parse_args()
    
    output_path = args.output if args.output else args.input_path + ".api.json"
    
    try:
        api_workflow = load_and_convert_workflow(args.input_path, not args.no_dynamic)
        save_api_workflow(api_workflow, output_path)
        logger.info(f"변환 완료: {output_path}")
    except Exception as e:
        logger.error(f"변환 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 