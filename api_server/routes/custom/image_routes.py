import os
import mimetypes
import shutil
from aiohttp import web
import folder_paths
from api_server.scripts.object_extractor import remove_similar_pixels_with_mask
import tempfile
from datetime import datetime

class ImageRoutes:
    def __init__(self, prompt_server):
        self.prompt_server = prompt_server

    def get_routes(self):
        routes = web.RouteTableDef()
        
        @routes.get("/api/custom/files")
        async def list_files(request):
            type = request.query.get("type", "input")
            subfolder = request.query.get("subfolder", "")
            
            base_dir = folder_paths.get_directory_by_type(type)
            if base_dir is None:
                return web.Response(status=400, text="Invalid type")
                
            target_dir = os.path.join(base_dir, subfolder)
            if not os.path.exists(target_dir):
                return web.Response(status=404, text="Directory not found")
                
            # 경로 검증
            if os.path.commonpath((os.path.abspath(target_dir), base_dir)) != base_dir:
                return web.Response(status=403, text="Access denied")
            
            result = []
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                result.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None,
                    "path": os.path.relpath(item_path, base_dir).replace("\\", "/")
                })
            
            return web.json_response(result)

        @routes.get("/api/custom/files/download")
        async def get_file(request):
            type = request.query.get("type", "input")
            file_path = request.query.get("path", "")
            
            if not file_path:
                return web.Response(status=400, text="File path is required")
            
            base_dir = folder_paths.get_directory_by_type(type)
            if base_dir is None:
                return web.Response(status=400, text="Invalid type")
                
            full_path = os.path.join(base_dir, file_path)
            if not os.path.isfile(full_path):
                return web.Response(status=404, text="File not found")
                
            # 경로 검증
            if os.path.commonpath((os.path.abspath(full_path), base_dir)) != base_dir:
                return web.Response(status=403, text="Access denied")
                
            content_type = mimetypes.guess_type(full_path)[0] or 'application/octet-stream'
            return web.FileResponse(
                full_path,
                headers={
                    "Content-Type": content_type,
                    "Content-Disposition": f"filename=\"{os.path.basename(file_path)}\""
                }
            )

        @routes.post("/api/custom/files/upload")
        async def upload_file(request):
            data = await request.post()
            file = data.get("file")
            type = data.get("type", "input")
            path = data.get("path", "")
            
            if not file:
                return web.Response(status=400, text="File is required")
                
            base_dir = folder_paths.get_directory_by_type(type)
            if base_dir is None:
                return web.Response(status=400, text="Invalid type")
                
            target_dir = os.path.join(base_dir, os.path.dirname(path))
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            # 경로 검증
            if os.path.commonpath((os.path.abspath(target_dir), base_dir)) != base_dir:
                return web.Response(status=403, text="Access denied")
                
            file_path = os.path.join(base_dir, path)
            with open(file_path, 'wb') as f:
                f.write(file.file.read())
                
            return web.Response(status=201)

        @routes.delete("/api/custom/files")
        async def delete_item(request):
            type = request.query.get("type", "input")
            path = request.query.get("path", "")
            
            if not path:
                return web.Response(status=400, text="Path is required")
                
            base_dir = folder_paths.get_directory_by_type(type)
            if base_dir is None:
                return web.Response(status=400, text="Invalid type")
                
            full_path = os.path.join(base_dir, path)
            if not os.path.exists(full_path):
                return web.Response(status=404, text="Path not found")
                
            # 경로 검증
            if os.path.commonpath((os.path.abspath(full_path), base_dir)) != base_dir:
                return web.Response(status=403, text="Access denied")
                
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
                
            return web.Response(status=200)

        @routes.post("/api/custom/files/directory")
        async def create_directory(request):
            type = request.query.get("type", "input")
            path = request.query.get("path", "")
            
            if not path:
                return web.Response(status=400, text="Path is required")
                
            base_dir = folder_paths.get_directory_by_type(type)
            if base_dir is None:
                return web.Response(status=400, text="Invalid type")
                
            full_path = os.path.join(base_dir, path)
            
            # 경로 검증
            if os.path.commonpath((os.path.abspath(full_path), base_dir)) != base_dir:
                return web.Response(status=403, text="Access denied")
                
            if os.path.exists(full_path):
                return web.Response(status=400, text="Directory already exists")
                
            os.makedirs(full_path)
            return web.Response(status=201)

        @routes.post("/api/custom/extract-object")
        async def extract_object(request):
            try:
                # multipart 폼 데이터 파싱
                reader = await request.multipart()
                
                # 이미지 파일 필드 처리
                field = await reader.next()
                if field is None or field.name != "image":
                    return web.Response(status=400, text="Image file is required")
                
                # 임시 파일로 이미지 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                    target_image_path = temp_file.name
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        temp_file.write(chunk)
                
                # 고정 경로 설정
                base_dir = folder_paths.get_directory_by_type("input")
                comparison_image_path = os.path.join(base_dir, "utils", "comparison_image.png")
                mask_image_path = os.path.join(base_dir, "utils", "mask_image.png")
                
                # 결과물 저장 경로 설정
                result_dir = os.path.join(base_dir, "extracted_objects", datetime.now().strftime("%Y%m%d_%H%M%S"))
                os.makedirs(result_dir, exist_ok=True)
                
                output_filename = "extracted_result.png"
                output_path = os.path.join(result_dir, output_filename)
                
                try:
                    # 이미지 처리 실행
                    remove_similar_pixels_with_mask(
                        target_image_path,
                        comparison_image_path,
                        mask_image_path,
                        output_path,
                        similarity_threshold=30,
                        removal_strength=10
                    )
                finally:
                    # 임시 파일 삭제
                    try:
                        os.unlink(target_image_path)
                    except:
                        pass
                
                # 결과 파일 확인
                if not os.path.exists(output_path):
                    return web.Response(status=500, text="Failed to process image")
                    
                # 상대 경로 계산
                relative_path = os.path.relpath(output_path, base_dir).replace("\\", "/")
                
                # 결과 반환
                return web.json_response({
                    "status": "success",
                    "result_path": relative_path
                })
                
            except Exception as e:
                return web.Response(status=500, text=str(e))

        return routes 