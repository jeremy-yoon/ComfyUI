from aiohttp import web
import json
import os
import logging
import uuid
import aiohttp
import asyncio
from typing import Dict, Any, List

logger = logging.getLogger("workflow_routes")
logger.setLevel(logging.DEBUG)  # 이 로거의 레벨을 DEBUG로 설정

class WorkflowRoutes:
    def __init__(self, prompt_server):
        self.prompt_server = prompt_server
        
        # ComfyUI 기본 경로 찾기 (현재 스크립트의 상위 디렉토리)
        self.comfy_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # 워크플로우 디렉토리 경로 설정
        self.workflow_directory = os.path.join(self.comfy_dir, "user", "default", "workflows")
        
        # 워크플로우 디렉토리가 없으면 생성
        os.makedirs(self.workflow_directory, exist_ok=True)
        logger.info(f"워크플로우 디렉토리 설정: {self.workflow_directory}")
        
        # 워크플로우 디렉토리 탐색 경로 설정
        self.workflow_search_paths = [
            self.workflow_directory,                   # 워크플로우 기본 디렉토리
            os.path.join(self.comfy_dir, "user/default/workflows"), # 프로젝트 루트의 workflows 디렉토리
            os.getcwd()                                # 현재 작업 디렉토리
        ]

    def get_routes(self):
        """라우트를 설정합니다."""
        routes = web.RouteTableDef()

        @routes.post("/api/workflow/execute")
        async def execute_workflow(request):
            """
            워크플로우 실행 API 엔드포인트
            
            Args:
                request: 워크플로우 실행 요청 모델
                background_tasks: FastAPI 백그라운드 작업 객체
                
            Returns:
                Dict: 워크플로우 실행 응답
            """
            try:
                # 요청 데이터를 비동기적으로 파싱
                request_data = await request.json()
                
                workflow_name = request_data.get("workflow_name")
                extra_data = request_data.get("extra_data", {})
                client_id = request_data.get("client_id", "")
                
                if not workflow_name:
                    return web.json_response({
                        "error": "workflow_name 파라미터가 필요합니다."
                    }, status=400)
                
                # 워크플로우 경로 결정
                workflow_path = self.find_workflow_file(workflow_name)
                if not workflow_path:
                    return web.json_response({
                        "error": f"워크플로우 '{workflow_name}'을 찾을 수 없습니다."
                    }, status=404)
                
                try:
                    # 워크플로우 파일 로드
                    with open(workflow_path, "r", encoding="utf-8") as f:
                        workflow_data = json.load(f)
                    
                    # 워크플로우 데이터 로깅 (디버깅용)
                    logger.debug(f"원본 워크플로우 데이터: {json.dumps(workflow_data, indent=2, ensure_ascii=False)}")
                    
                    # API 전용 워크플로우 파일 찾기 (원래 이름 + _api)
                    api_workflow_name = f"{workflow_name}_api.json"
                    api_workflow_path = self.find_workflow_file(api_workflow_name)
                    
                    if api_workflow_path:
                        # API 워크플로우 파일 로드
                        with open(api_workflow_path, "r", encoding="utf-8") as f:
                            api_workflow = json.load(f)
                        logger.debug(f"API 워크플로우 데이터 로드됨: {api_workflow_path}")
                    else:
                        return web.json_response({
                            "error": f"API 워크플로우 '{api_workflow_name}'을 찾을 수 없습니다."
                        }, status=404)
                    
                    # 추가 데이터 병합
                    if extra_data:
                        logger.debug(f"병합 전 extra_data: {json.dumps(extra_data, indent=2, ensure_ascii=False)}")
                        api_workflow = self.merge_extra_data(api_workflow, extra_data)
                        logger.debug(f"extra_data 병합 후 워크플로우: {json.dumps(api_workflow, indent=2, ensure_ascii=False)}")
                    
                    # 서버에 워크플로우 실행 요청
                    prompt_request = {
                        "prompt": api_workflow,
                        "client_id": client_id
                    }
                    
                    logger.debug(f"서버에 보내는 프롬프트 요청: {json.dumps(prompt_request, indent=2, ensure_ascii=False)}")
                    
                    # 서버에 HTTP 요청 전송
                    comfy_host = f"http://127.0.0.1:{request.url.port}/prompt"
                    async with aiohttp.ClientSession() as session:
                        async with session.post(comfy_host, json=prompt_request) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                logger.error(f"워크플로우 실행 오류 (상태 코드: {response.status}): {error_text}")
                                return web.json_response({
                                    "error": f"ComfyUI 서버에서 오류 발생: {error_text}"
                                }, status=response.status)
                                
                            result = await response.json()
                            logger.debug(f"워크플로우 실행 결과: {result}")
                            return web.json_response({
                                "status": "success",
                                "message": "워크플로우 실행이 시작되었습니다.",
                                "prompt_id": result.get("prompt_id"),
                                "node_count": len(api_workflow)
                            })
                
                except Exception as e:
                    logger.error(f"워크플로우 실행 중 오류 발생: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return web.json_response({
                        "error": "워크플로우 실행 실패",
                        "message": str(e)
                    }, status=500)
                
            except Exception as e:
                logger.error(f"워크플로우 실행 요청 처리 중 오류 발생: {str(e)}")
                return web.json_response({
                    "error": "요청 처리 실패",
                    "message": str(e)
                }, status=500)
             
        return routes

    def merge_extra_data(self, api_workflow: Dict[str, Any], extra_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 워크플로우에 추가 데이터를 병합합니다.
        
        Args:
            api_workflow: API 워크플로우 데이터
            extra_data: 병합할 추가 데이터 (노드 ID 또는 meta.title -> 입력 값 매핑)
        """
        # 타이틀을 기반으로 노드 ID를 찾는 매핑 생성
        title_to_node_id = {}
        for node_id, node_data in api_workflow.items():
            if isinstance(node_data, dict) and "_meta" in node_data and "title" in node_data["_meta"]:
                title = node_data["_meta"]["title"]
                title_to_node_id[title] = node_id
        
        logger.debug(f"생성된 title_to_node_id 매핑: {title_to_node_id}")
        logger.debug(f"병합할 extra_data 키: {list(extra_data.keys())}")
        
        for key, inputs in extra_data.items():
            # 먼저 키가 직접 노드 ID인지 확인
            if key in api_workflow:
                node_id = key
                logger.debug(f"노드 ID로 직접 찾음: {key}")
                if "inputs" in api_workflow[node_id]:
                    self._update_node_inputs(api_workflow[node_id]["inputs"], inputs)
                else:
                    logger.warning(f"노드 ID {key}에 'inputs' 필드가 없습니다.")
            # 그 다음 키가 노드 타이틀인지 확인
            elif key in title_to_node_id:
                node_id = title_to_node_id[key]
                logger.debug(f"노드 타이틀로 찾음: {key} -> 노드 ID: {node_id}")
                if "inputs" in api_workflow[node_id]:
                    self._update_node_inputs(api_workflow[node_id]["inputs"], inputs)
                else:
                    logger.warning(f"노드 ID {node_id} (타이틀: {key})에 'inputs' 필드가 없습니다.")
            else:
                logger.warning(f"노드 ID 또는 타이틀을 찾을 수 없습니다: {key}")
        
        return api_workflow
        
    def _update_node_inputs(self, current_inputs: Dict[str, Any], new_inputs: Dict[str, Any]) -> None:
        """
        노드의 입력 값을 지능적으로 업데이트합니다.
        배열 값의 경우 첫 번째 요소만 제공되었을 때 나머지 요소를 유지합니다.
        
        Args:
            current_inputs: 현재 노드 입력 값
            new_inputs: 새로운 노드 입력 값
        """
        logger.debug(f"_update_node_inputs 호출 - 현재 입력: {current_inputs}, 새 입력: {new_inputs}")
        
        for input_key, input_value in new_inputs.items():
            if input_key in current_inputs:
                current_value = current_inputs[input_key]
                
                # 문자열만 제공된 경우 배열 형태를 유지
                if isinstance(current_value, list) and not isinstance(input_value, list):
                    # 입력값이 단일 문자열이고 현재 배열의 첫 번째 요소가 문자열인 경우
                    if isinstance(input_value, str) and len(current_value) > 0 and isinstance(current_value[0], str):
                        logger.debug(f"배열의 첫 번째 문자열 요소 업데이트: {input_key} - {current_value[0]} -> {input_value}")
                        current_inputs[input_key][0] = input_value
                    else:
                        # 기존 배열의 첫 번째 요소만 업데이트
                        if len(current_value) > 0:
                            logger.debug(f"배열의 첫 번째 요소 업데이트: {input_key} - {current_value[0]} -> {input_value}")
                            current_value[0] = input_value
                elif isinstance(current_value, list) and isinstance(input_value, list) and len(input_value) == 1 and len(current_value) > 1:
                    # 요소가 하나만 있는 배열이 제공된 경우, 첫 번째 요소만 업데이트하고 나머지는 유지
                    logger.debug(f"배열 첫 번째 요소만 업데이트 (배열->배열): {input_key} - {current_value[0]} -> {input_value[0]}")
                    current_value[0] = input_value[0]
                else:
                    # 그 외의 경우 직접 업데이트
                    logger.debug(f"값 직접 업데이트: {input_key} - {current_value} -> {input_value}")
                    current_inputs[input_key] = input_value
            else:
                # 존재하지 않는 입력 키는 그대로 추가
                logger.debug(f"새 입력 키 추가: {input_key} = {input_value}")
                current_inputs[input_key] = input_value
                
        logger.debug(f"_update_node_inputs 결과: {current_inputs}")

    def find_workflow_file(self, workflow_name, workflow_path=None):
        """
        워크플로우 파일을 여러 위치에서 찾습니다.
        
        Args:
            workflow_name: 워크플로우 파일 이름
            workflow_path: 전체 워크플로우 파일 경로 (선택적)
            
        Returns:
            str: 찾은 워크플로우 파일 경로 또는 None
        """
        # 1. 전체 경로가 제공된 경우
        if workflow_path and os.path.exists(workflow_path):
            return workflow_path
            
        # 2. 파일 이름이 제공된 경우
        if workflow_name:
            # 기본 워크플로우 디렉토리에서 검색
            path = os.path.join(self.workflow_directory, workflow_name)
            if os.path.exists(path):
                return path
                
            # 추가 경로에서 검색
            for dir_path in self.workflow_search_paths:
                path = os.path.join(dir_path, workflow_name)
                if os.path.exists(path):
                    return path
                    
            # 확장자가 없는 경우 .json 확장자 추가하여 재시도
            if not workflow_name.lower().endswith('.json'):
                return self.find_workflow_file(workflow_name + '.json', None)
                
        return None 