# ComfyUI Custom API 문서

## 의류 생성 API

### 1. 의류 이미지 생성 v2

AI를 사용하여 의류 이미지를 생성합니다.

```
POST /api/custom/generate_clothes_v2
```

**Request Body**
```json
{
  "image": "Frame 84.png",
  "image2": "Frame 93.png",
  "mask": "Frame 82.png",
  "prompt": "pixel art, round plush, melting plush, plush wearing pajama...",
  "negative_prompt": "hand, arm, foot, (outline:1.4), particles",
  "seed": 12345
}
```

**Parameters**
- `image` (선택, 기본값: "Frame 84.png"): 기본 이미지 파일명
- `image2` (선택, 기본값: "Frame 93.png"): 두 번째 이미지 파일명
- `mask` (선택, 기본값: "Frame 82.png"): 마스크 이미지 파일명
- `prompt` (선택): 이미지 생성을 위한 프롬프트 텍스트
- `negative_prompt` (선택): 이미지 생성 시 제외할 요소를 지정하는 프롬프트
- `seed` (선택): 이미지 생성을 위한 시드값 (미지정시 랜덤 생성)

**Response**
```json
{
  "status": "success",
  "message": "Clothes image generation queued",
  "prompt_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Status Codes**
- 200: 성공
- 400: 잘못된 요청

## 이미지 처리 API

### 1. 오브젝트 추출

마스크 영역을 기반으로 두 이미지 간의 유사한 픽셀을 찾아 제거합니다.

```
POST /api/custom/extract-object
```

**Request Body**
- Content-Type: `multipart/form-data`
- Form Fields:
  - `image`: 처리할 대상 이미지 파일 (PNG 형식)

**고정 경로**
- 비교 이미지: `input/utils/comparison_image.png`
- 마스크 이미지: `input/utils/mask_image.png`

**Response**
```json
{
  "status": "success",
  "result_path": "extracted_objects/20240321_143022/extracted_result.png"
}
```

**주의사항**
- 마스크 이미지는 반드시 알파 채널이 포함된 PNG 파일이어야 합니다.
- 마스크의 투명한 부분(알파=0)이 처리할 영역으로 인식됩니다.
- 처리 결과는 input 디렉토리 아래 `extracted_objects` 폴더에 저장됩니다.
- 결과 파일명은 타임스탬프 폴더 아래 `extracted_result.png`로 저장됩니다.

**Status Codes**
- 200: 성공
- 400: 잘못된 요청 (이미지 파일 누락)
- 500: 처리 중 오류 발생

## 파일 시스템 API

### 1. 파일/폴더 목록 조회

파일과 폴더의 목록을 조회합니다.

```
GET /api/custom/files
```

**Query Parameters**
- `type` (선택, 기본값: "input"): 디렉토리 타입
- `subfolder` (선택): 하위 폴더 경로

**Response**
```json
[
  {
    "name": "image.png",
    "type": "file",
    "size": 1234567,
    "path": "subfolder/image.png"
  },
  {
    "name": "folder1",
    "type": "directory",
    "size": null,
    "path": "subfolder/folder1"
  }
]
```

**Status Codes**
- 200: 성공
- 400: 잘못된 타입
- 403: 접근 거부
- 404: 폴더를 찾을 수 없음

### 2. 파일 다운로드

특정 파일을 다운로드합니다.

```
GET /api/custom/files/download
```

**Query Parameters**
- `type` (선택, 기본값: "input"): 디렉토리 타입
- `path` (필수): 파일 경로

**Response**
- 파일 데이터와 적절한 Content-Type 헤더

**Status Codes**
- 200: 성공
- 400: 잘못된 요청 (경로 누락 등)
- 403: 접근 거부
- 404: 파일을 찾을 수 없음

### 3. 파일 업로드

파일을 업로드합니다.

```
POST /api/custom/files/upload
```

**Form Data**
- `file` (필수): 업로드할 파일
- `type` (선택, 기본값: "input"): 디렉토리 타입
- `path` (필수): 저장할 파일 경로

**Status Codes**
- 201: 생성 성공
- 400: 잘못된 요청 (파일 누락 등)
- 403: 접근 거부

### 4. 파일/폴더 삭제

파일이나 폴더를 삭제합니다.

```
DELETE /api/custom/files
```

**Query Parameters**
- `type` (선택, 기본값: "input"): 디렉토리 타입
- `path` (필수): 삭제할 파일/폴더 경로

**Status Codes**
- 200: 삭제 성공
- 400: 잘못된 요청 (경로 누락 등)
- 403: 접근 거부
- 404: 파일/폴더를 찾을 수 없음

### 5. 폴더 생성

새 폴더를 생성합니다.

```
POST /api/custom/files/directory
```

**Query Parameters**
- `type` (선택, 기본값: "input"): 디렉토리 타입
- `path` (필수): 생성할 폴더 경로

**Status Codes**
- 201: 생성 성공
- 400: 잘못된 요청 (경로 누락 또는 이미 존재)
- 403: 접근 거부

## 히스토리 API

### 1. 프롬프트 히스토리 조회

특정 프롬프트의 히스토리를 조회합니다.

```
GET /api/custom/history/{prompt_id}
```

**Path Parameters**
- `prompt_id` (필수): 조회할 프롬프트 ID

**Response**
- 해당 프롬프트의 히스토리 데이터

**Status Codes**
- 200: 성공
- 400: 잘못된 요청 (프롬프트 ID 누락)

## 워크플로우 API

### 워크플로우를 API 형식으로 변환

**엔드포인트**: `POST /api/custom/convert_to_api_workflow`

**설명**: 표준 ComfyUI 워크플로우 JSON을 API 형식으로 변환합니다. 이 API 형식은 ComfyUI API를 통해 워크플로우를 실행하는 데 사용할 수 있습니다.

**요청 본문**:
```json
{
  "workflow": {
    "nodes": [...],
    "links": [...],
    ...
  }
}
```

**응답**:
```json
{
  "status": "success",
  "api_workflow": {
    "1": {
      "class_type": "노드타입",
      "inputs": {
        "param1": 값,
        "param2": [노드ID, 출력인덱스]
      }
    },
    "2": { ... }
  }
}
```

**오류 응답**:
```json
{
  "status": "error",
  "message": "오류 메시지"
}
```

**예제 요청**:
```bash
curl -X POST http://localhost:8188/api/custom/convert_to_api_workflow \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": {
      "nodes": [
        {
          "id": 1,
          "type": "CheckpointLoaderSimple",
          "widgets_values": ["v1-5-pruned-emaonly.safetensors"]
        },
        {
          "id": 2,
          "type": "CLIPTextEncode",
          "inputs": {
            "clip": {"link": 1, "slot": 1},
            "text": "a beautiful landscape"
          }
        }
      ],
      "links": [
        {"source": 1, "source_slot": 1, "target": 2, "target_slot": 0}
      ]
    }
  }'
```

**예제 응답**:
```json
{
  "status": "success",
  "api_workflow": {
    "1": {
      "class_type": "CheckpointLoaderSimple",
      "inputs": {
        "ckpt_name": "v1-5-pruned-emaonly.safetensors"
      }
    },
    "2": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "clip": ["1", 1],
        "text": "a beautiful landscape"
      }
    }
  }
}
```

## 공통 사항

### 에러 응답 형식
```json
{
  "text": "에러 메시지"
}
```

### 보안
- 모든 파일 시스템 관련 API는 기본 디렉토리 외부로의 접근을 차단합니다.
- 특정 파일 타입(.html, .js, .css 등)은 보안상의 이유로 다운로드 형식으로 제공됩니다.

### 타입(type) 파라미터
- `input`: 입력 파일 디렉토리 (기본값)
- 기타 ComfyUI에서 지원하는 디렉토리 타입