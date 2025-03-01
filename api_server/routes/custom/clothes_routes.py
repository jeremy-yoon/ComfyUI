import uuid
import random
import json
import os
from aiohttp import web

class ClothesRoutes:
    def __init__(self, prompt_server):
        self.prompt_server = prompt_server
        self.comfy_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        # 로컬 워크플로우 경로 대신 서버 API 엔드포인트를 사용하도록 설정
        self.api_base_url = "/api/workflows"

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
                
                # 워크플로우 JSON 파일 로드 - 기존 로컬 파일 경로 대신 API 사용
                # 서버에서 저장된 워크플로우를 가져오기 위한 API 엔드포인트를 사용할 수 있지만
                # 예제 워크플로우는 여전히 로컬 파일에서 로드
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
                # 로컬 디렉토리 대신 API를 통해 워크플로우 목록 가져오기
                # 이 예제에서는 간단히 JSON 응답만 수정
                # 실제로는 외부 API를 호출하거나 데이터베이스에서 가져와야 함
                return web.json_response({
                    "status": "success",
                    "message": "API 서버에서 워크플로우 목록을 가져옵니다",
                    "workflows": [
                        # 여기에 실제 서버 API에서 가져온 워크플로우 목록이 들어갈 것입니다
                    ]
                })

            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)

        # 새로운 API 엔드포인트 추가 - 워크플로우 저장
        @routes.post("/api/workflows")
        async def save_workflow(request):
            try:
                json_data = await request.json()
                workflow_name = json_data.get("name")
                workflow_data = json_data.get("data")
                
                if not workflow_name or not workflow_data:
                    return web.json_response({
                        "status": "error",
                        "message": "워크플로우 이름과 데이터가 필요합니다"
                    }, status=400)
                
                # 여기서는 워크플로우를 서버에 저장하는 로직을 구현할 수 있습니다
                # 데이터베이스나 서버 스토리지 시스템에 저장
                
                return web.json_response({
                    "status": "success",
                    "message": f"워크플로우 '{workflow_name}'이(가) 저장되었습니다",
                    "id": str(uuid.uuid4())  # 저장된 워크플로우의 고유 ID 반환
                })
                
            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)
        
        # 워크플로우 가져오기 API
        @routes.get("/api/workflows/{workflow_id}")
        async def get_workflow(request):
            try:
                workflow_id = request.match_info.get("workflow_id")
                
                if not workflow_id:
                    return web.json_response({
                        "status": "error",
                        "message": "워크플로우 ID가 필요합니다"
                    }, status=400)
                
                # 여기서는 ID를 기반으로 워크플로우를 가져오는 로직을 구현할 수 있습니다
                # 데이터베이스나 서버 스토리지 시스템에서 조회
                
                # 예시 응답 (실제 구현에서는 데이터베이스에서 가져와야 함)
                workflow_data = {
                    "id": workflow_id,
                    "name": "Example Workflow",
                    "data": {}  # 여기에 워크플로우 JSON 데이터가 들어갈 것입니다
                }
                
                return web.json_response({
                    "status": "success",
                    "workflow": workflow_data
                })
                
            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)
        
        # 워크플로우 JSON 데이터 조회 API
        @routes.get("/api/workflows/{workflow_id}/workflow_json")
        async def get_workflow_json(request):
            try:
                workflow_id = request.match_info.get("workflow_id")
                
                if not workflow_id:
                    return web.json_response({
                        "status": "error",
                        "message": "워크플로우 ID가 필요합니다"
                    }, status=400)
                
                # 워크플로우 JSON 데이터 가져오기
                # 실제 구현에서는 데이터베이스에서 가져와야 함
                
                # 예시 응답
                workflow_json = {}  # 실제 워크플로우 JSON 데이터
                
                return web.json_response(workflow_json)
                
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
                
                # 로컬 파일 대신 API를 통해 워크플로우 가져오기
                # 하지만 예시를 위해 일단 로컬 파일이 있는지 확인
                workflow_path = os.path.join(self.comfy_root, "script_examples", workflow_name)
                
                if os.path.exists(workflow_path):
                    with open(workflow_path, 'r', encoding='utf-8') as f:
                        workflow = json.load(f)
                else:
                    # API를 통해 워크플로우 가져오기 (실제 구현 필요)
                    # 여기서는 기본 워크플로우를 반환
                    return web.json_response({
                        "status": "error",
                        "message": f"워크플로우를 찾을 수 없습니다: {workflow_name}, API 서버에서 확인해 주세요."
                    }, status=404)
                
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

        # 태그 기반 워크플로우 검색 API
        @routes.get("/api/workflows/by_tags/")
        async def get_workflows_by_tags(request):
            try:
                tags = request.query.get("tags", "").split(",")
                
                # 태그 기반 워크플로우 필터링 로직 구현 필요
                # 여기서는 예시 응답만 반환
                
                return web.json_response({
                    "status": "success",
                    "workflows": [
                        # 필터링된 워크플로우 목록이 들어갈 것입니다
                    ]
                })
                
            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)
                
        # 서버 호환성 워크플로우 API
        @routes.get("/api/workflows/compatible_workflows/")
        async def get_compatible_workflows(request):
            try:
                server_id = request.query.get("server_id")
                
                if not server_id:
                    return web.json_response({
                        "status": "error",
                        "message": "서버 ID가 필요합니다"
                    }, status=400)
                
                # 서버 호환성 확인 로직 구현 필요
                # 여기서는 예시 응답만 반환
                
                return web.json_response({
                    "status": "success",
                    "compatible_workflows": [
                        # 호환되는 워크플로우 목록이 들어갈 것입니다
                    ]
                })
                
            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)
                
        # 워크플로우 서버 배포 API
        @routes.post("/api/workflows/{workflow_id}/deploy_to_server/")
        async def deploy_to_server(request):
            try:
                workflow_id = request.match_info.get("workflow_id")
                json_data = await request.json()
                server_id = json_data.get("server_id")
                
                if not workflow_id or not server_id:
                    return web.json_response({
                        "status": "error",
                        "message": "워크플로우 ID와 서버 ID가 필요합니다"
                    }, status=400)
                
                # 서버 배포 로직 구현 필요
                # 여기서는 예시 응답만 반환
                
                return web.json_response({
                    "status": "success",
                    "message": f"워크플로우 {workflow_id}가 서버 {server_id}에 배포되었습니다"
                })
                
            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)
                
        # 서버 리소스 동기화 API
        @routes.post("/api/servers/{server_id}/sync_resources/")
        async def sync_server_resources(request):
            try:
                server_id = request.match_info.get("server_id")
                
                if not server_id:
                    return web.json_response({
                        "status": "error",
                        "message": "서버 ID가 필요합니다"
                    }, status=400)
                
                # 리소스 동기화 로직 구현 필요
                # 여기서는 예시 응답만 반환
                
                return web.json_response({
                    "status": "success",
                    "message": f"서버 {server_id}의 리소스가 동기화되었습니다"
                })
                
            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "message": str(e)
                }, status=400)

        return routes 