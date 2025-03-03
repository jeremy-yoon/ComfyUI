import uuid
import random
import json
import os
from aiohttp import web
from api_server.utils.workflow_converter import convert_workflow_to_api, save_api_workflow

class ClothesRoutes:
    def __init__(self, prompt_server):
        self.prompt_server = prompt_server
        self.comfy_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.workflow_dir = os.path.join(self.comfy_root, "user", "default", "workflows", "api")
        self.ui_workflow_dir = os.path.join(self.comfy_root, "user", "default", "workflows")

    def get_routes(self):
        routes = web.RouteTableDef()
        
        @routes.post("/api/custom/generate_clothes_v2")
        async def generate_clothes_v2(request):
            try:
                json_data = await request.json()
                image_path = json_data.get("image", "Frame 84.png")
                image_path2 = json_data.get("image2", "Frame 93.png")
                mask_path = json_data.get("mask", "Frame 82ㄴㅇㄻㅇㄴㅁㄹㄴㅁㄴ (4).png")
                prompt_text = json_data.get("prompt", "pixel art, round plush, melting plush, plush wearing pajama, ribbon, clothes are dragging on the floor, fluffy blankets, side view, soft colors, (soft lighting:1.4), soft shading, white background, simple background")
                negative_prompt = json_data.get("negative_prompt", "hand, arm, foot, (outline:1.4), particles")
                seed = json_data.get("seed", random.randint(1, 2**64))
                
                # 워크플로우 JSON 파일 로드
                workflow_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                          "script_examples", "250218_clothes.json")
                
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                
                # 동적 파라미터 업데이트
                workflow["3"]["inputs"]["image"] = image_path
                workflow["16"]["inputs"]["image"] = image_path2
                workflow["35"]["inputs"]["image"] = mask_path
                workflow["6"]["inputs"]["positive_g"] = prompt_text
                workflow["6"]["inputs"]["positive_l"] = prompt_text
                workflow["6"]["inputs"]["negative_g"] = negative_prompt
                workflow["6"]["inputs"]["negative_l"] = negative_prompt
                workflow["6"]["inputs"]["seed"] = seed
                workflow["46"]["inputs"]["seed"] = seed

                prompt_id = str(uuid.uuid4())
                # SaveImage 노드들의 출력을 모두 받도록 설정
                self.prompt_server.prompt_queue.put((self.prompt_server.number, prompt_id, workflow, {}, ["14"]))
                self.prompt_server.number += 1

                return web.json_response({
                    "status": "success",
                    "message": "Clothes image generation queued",
                    "prompt_id": prompt_id
                })

            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)

        @routes.get("/api/custom/workflows")
        async def list_workflows(request):
            try:
                if not os.path.exists(self.workflow_dir):
                    return web.json_response({
                        "status": "error",
                        "message": "Workflow directory not found"
                    }, status=404)

                workflows = [f for f in os.listdir(self.workflow_dir) if f.endswith('.json')]
                
                return web.json_response({
                    "status": "success",
                    "workflows": workflows
                })

            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)

        @routes.post("/api/custom/process_images")
        async def process_images(request):
            try:
                json_data = await request.json()
                
                workflow_name = json_data.get("workflow_name", "250218_clothes.json")
                image_path1 = json_data.get("image_path1")
                image_path2 = json_data.get("image_path2")
                image_path3 = json_data.get("image_path3")
                positive_prompt = json_data.get("positive_prompt", "masterpiece, best quality, high quality, beautiful lighting, detailed, intricate details")
                negative_prompt = json_data.get("negative_prompt", "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry")
                seed = random.randint(1, 2**64)
                
                workflow_path = os.path.join(self.workflow_dir, workflow_name)
                
                if not os.path.exists(workflow_path):
                    return web.json_response({
                        "status": "error",
                        "message": f"Workflow file not found: {workflow_name}"
                    }, status=404)
                
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                
                # SaveImage 노드들 찾기
                save_image_nodes = []
                for node_id, node_data in workflow.items():
                    if node_data.get("class_type") == "SaveImage":
                        save_image_nodes.append(node_id)
                
                if image_path1:
                    if "2000" in workflow and "inputs" in workflow["2000"]:
                        workflow["2000"]["inputs"]["image"] = image_path1
                if image_path2:
                    if "2001" in workflow and "inputs" in workflow["2001"]:
                        workflow["2001"]["inputs"]["image"] = image_path2
                if image_path3:
                    if "2002" in workflow and "inputs" in workflow["2002"]:
                        workflow["2002"]["inputs"]["image"] = image_path3
                if positive_prompt:
                    if "1000" in workflow and "inputs" in workflow["1000"]:
                        workflow["1000"]["inputs"]["positive_g"] = positive_prompt
                        workflow["1000"]["inputs"]["positive_l"] = positive_prompt
                if negative_prompt:
                    if "1000" in workflow and "inputs" in workflow["1000"]:
                        workflow["1000"]["inputs"]["negative_g"] = negative_prompt
                        workflow["1000"]["inputs"]["negative_l"] = negative_prompt

                # 시드 적용
                if "3000" in workflow and "inputs" in workflow["3000"]:
                    workflow["3000"]["inputs"]["seed"] = seed

                prompt_id = str(uuid.uuid4())
                # SaveImage 노드들의 출력을 모두 받도록 설정
                self.prompt_server.prompt_queue.put((self.prompt_server.number, prompt_id, workflow, {}, save_image_nodes))
                self.prompt_server.number += 1

                return web.json_response({
                    "status": "success",
                    "message": "Image generation queued",
                    "prompt_id": prompt_id,
                    "data": {
                        "workflow_name": workflow_name,
                        "image_path1": image_path1,
                        "image_path2": image_path2,
                        "image_path3": image_path3,
                        "positive_prompt": positive_prompt,
                        "negative_prompt": negative_prompt,
                        "seed": seed
                    }
                })

            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)

        @routes.post("/api/custom/convert_workflow")
        async def convert_workflow(request):
            """
            일반 ComfyUI 워크플로우를 API 워크플로우로 변환합니다.
            
            요청 파라미터:
            - workflow_name: 변환할 워크플로우 파일 이름
            - save_converted: 변환된 워크플로우를 파일로 저장할지 여부 (선택, 기본값: True)
            - use_dynamic_loading: ComfyUI 노드 정의를 동적으로 로드할지 여부 (선택, 기본값: True)
            
            응답:
            - 성공 시: 변환된 API 워크플로우 JSON
            - 실패 시: 오류 메시지
            """
            try:
                json_data = await request.json()
                workflow_name = json_data.get("workflow_name")
                save_converted = json_data.get("save_converted", True)
                use_dynamic_loading = json_data.get("use_dynamic_loading", True)
                
                if not workflow_name:
                    return web.json_response({
                        "status": "error",
                        "message": "Workflow name is required"
                    }, status=400)
                
                # UI 워크플로우 디렉토리 경로 구성
                source_path = os.path.join(self.ui_workflow_dir, workflow_name)
                
                # 만약 파일명만 입력했다면 (확장자가 없는 경우) .json 확장자 추가
                if not os.path.exists(source_path) and not source_path.endswith('.json'):
                    source_path = source_path + '.json'
                
                if not os.path.exists(source_path):
                    return web.json_response({
                        "status": "error",
                        "message": f"Workflow file not found: {workflow_name}"
                    }, status=404)
                
                # 워크플로우 파일 로드
                with open(source_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                
                # API 워크플로우로 변환
                api_workflow = convert_workflow_to_api(workflow, use_dynamic_loading)
                
                # 변환된 워크플로우 저장 (선택적)
                if save_converted:
                    # API 워크플로우 디렉토리가 없으면 생성
                    if not os.path.exists(self.workflow_dir):
                        os.makedirs(self.workflow_dir, exist_ok=True)
                    
                    # 출력 파일 경로 구성
                    file_name = os.path.basename(source_path)
                    if file_name.endswith('.json'):
                        file_name = file_name[:-5]  # .json 확장자 제거
                    
                    output_path = os.path.join(self.workflow_dir, f"{file_name}_api.json")
                    
                    # 변환된 워크플로우 저장
                    save_api_workflow(api_workflow, output_path)
                
                return web.json_response({
                    "status": "success",
                    "message": "Workflow converted successfully",
                    "data": {
                        "source_path": source_path,
                        "output_path": output_path if save_converted else None,
                        "workflow": api_workflow
                    }
                })
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=500)

        @routes.post("/api/custom/convert_and_generate")
        async def convert_and_generate(request):
            """
            일반 ComfyUI 워크플로우를 API 워크플로우로 변환하고 즉시 이미지를 생성합니다.
            
            요청 파라미터:
            - workflow_name: 변환할 워크플로우 파일 이름
            - use_dynamic_loading: ComfyUI 노드 정의를 동적으로 로드할지 여부 (선택, 기본값: True)
            - save_converted: 변환된 워크플로우를 파일로 저장할지 여부 (선택, 기본값: False)
            - parameters: 워크플로우 실행 시 적용할 파라미터 (선택)
              예: {"positive_prompt": "멋진 풍경", "negative_prompt": "저품질, 흐릿함", "seed": 12345}
            
            응답:
            - 성공 시: 변환 및 생성 요청 정보
            - 실패 시: 오류 메시지
            """
            try:
                json_data = await request.json()
                workflow_name = json_data.get("workflow_name")
                use_dynamic_loading = json_data.get("use_dynamic_loading", True)
                save_converted = json_data.get("save_converted", False)
                parameters = json_data.get("parameters", {})
                
                if not workflow_name:
                    return web.json_response({
                        "status": "error",
                        "message": "Workflow name is required"
                    }, status=400)
                
                # UI 워크플로우 디렉토리 경로 구성
                source_path = os.path.join(self.ui_workflow_dir, workflow_name)
                
                # 만약 파일명만 입력했다면 (확장자가 없는 경우) .json 확장자 추가
                if not os.path.exists(source_path) and not source_path.endswith('.json'):
                    source_path = source_path + '.json'
                
                if not os.path.exists(source_path):
                    return web.json_response({
                        "status": "error",
                        "message": f"Workflow file not found: {workflow_name}"
                    }, status=404)
                
                # 워크플로우 파일 로드
                with open(source_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                
                # API 워크플로우로 변환
                api_workflow = convert_workflow_to_api(workflow, use_dynamic_loading)
                
                # 변환된 워크플로우 저장 (선택적)
                output_path = None
                if save_converted:
                    # API 워크플로우 디렉토리가 없으면 생성
                    if not os.path.exists(self.workflow_dir):
                        os.makedirs(self.workflow_dir, exist_ok=True)
                    
                    # 출력 파일 경로 구성
                    file_name = os.path.basename(source_path)
                    if file_name.endswith('.json'):
                        file_name = file_name[:-5]  # .json 확장자 제거
                    
                    output_path = os.path.join(self.workflow_dir, f"{file_name}_api.json")
                    
                    # 변환된 워크플로우 저장
                    save_api_workflow(api_workflow, output_path)
                
                # 워크플로우에 파라미터 적용
                self._apply_parameters_to_workflow(api_workflow, parameters)
                
                # SaveImage 노드 찾기
                save_image_nodes = []
                for node_id, node_data in api_workflow.items():
                    if node_data.get("class_type") == "SaveImage":
                        save_image_nodes.append(node_id)
                
                # 프롬프트 ID 생성 및 워크플로우 실행
                prompt_id = str(uuid.uuid4())
                self.prompt_server.prompt_queue.put(
                    (self.prompt_server.number, prompt_id, api_workflow, {}, save_image_nodes)
                )
                self.prompt_server.number += 1
                
                return web.json_response({
                    "status": "success",
                    "message": "Workflow converted and image generation queued",
                    "data": {
                        "source_path": source_path,
                        "output_path": output_path,
                        "prompt_id": prompt_id,
                        "parameters": parameters
                    }
                })
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=500)
        
        return routes
    
    def _apply_parameters_to_workflow(self, workflow, parameters):
        """
        워크플로우에 사용자 파라미터를 적용합니다.
        
        Args:
            workflow (dict): API 워크플로우
            parameters (dict): 적용할 파라미터
        """
        # 프롬프트 관련 파라미터 적용
        if "positive_prompt" in parameters or "negative_prompt" in parameters:
            for node_id, node in workflow.items():
                # CLIPTextEncode 노드 찾기
                if node.get("class_type") == "CLIPTextEncode":
                    if "positive_prompt" in parameters and "text" in node.get("inputs", {}):
                        workflow[node_id]["inputs"]["text"] = parameters["positive_prompt"]
                
                # 다른 노드 타입에서 프롬프트 관련 입력 찾기
                inputs = node.get("inputs", {})
                if "positive_g" in inputs and "positive_prompt" in parameters:
                    workflow[node_id]["inputs"]["positive_g"] = parameters["positive_prompt"]
                    workflow[node_id]["inputs"]["positive_l"] = parameters["positive_prompt"]
                if "negative_g" in inputs and "negative_prompt" in parameters:
                    workflow[node_id]["inputs"]["negative_g"] = parameters["negative_prompt"]
                    workflow[node_id]["inputs"]["negative_l"] = parameters["negative_prompt"]
        
        # 시드 적용
        if "seed" in parameters:
            seed_value = parameters["seed"]
            for node_id, node in workflow.items():
                if node.get("class_type") == "KSampler" and "seed" in node.get("inputs", {}):
                    workflow[node_id]["inputs"]["seed"] = seed_value
        
        # 이미지 파일 파라미터 적용
        if "image_paths" in parameters and isinstance(parameters["image_paths"], dict):
            for node_id, image_path in parameters["image_paths"].items():
                if node_id in workflow and "inputs" in workflow[node_id] and "image" in workflow[node_id]["inputs"]:
                    workflow[node_id]["inputs"]["image"] = image_path 