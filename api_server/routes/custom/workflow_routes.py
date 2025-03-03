from aiohttp import web
import json
import os
import logging
import uuid
import aiohttp
from typing import Dict, Any, List, Optional
from api_server.utils.workflow_converter import convert_workflow_to_api, load_and_convert_workflow, validate_workflow
from api_server.utils.config import get_config
from api_server.utils.server_utils import get_comfy_nodes_info

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

        @workflow_routes.post("/api/workflow/convert")
        async def convert_workflow(request):
            """
            워크플로우 JSON 파일을 API 형식으로 변환합니다.
            
            파라미터:
                - workflow_name: 변환할 워크플로우 JSON 파일명
                - output_name: (선택) 출력할 API 워크플로우 JSON 파일명
            """
            try:
                json_data = await request.json()
                workflow_name = json_data.get("workflow_name")
                output_name = json_data.get("output_name")
                use_dynamic_loading = json_data.get("use_dynamic_loading", True)
                
                if not workflow_name:
                    return web.json_response({"error": "workflow_name 파라미터가 필요합니다"}, status=400)
                
                # 워크플로우 파일 경로 생성
                workflow_path = os.path.join(self.workflow_directory, workflow_name)
                
                # 입력 워크플로우 파일이 존재하는지 확인
                if not os.path.exists(workflow_path):
                    return web.json_response({"error": f"워크플로우 파일을 찾을 수 없습니다: {workflow_name}"}, status=404)
                
                # 워크플로우 로드 및 변환
                api_workflow = load_and_convert_workflow(workflow_path, use_dynamic_loading)
                
                # 출력 파일명이 지정된 경우 파일로 저장
                output_path = None
                if output_name:
                    output_path = os.path.join(self.workflow_directory, output_name)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(api_workflow, f, indent=2, ensure_ascii=False)
                    logger.info(f"변환된 워크플로우를 저장했습니다: {output_path}")
                
                # 변환 결과 응답
                return web.json_response({
                    "status": "success",
                    "message": "워크플로우 변환 완료",
                    "api_workflow": api_workflow,
                    "output_path": output_path
                })
                
            except Exception as e:
                logger.error(f"워크플로우 변환 중 오류 발생: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return web.json_response({
                    "error": "워크플로우 변환 실패",
                    "message": str(e)
                }, status=500)

        @workflow_routes.post("/api/workflow/execute")
        async def execute_workflow(request):
            """
            워크플로우 파일을 API 형식으로 변환하고 실행합니다.
            
            파라미터:
                - workflow_name: 실행할 워크플로우 JSON 파일명
                - workflow_path: (선택) 실행할 워크플로우 JSON 파일의 전체 경로
                - extra_data: (선택) 워크플로우에 전달할 추가 데이터
            """
            try:
                json_data = await request.json()
                workflow_name = json_data.get("workflow_name")
                workflow_path = json_data.get("workflow_path")
                extra_data = json_data.get("extra_data", {})
                use_dynamic_loading = json_data.get("use_dynamic_loading", True)
                client_id = json_data.get("client_id", "")
                
                # 워크플로우 파일 찾기
                if not workflow_name and not workflow_path:
                    return web.json_response({"error": "workflow_name 또는 workflow_path 파라미터가 필요합니다"}, status=400)
                
                target_workflow_path = self.find_workflow_file(workflow_name, workflow_path)
                if not target_workflow_path:
                    return web.json_response({"error": f"워크플로우 파일을 찾을 수 없습니다: {workflow_name or workflow_path}"}, status=404)
                
                logger.info(f"워크플로우 파일 경로: {target_workflow_path}")
                
                # 워크플로우 로드 및 변환
                logger.info(f"워크플로우 로드 및 변환 시작: {workflow_name or os.path.basename(target_workflow_path)}")
                try:
                    api_workflow = load_and_convert_workflow(target_workflow_path, use_dynamic_loading)
                    logger.info(f"워크플로우 변환 완료: {len(api_workflow)} 노드")
                except Exception as e:
                    logger.error(f"워크플로우 변환 중 오류 발생: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return web.json_response({
                        "error": "워크플로우 변환 실패",
                        "message": str(e)
                    }, status=500)
                
                # 디버깅을 위해 변환된 API 워크플로우 로깅
                logger.debug(f"변환된 API 워크플로우: {json.dumps(api_workflow, indent=2)}")
                
                # 추가 데이터와 워크플로우 병합
                if extra_data:
                    logger.info(f"추가 데이터 병합: {extra_data}")
                    self.merge_extra_data(api_workflow, extra_data)
                
                # 워크플로우 검증
                validation_result = self.validate_workflow(api_workflow)
                if validation_result["issues"]:
                    logger.warning(f"워크플로우 검증 이슈 발견: {validation_result['issues']}")
                
                # 프롬프트 ID 생성 (UUID 사용)
                prompt_id = str(uuid.uuid4())
                
                # /prompt 엔드포인트로 요청 전송
                # ComfyUI 서버는 /prompt 엔드포인트를 통해 워크플로우 실행을 처리함
                async with aiohttp.ClientSession() as session:
                    # 로컬 서버에 요청 보내기
                    url = f"http://127.0.0.1:{request.url.port}/prompt"
                    
                    # 프롬프트 데이터 구성
                    prompt_data = {
                        "prompt": api_workflow,
                        "client_id": client_id
                    }
                    
                    logger.info(f"프롬프트 요청 전송: {url}")
                    async with session.post(url, json=prompt_data) as response:
                        if response.status == 200:
                            result = await response.json()
                            prompt_id = result.get("prompt_id", prompt_id)
                            number = result.get("number", 0)
                            node_errors = result.get("node_errors", {})
                            logger.info(f"워크플로우 실행 요청 성공: {prompt_id}")
                            
                            # 원래 /prompt 엔드포인트와 동일한 형식의 응답 반환
                            return web.json_response({
                                "prompt_id": prompt_id,
                                "number": number,
                                "node_errors": node_errors
                            })
                        else:
                            error_msg = await response.text()
                            logger.error(f"프롬프트 실행 요청 실패: {error_msg}")
                            
                            # 오류 상세 정보 파싱 시도
                            try:
                                error_json = json.loads(error_msg)
                                # 원래 /prompt 엔드포인트와 동일한 형식의 오류 응답 반환
                                return web.json_response({
                                    "error": error_json.get("error", "워크플로우 실행 실패"),
                                    "node_errors": error_json.get("node_errors", {})
                                }, status=response.status)
                            except:
                                return web.json_response({
                                    "error": f"프롬프트 요청 오류: {error_msg}",
                                    "node_errors": {}
                                }, status=response.status)
                
            except Exception as e:
                logger.error(f"워크플로우 실행 중 오류 발생: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return web.json_response({
                    "error": "워크플로우 실행 실패",
                    "message": str(e)
                }, status=500)
                
        @workflow_routes.get("/api/workflow/list")
        async def list_workflows(request):
            """워크플로우 디렉토리에 있는 모든 JSON 파일 목록을 반환합니다."""
            try:
                workflow_files = []
                for file in os.listdir(self.workflow_directory):
                    if file.endswith(".json"):
                        file_path = os.path.join(self.workflow_directory, file)
                        workflow_files.append({
                            "name": file,
                            "size": os.path.getsize(file_path),
                            "modified": os.path.getmtime(file_path)
                        })
                
                return web.json_response({
                    "status": "success",
                    "workflows": workflow_files,
                    "directory": self.workflow_directory
                })
                
            except Exception as e:
                logger.error(f"워크플로우 목록 조회 중 오류 발생: {str(e)}")
                return web.json_response({
                    "error": "워크플로우 목록 조회 실패",
                    "message": str(e)
                }, status=500)
                
        @workflow_routes.get("/api/workflow/{workflow_name}")
        async def get_workflow(request):
            """특정 워크플로우 파일의 내용을 반환합니다."""
            try:
                workflow_name = request.match_info.get("workflow_name")
                workflow_path = os.path.join(self.workflow_directory, workflow_name)
                
                if not os.path.exists(workflow_path):
                    return web.json_response({
                        "error": f"워크플로우 파일을 찾을 수 없습니다: {workflow_name}"
                    }, status=404)
                
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                
                return web.json_response({
                    "status": "success",
                    "workflow": workflow_data
                })
                
            except Exception as e:
                logger.error(f"워크플로우 조회 중 오류 발생: {str(e)}")
                return web.json_response({
                    "error": "워크플로우 조회 실패",
                    "message": str(e)
                }, status=500)

        self.routes.extend(workflow_routes)

    def merge_extra_data(self, api_workflow: Dict[str, Any], extra_data: Dict[str, Any]) -> None:
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

    def validate_workflow(self, api_workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        워크플로우를 검증하고 필요한 경우 수정합니다.
        
        Args:
            api_workflow: 변환된 API 워크플로우
            
        Returns:
            Dict: 검증 결과 (성공 여부, 문제점 목록)
        """
        validation_result = {
            "success": True,
            "issues": []
        }
        
        # 필수 입력값 검증
        for node_id, node in api_workflow.items():
            node_type = node.get("class_type")
            
            # 특수 케이스 - SaveImage 노드는 filename_prefix가 필요
            if node_type == "SaveImage" and "filename_prefix" not in node.get("inputs", {}):
                # 기본값 설정
                if "inputs" not in node:
                    node["inputs"] = {}
                node["inputs"]["filename_prefix"] = "ComfyUI"
                validation_result["issues"].append(f"노드 {node_id} (SaveImage): filename_prefix가 누락되어 기본값으로 설정")
        
        # 검증 결과 반환
        validation_result["success"] = len(validation_result["issues"]) == 0
        return validation_result

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