from aiohttp import web
import json
import os
import logging
import uuid
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
# from api_server.utils.workflow_converter import convert_workflow_to_api, load_and_convert_workflow, validate_workflow
from api_server.utils.config import get_config
from api_server.utils.server_utils import get_comfy_nodes_info
# aiohttp와 fastapi를 동시에 사용하고 있습니다. 
# 아래 주석 처리된 부분은 fastapi 사용 시 필요한 임포트입니다.
# 현재 코드는 aiohttp를 기반으로 작성되어 있습니다.
# from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends
# from pydantic import BaseModel

logger = logging.getLogger("workflow_routes")

class WorkflowRoutes:
    def __init__(self, prompt_server):
        self.prompt_server = prompt_server
        self.routes = []
        self.setup_routes()
        
        # ComfyUI 기본 경로 찾기 (현재 스크립트의 상위 디렉토리)
        self.comfy_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # 워크플로우 디렉토리 경로 설정
        self.workflow_directory = os.path.join(self.comfy_dir, "user", "default", "workflows")
        
        # 워크플로우 디렉토리가 없으면 생성
        os.makedirs(self.workflow_directory, exist_ok=True)
        logger.info(f"워크플로우 디렉토리 설정: {self.workflow_directory}")
        
        # 워크플로우를 찾을 수 있는 추가 경로
        self.additional_workflow_paths = [
            os.path.join(self.comfy_dir, "workflows"),  # 기본 workflows 디렉토리
            os.path.join(os.getcwd(), "workflows"),     # 현재 작업 디렉토리의 workflows
            os.getcwd()                                # 현재 작업 디렉토리
        ]

    def setup_routes(self):
        """라우트를 설정합니다."""
        workflow_routes = web.RouteTableDef()

        @workflow_routes.post("/api/workflow/execute")
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
                    api_workflow_name = f"{workflow_name}_api"
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
                        api_workflow = self.merge_extra_data(api_workflow, extra_data)
                    
                    # 워크플로우 검증
                    missing_inputs = self.validate_workflow(api_workflow)
                    if missing_inputs:
                        error_msg = f"워크플로우에 필수 입력 값이 누락되었습니다: {missing_inputs}"
                        logger.error(error_msg)
                        return web.json_response({
                            "error": error_msg
                        }, status=400)
                    
                    # 서버에 워크플로우 실행 요청
                    prompt_request = {
                        "prompt": api_workflow,
                        "client_id": client_id
                    }
                    
                    logger.debug(f"서버에 보내는 프롬프트 요청: {json.dumps(prompt_request, indent=2, ensure_ascii=False)}")
                    
                    # 서버에 HTTP 요청 전송
                    comfy_host = get_config().get("comfy_host", "http://127.0.0.1:8188")
                    async with aiohttp.ClientSession() as session:
                        async with session.post(f"{comfy_host}/prompt", json=prompt_request) as response:
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
             
    def merge_extra_data(self, api_workflow: Dict[str, Any], extra_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 워크플로우에 추가 데이터를 병합합니다.
        
        Args:
            api_workflow: API 워크플로우 데이터
            extra_data: 병합할 추가 데이터 (노드 ID -> 입력 값 매핑)
        """
        for node_id, inputs in extra_data.items():
            if node_id in api_workflow:
                # 노드의 입력 값 업데이트
                if "inputs" in api_workflow[node_id]:
                    api_workflow[node_id]["inputs"].update(inputs)
            else:
                logger.warning(f"노드 ID를 찾을 수 없습니다: {node_id}")
        return api_workflow

    def validate_workflow(self, api_workflow: Dict[str, Any]) -> List[str]:
        """
        워크플로우가 유효한지 검사합니다.
        모든 노드에 필수 입력이 있는지 확인합니다.
        
        Args:
            api_workflow: API 형식의 워크플로우
            
        Returns:
            List[str]: 누락된 필수 입력 목록
        """
        missing_inputs = []
        
        # ComfyUI 서버에서 노드 정보 가져오기 시도
        node_info = {}
        try:
            # 비동기 컨텍스트가 아니므로 임시 이벤트 루프 사용
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            from api_server.utils.server_utils import get_comfy_nodes_info
            node_info = loop.run_until_complete(get_comfy_nodes_info())
            loop.close()
        except Exception as e:
            logger.warning(f"노드 정보를 가져오는데 실패했습니다: {str(e)}")
        
        # 각 노드 검증
        for node_id, node in api_workflow.items():
            node_type = node.get("class_type")
            node_inputs = node.get("inputs", {})
            
            # 서버 노드 정보에서 필수 입력 찾기
            required_inputs = []
            if node_info and node_type in node_info and "input" in node_info[node_type]:
                for input_name, input_info in node_info[node_type]["input"].items():
                    # 필수 입력 여부 확인 (optional 키가 없거나 False인 경우)
                    if isinstance(input_info, dict) and input_info.get("optional", False) == False:
                        required_inputs.append(input_name)
                    elif isinstance(input_info, list) and len(input_info) > 1:
                        # 리스트 형태의 입력 정보에서 필수 여부 확인
                        optional = False
                        for item in input_info:
                            if isinstance(item, dict) and "optional" in item:
                                optional = item["optional"]
                                break
                        if not optional:
                            required_inputs.append(input_name)
            
            # 필수 입력이 없는 경우의 처리
            if not required_inputs:
                # 주의: 여기서 하드코딩된 노드 타입별 필수 입력 목록을 사용하지 마세요!
                # 모든 노드 타입은 서버에서 동적으로 정보를 가져와 처리해야 합니다.
                # 하드코딩된 매핑은 유지보수가 어렵고 새로운 노드 타입이나 변경사항을 반영하지 못합니다.
                logger.warning(f"노드 타입 '{node_type}'의 필수 입력 정보를 서버에서 가져오지 못했습니다. 검증을 건너뜁니다.")
                continue
            
            # 필수 입력 확인
            for req_input in required_inputs:
                if req_input not in node_inputs:
                    missing_inputs.append(f"노드 {node_id} ({node_type}): '{req_input}' 입력 누락")
        
        return missing_inputs

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
            for dir_path in self.additional_workflow_paths:
                path = os.path.join(dir_path, workflow_name)
                if os.path.exists(path):
                    return path
                    
            # 확장자가 없는 경우 .json 확장자 추가하여 재시도
            if not workflow_name.lower().endswith('.json'):
                return self.find_workflow_file(workflow_name + '.json', None)
                
        return None

    def get_routes(self):
        """설정된 라우트를 반환합니다."""
        return self.routes 