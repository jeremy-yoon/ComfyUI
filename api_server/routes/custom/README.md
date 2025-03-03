# ComfyUI 워크플로우 API

ComfyUI 워크플로우 API는 일반 ComfyUI 워크플로우를 API 워크플로우로 변환하고 실행하는 기능을 제공합니다.

## 워크플로우 변환 API

### 워크플로우 변환하기

**엔드포인트:** `POST /api/workflow/convert`

일반 ComfyUI 워크플로우 JSON 파일을 API 워크플로우 형식으로 변환합니다.

**요청 본문:**
```json
{
  "workflow_name": "my_workflow.json",
  "output_name": "my_workflow_api.json",
  "use_dynamic_loading": true
}
```

**파라미터:**
- `workflow_name` (필수): 변환할 워크플로우 JSON 파일명
- `output_name` (선택): 변환된 API 워크플로우를 저장할 파일명
- `use_dynamic_loading` (선택): ComfyUI 노드 정의를 동적으로 로드할지 여부 (기본값: true)

**응답:**
```json
{
  "status": "success",
  "message": "워크플로우 변환 완료",
  "api_workflow": { /* 변환된 API 워크플로우 JSON */ },
  "output_path": "/path/to/ComfyUI/user/default/workflows/my_workflow_api.json"
}
```

### 워크플로우 실행하기

**엔드포인트:** `POST /api/workflow/execute`

일반 ComfyUI 워크플로우 JSON 파일을 API 워크플로우로 변환하고 실행합니다.

**요청 본문:**
```json
{
  "workflow_name": "my_workflow.json",
  "extra_data": {
    "6": {
      "text": "새로운 프롬프트 텍스트"
    }
  },
  "use_dynamic_loading": true
}
```

**파라미터:**
- `workflow_name` (필수): 실행할 워크플로우 JSON 파일명
- `extra_data` (선택): 워크플로우에 전달할 추가 데이터 (노드 ID -> 입력 값 매핑)
- `use_dynamic_loading` (선택): ComfyUI 노드 정의를 동적으로 로드할지 여부 (기본값: true)

**응답:**
```json
{
  "status": "success",
  "message": "워크플로우 실행 요청 완료",
  "prompt_id": "42"
}
```

### 워크플로우 목록 조회하기

**엔드포인트:** `GET /api/workflow/list`

사용 가능한 워크플로우 파일 목록을 조회합니다.

**응답:**
```json
{
  "status": "success",
  "workflows": [
    {
      "name": "my_workflow.json",
      "size": 12345,
      "modified": 1678901234.5678
    },
    {
      "name": "my_workflow_api.json",
      "size": 6789,
      "modified": 1678901234.5678
    }
  ],
  "directory": "/path/to/ComfyUI/user/default/workflows"
}
```

### 워크플로우 조회하기

**엔드포인트:** `GET /api/workflow/{workflow_name}`

특정 워크플로우 파일의 내용을 조회합니다.

**파라미터:**
- `workflow_name`: 조회할 워크플로우 JSON 파일명

**응답:**
```json
{
  "status": "success",
  "workflow": { /* 워크플로우 JSON 내용 */ }
}
```

## 사용 예시

### 워크플로우 변환 및 실행

```python
import requests
import json

# API 엔드포인트
base_url = "http://localhost:8188"

# 워크플로우 변환
convert_response = requests.post(
    f"{base_url}/api/workflow/convert",
    json={
        "workflow_name": "이미지 생성.json",
        "output_name": "이미지 생성api.json"
    }
)
print(convert_response.json())

# 워크플로우 실행
execute_response = requests.post(
    f"{base_url}/api/workflow/execute",
    json={
        "workflow_name": "이미지 생성.json",
        "extra_data": {
            "6": {
                "text": "beautiful scenery nature glass bottle landscape, purple galaxy bottle, high quality"
            },
            "7": {
                "text": "text, watermark, low quality"
            }
        }
    }
)
print(execute_response.json())
```

## 참고 사항

- 워크플로우 파일은 `ComfyUI/user/default/workflows` 디렉토리에 저장됩니다.
- 해당 디렉토리가 없는 경우 자동으로 생성됩니다.
- 워크플로우 ID는 프롬프트 ID로 반환되며, 기존 ComfyUI API를 통해 상태를 조회할 수 있습니다.
- `extra_data`를 통해 노드의 입력 값을 동적으로 변경할 수 있습니다. 