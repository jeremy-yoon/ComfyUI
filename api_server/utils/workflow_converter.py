import json
import copy
import os
import sys
import logging
import importlib.util
from typing import Dict, List, Any, Tuple, Optional, Union

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
        from comfy.nodes import NODE_CLASS_MAPPINGS
        logger.info(f"ComfyUI 노드 정의 로드 성공: {len(NODE_CLASS_MAPPINGS)} 노드 발견")
        return NODE_CLASS_MAPPINGS
    except Exception as e:
        logger.warning(f"ComfyUI 노드 정의 로드 실패: {str(e)}")
        logger.warning("노드 정의 없이 변환을 진행합니다.")
        return {}

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
    # 위젯이 연결된 입력 찾기
    widget_input_names = []
    
    # 위젯 정보가 있는 경우
    for inp in node.get("inputs", []):
        if inp.get("widget") is not None:
            widget_input_names.append(inp.get("name"))
    
    return widget_input_names

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
    
    # 1. 노드 내에서 위젯에 연결된 입력 이름 찾기
    widget_input_names = find_widget_input_names(node)
    
    # 2. 노드 스키마에서 입력 이름 찾기
    schema_input_names = []
    required_inputs = []
    if node_type in node_schemas:
        schema_input_names = list(node_schemas[node_type]["inputs"].keys())
        required_inputs = node_schemas[node_type].get("required_inputs", [])
    
    # 3. 입력 이름 결정 및 매핑
    for i, value in enumerate(widgets_values):
        # 위젯 입력 이름이 있는 경우 먼저 사용
        if i < len(widget_input_names):
            input_name = widget_input_names[i]
        # 스키마 입력 이름이 있는 경우 다음으로 사용
        elif i < len(schema_input_names):
            input_name = schema_input_names[i]
        # 아무 정보도 없는 경우 일반적인 이름 생성
        else:
            input_name = f"param_{i}"
            
        # 입력 값 할당
        if input_name:
            inputs[input_name] = value
    
    # 4. 일반적인 노드 타입 처리 - 하드코딩 대신 동적 처리
    # ComfyUI 노드 타입에 따른 일반적인 규칙 적용
    
    # 가장 일반적인 노드 타입에 대한 기본 매핑 처리
    # 노드 타입별 규칙 추가 대신 스키마에서 필수 입력값 정보를 활용
    if node_type in common_node_defaults and len(widgets_values) > 0:
        default_mappings = common_node_defaults[node_type]
        for input_name, value_index in default_mappings.items():
            if value_index < len(widgets_values) and input_name not in inputs:
                inputs[input_name] = widgets_values[value_index]
    
    # 5. 스키마에서 찾은 필수 입력값 중 누락된 것이 있으면 기본값 설정
    for input_name in required_inputs:
        if input_name not in inputs:
            # 위젯값에서 적절한 값 찾기 시도
            found = False
            for i, value in enumerate(widgets_values):
                # 이름 매칭 시도
                if input_name.lower() in get_default_input_name(node_type, i).lower():
                    inputs[input_name] = value
                    found = True
                    break
            
            # 이름 매칭으로 찾지 못했으면 위치 기반 휴리스틱 시도
            if not found and i < len(widgets_values):
                inputs[input_name] = widgets_values[i]
    
    # 6. SaveImage 노드의 경우 filename_prefix가 일반적으로 필요함
    if node_type == "SaveImage" and "filename_prefix" not in inputs and len(widgets_values) > 0:
        inputs["filename_prefix"] = widgets_values[0]
    
    return inputs

# 가장 일반적인 노드 타입에 대한 기본 매핑 정보
common_node_defaults = {
    "CheckpointLoaderSimple": {"ckpt_name": 0},
    "CLIPTextEncode": {"text": 0},
    "EmptyLatentImage": {"width": 0, "height": 1, "batch_size": 2},
    "KSampler": {"seed": 0, "steps": 2, "cfg": 3, "sampler_name": 4, "scheduler": 5, "denoise": 6},
    "SaveImage": {"filename_prefix": 0}
}

def get_default_input_name(node_type: str, index: int) -> str:
    """
    노드 타입별 기본 입력 이름을 가져옵니다.
    
    Args:
        node_type: 노드 타입
        index: 위젯 인덱스
        
    Returns:
        str: 기본 입력 이름
    """
    # 노드 타입별 기본 입력 이름 매핑
    default_names = {
        "CheckpointLoaderSimple": ["ckpt_name"],
        "CLIPTextEncode": ["text"],
        "EmptyLatentImage": ["width", "height", "batch_size"],
        "KSampler": ["seed", "control_after_generate", "steps", "cfg", "sampler_name", "scheduler", "denoise"],
        "SaveImage": ["filename_prefix"]
    }
    
    if node_type in default_names and index < len(default_names[node_type]):
        return default_names[node_type][index]
    
    return f"param_{index}"

def build_input_name_map(workflow: Dict) -> Dict:
    """
    워크플로우에서 입력 이름 매핑을 생성합니다.
    
    Args:
        workflow: 워크플로우 정보
        
    Returns:
        Dict: (노드ID, 링크ID) -> 입력이름 매핑
    """
    input_name_map = {}
    for node in workflow.get("nodes", []):
        for inp in node.get("inputs", []):
            link_id = inp.get("link")
            if link_id is not None:
                input_name_map[(node["id"], link_id)] = inp.get("name")
    return input_name_map

def build_link_map(workflow: Dict) -> Dict:
    """
    워크플로우에서 링크 매핑을 생성합니다.
    
    Args:
        workflow: 워크플로우 정보
        
    Returns:
        Dict: 링크ID -> [소스노드ID, 소스출력인덱스, 대상노드ID, 대상입력인덱스] 매핑
    """
    link_map = {}
    for link in workflow.get("links", []):
        link_id, src_node_id, src_output_idx, dst_node_id, dst_input_idx, link_type = link
        link_map[link_id] = [src_node_id, src_output_idx, dst_node_id, dst_input_idx]
    return link_map

def get_node_title(node: Dict) -> str:
    """
    노드 제목을 가져옵니다.
    
    Args:
        node: 노드 정보
        
    Returns:
        str: 노드 제목
    """
    # 여러 방법으로 노드 제목 결정
    title = node.get("title")
    if title:
        return title
    
    props = node.get("properties", {})
    if "Node name for S&R" in props:
        return props["Node name for S&R"]
    
    return node.get("type", "Unknown Node")

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
        
        # 위젯 값 처리
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