import os
import json
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional

from api_server.utils.config import get_config

# 로깅 설정
logger = logging.getLogger(__name__)

# 노드 정보 캐시
_node_info_cache = None

async def get_comfy_nodes_info() -> Dict[str, Any]:
    """
    ComfyUI 서버에서 노드 정보를 가져옵니다.
    
    Returns:
        Dict[str, Any]: 노드 정보
    """
    global _node_info_cache
    
    # 캐시된 정보가 있으면 반환
    if _node_info_cache is not None:
        return _node_info_cache
    
    # ComfyUI 서버에서 노드 정보 가져오기
    comfy_host = get_config().get("comfy_host", "http://127.0.0.1:8188")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{comfy_host}/object_info") as response:
                if response.status != 200:
                    logger.error(f"ComfyUI 서버에서 노드 정보를 가져오는 데 실패했습니다. 상태 코드: {response.status}")
                    return {}
                
                node_info = await response.json()
                _node_info_cache = node_info
                logger.info(f"ComfyUI 서버에서 노드 정보를 가져왔습니다. {len(node_info)} 노드 타입 정보가 있습니다.")
                return node_info
    except Exception as e:
        logger.error(f"ComfyUI 서버 통신 중 오류: {str(e)}")
        return {}

def clear_node_info_cache():
    """
    노드 정보 캐시를 지웁니다.
    서버가 재시작되거나 노드 구성이 변경되었을 때 호출합니다.
    """
    global _node_info_cache
    _node_info_cache = None
    logger.info("노드 정보 캐시가 지워졌습니다.")

async def check_server_status() -> bool:
    """
    ComfyUI 서버가 실행 중인지 확인합니다.
    
    Returns:
        bool: 서버가 실행 중이면 True, 아니면 False
    """
    comfy_host = get_config().get("comfy_host", "http://127.0.0.1:8188")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{comfy_host}/system_stats") as response:
                return response.status == 200
    except Exception:
        return False

async def get_server_history(prompt_id: Optional[str] = None) -> Dict[str, Any]:
    """
    ComfyUI 서버에서 프롬프트 실행 기록을 가져옵니다.
    
    Args:
        prompt_id: 특정 프롬프트 ID (None이면 모든 기록)
        
    Returns:
        Dict[str, Any]: 프롬프트 실행 기록
    """
    comfy_host = get_config().get("comfy_host", "http://127.0.0.1:8188")
    
    try:
        async with aiohttp.ClientSession() as session:
            if prompt_id:
                # 특정 프롬프트 ID에 대한 기록 가져오기
                async with session.get(f"{comfy_host}/history/{prompt_id}") as response:
                    if response.status != 200:
                        logger.error(f"프롬프트 ID {prompt_id}에 대한 기록을 가져오는 데 실패했습니다. 상태 코드: {response.status}")
                        return {}
                    
                    return await response.json()
            else:
                # 모든 기록 가져오기
                async with session.get(f"{comfy_host}/history") as response:
                    if response.status != 200:
                        logger.error(f"프롬프트 기록을 가져오는 데 실패했습니다. 상태 코드: {response.status}")
                        return {}
                    
                    return await response.json()
    except Exception as e:
        logger.error(f"프롬프트 기록을 가져오는 중 오류: {str(e)}")
        return {}

async def get_queue_status() -> Dict[str, Any]:
    """
    ComfyUI 서버의 큐 상태를 가져옵니다.
    
    Returns:
        Dict[str, Any]: 큐 상태 정보
    """
    comfy_host = get_config().get("comfy_host", "http://127.0.0.1:8188")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{comfy_host}/queue") as response:
                if response.status != 200:
                    logger.error(f"큐 상태를 가져오는 데 실패했습니다. 상태 코드: {response.status}")
                    return {}
                
                return await response.json()
    except Exception as e:
        logger.error(f"큐 상태를 가져오는 중 오류: {str(e)}")
        return {} 