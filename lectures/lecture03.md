---
marp: true
theme: default
paginate: true
header: "드론 프로그래밍 기초 - 3차시"
footer: "AI 융합 프로젝트"
---

# AI 융합 프로젝트
## 3차시 (3시간)
### 웹 인터페이스와 AI 통합

---

# 강의 개요

1. 웹 기반 드론 제어 시스템 (45분)
2. AI 기술 통합 (45분)
3. 실시간 영상 처리와 분석 (45분)
4. 미니 프로젝트 실습 (45분)

---

# 1. 웹 기반 드론 제어 시스템

## Flask 웹 프레임워크
- Flask 소개 및 기본 구조
- 라우팅과 뷰 함수
- 템플릿 시스템
- 정적 파일 처리

---

## 필수 라이브러리
```python
from flask import Flask, render_template, Response, jsonify
import cv2
import threading
from queue import Queue
from djitellopy import Tello
```

---

## 웹 서버 구성
- 서버 초기화
- 라우트 설정
- 비디오 스트리밍
- API 엔드포인트

---

## 비디오 스트리밍 구현
```python
def get_frame():
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + 
                   frame_bytes + b'\r\n')
```

---

## 프론트엔드 인터페이스
- HTML 템플릿 구조
- CSS 스타일링
- JavaScript 이벤트 처리
- 실시간 업데이트

---

## RESTful API 설계
- 드론 연결 API
- 비행 제어 API
- 상태 모니터링 API
- 에러 처리

---

# 2. AI 기술 통합

## OpenAI GPT 통합
- API 설정
- 프롬프트 엔지니어링
- 응답 처리
- 에러 핸들링

---

## 이미지 분석 시스템
```python
def analyze_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(
            image_file.read()
        ).decode('utf-8')
        
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", 
                     "text": "이미지 분석을 해주세요"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    )
```

---

## 음성 변환 시스템
- gTTS 라이브러리 활용
- 텍스트 음성 변환
- 오디오 재생
- 에러 처리

---

## 멀티스레딩 처리
- 스레드 안전성
- 큐 시스템
- 리소스 관리
- 동기화 처리

---

# 3. 실시간 영상 처리와 분석

## 영상 스트리밍 최적화
- 프레임 처리
- 버퍼 관리
- 메모리 최적화
- 성능 모니터링

---

## 파노라마 촬영 시스템
```python
def create_panorama():
    images = []
    for i in range(4):
        frame = get_frame()
        images.append(frame)
        rotate_clockwise(90)
        time.sleep(2)
    
    stitcher = cv2.Stitcher.create()
    status, panorama = stitcher.stitch(images)
```

---

## 이미지 처리 파이프라인
- 프레임 캡처
- 이미지 전처리
- AI 분석
- 결과 시각화

---

## 실시간 모니터링 시스템
- 상태 모니터링
- 로그 기록
- 알림 시스템
- 대시보드

---

# 4. 미니 프로젝트 실습

## 프로젝트 주제
1. AI 기반 드론 관제 시스템
2. 실시간 환경 모니터링
3. 자동 순찰 시스템
4. 스마트 촬영 시스템

---

## 시스템 아키텍처
```python
class DroneController:
    def __init__(self):
        self.tello = Tello()
        self.frame_reader = None
        self.is_streaming = False
        self.frame_queue = Queue(maxsize=10)
        self.stream_thread = None
```

---

## 구현 가이드라인
1. 모듈화 설계
2. 에러 처리
3. 성능 최적화
4. 사용자 경험

---

## 테스트 및 디버깅
- 단위 테스트
- 통합 테스트
- 성능 테스트
- 사용성 테스트

---

# 실전 응용

## 산업 현장 활용
- 시설물 점검
- 재고 관리
- 보안 감시
- 환경 모니터링

---

## 안전 고려사항
- 비행 구역 확인
- 배터리 관리
- 비상 착륙 절차
- 네트워크 보안

---

## 향후 발전 방향
- 고급 AI 모델 통합
- 클라우드 연동
- 실시간 분석 강화
- 자동화 시스템 개선

---

# 과제 및 평가

## 프로젝트 과제
- 웹 인터페이스 개선
- AI 기능 추가
- 새로운 기능 구현
- 문서화

---

## 평가 기준
1. 기술 구현도 (40%)
2. 창의성 (20%)
3. 완성도 (20%)
4. 발표 능력 (20%)

---

# 참고 자료

## 문서 및 API
- Flask 공식 문서
- DJITelloPy 문서
- OpenAI API 문서
- OpenCV 튜토리얼

---

## 추천 도서
- 파이썬 웹 프로그래밍
- 실전 OpenCV
- 드론 프로그래밍 입문
- AI 시스템 설계

---

# Q&A 및 마무리

## 주요 질문 사항
- 성능 최적화 방법
- 에러 처리 전략
- 확장성 고려사항
- 보안 관련 주의점 