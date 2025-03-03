import os
import json
import logging
from typing import Dict, Any

# 로깅 설정
logger = logging.getLogger(__name__)

# 기본 설정 값
DEFAULT_CONFIG = {
    "comfy_host": "http://127.0.0.1:8188",
    "workflow_dir": "workflows",
    "output_dir": "outputs",
    "api_server_port": 8000,
    "api_server_host": "0.0.0.0"
}

# 구성 파일 경로
CONFIG_FILE = os.environ.get("COMFY_API_CONFIG", "config.json")

# 글로벌 설정 변수
_config = None

def load_config() -> Dict[str, Any]:
    """
    구성 파일을 로드합니다.
    파일이 없는 경우 기본 설정을 사용합니다.
    
    Returns:
        Dict[str, Any]: 구성 정보
    """
    global _config
    
    if _config is not None:
        return _config
    
    # 환경에서 설정 시도
    config = DEFAULT_CONFIG.copy()
    
    # 파일에서 설정 로드 시도
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                config.update(file_config)
                logger.info(f"구성 파일 {CONFIG_FILE}에서 설정을 로드했습니다.")
        except Exception as e:
            logger.error(f"구성 파일 {CONFIG_FILE} 로드 중 오류 발생: {str(e)}")
    else:
        logger.info(f"구성 파일 {CONFIG_FILE}이 없습니다. 기본 설정을 사용합니다.")
        
        # 기본 구성 파일 생성
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
            logger.info(f"기본 구성 파일 {CONFIG_FILE}을 생성했습니다.")
        except Exception as e:
            logger.warning(f"기본 구성 파일 생성 실패: {str(e)}")
    
    # 환경 변수에서 설정 오버라이드
    for key in config:
        env_key = f"COMFY_API_{key.upper()}"
        if env_key in os.environ:
            # 타입에 따라 변환
            if isinstance(config[key], bool):
                config[key] = os.environ[env_key].lower() in ("true", "1", "yes")
            elif isinstance(config[key], int):
                config[key] = int(os.environ[env_key])
            else:
                config[key] = os.environ[env_key]
            logger.info(f"환경 변수 {env_key}에서 '{key}'를 '{config[key]}'(으)로 설정했습니다.")
    
    _config = config
    return config

def get_config() -> Dict[str, Any]:
    """
    구성 정보를 가져옵니다.
    
    Returns:
        Dict[str, Any]: 구성 정보
    """
    if _config is None:
        return load_config()
    return _config

def update_config(new_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    구성 정보를 업데이트하고 파일에 저장합니다.
    
    Args:
        new_config: 새 구성 정보
        
    Returns:
        Dict[str, Any]: 업데이트된 구성 정보
    """
    global _config
    
    if _config is None:
        _config = load_config()
    
    # 구성 업데이트
    _config.update(new_config)
    
    # 파일에 저장
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(_config, f, indent=2, ensure_ascii=False)
        logger.info(f"구성 파일 {CONFIG_FILE}에 업데이트된 설정을 저장했습니다.")
    except Exception as e:
        logger.error(f"구성 파일 저장 중 오류 발생: {str(e)}")
    
    return _config 