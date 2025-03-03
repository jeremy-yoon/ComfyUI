import uuid
import random
import json
import os
from aiohttp import web

class ClothesRoutes:
    def __init__(self, prompt_server):
        self.prompt_server = prompt_server
        self.comfy_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.workflow_dir = os.path.join(self.comfy_root, "user", "default", "workflows", "api")

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

        return routes 