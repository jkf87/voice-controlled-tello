---
marp: true
theme: default
paginate: true
header: "드론 프로그래밍 기초 - 3차시"
footer: "AI 융합 프로젝트"
---

# AI 융합 프로젝트
## 3차시 (3시간)

---

# 강의 개요

1. 객체 인식(Object Detection) 실습 (45분)
2. 음성 명령 기반 드론 제어 구현 (45분)
3. AI 기술 융합 미니 프로젝트 수행 (45분)
4. 결과물 시연 및 발표 (45분)

---

# 1. 객체 인식(Object Detection) 실습

## OpenCV와 객체 인식
- OpenCV 기본 개념
- 이미지 처리 기초
- 객체 검출 알고리즘
- 실시간 비디오 처리

---

## YOLO 모델 활용
```python
import cv2
import numpy as np
from ultralytics import YOLO

# YOLO 모델 로드
model = YOLO('yolov8n.pt')

# 드론 카메라에서 프레임 받기
frame = tello.get_frame_read().frame

# 객체 감지
results = model(frame)

# 결과 시각화
annotated_frame = results[0].plot()
cv2.imshow("Object Detection", annotated_frame)
```

---

## 객체 추적 시스템 구현
```python
def track_object(frame, target_class="person"):
    # 객체 감지
    results = model(frame)
    
    # 대상 객체 찾기
    for r in results:
        boxes = r.boxes
        for box in boxes:
            # 클래스가 일치하는 경우
            if model.names[int(box.cls)] == target_class:
                return box.xyxy[0]  # 박스 좌표 반환
    
    return None
```

---

# 2. 음성 명령 기반 드론 제어 구현

## 통합 제어 시스템
```python
def process_voice_command(command, detected_objects):
    if "추적" in command:
        if "사람" in command:
            track_target("person")
        elif "자동차" in command:
            track_target("car")
    elif "촬영" in command:
        start_recording()
    elif "중지" in command:
        stop_tracking()
```

---

## 자동 추적 비행
```python
def track_target(target_class):
    while tracking_enabled:
        # 프레임 획득
        frame = tello.get_frame_read().frame
        
        # 객체 위치 파악
        target_pos = track_object(frame, target_class)
        
        if target_pos is not None:
            # 드론 제어
            adjust_position(target_pos)
        else:
            # 대상을 찾을 수 없는 경우
            search_pattern()
```

---

# 3. AI 기술 융합 미니 프로젝트 수행

## 프로젝트 주제 예시
1. 음성 명령 기반 자동 촬영 시스템
2. 객체 추적 및 기록 시스템
3. 안전 감시 드론 시스템
4. 실시간 상황 보고 시스템

---

## 프로젝트 구현 가이드
1. 요구사항 분석
2. 시스템 설계
3. 구현 및 테스트
4. 문제점 개선
5. 발표 자료 준비

---

## 프로젝트 구조 예시
```python
class AIControlledDrone:
    def __init__(self):
        self.tello = Tello()
        self.voice_controller = VoiceController()
        self.object_detector = ObjectDetector()
        self.recorder = VideoRecorder()
    
    def run(self):
        while True:
            command = self.voice_controller.get_command()
            objects = self.object_detector.detect()
            self.process_command(command, objects)
```

---

# 4. 결과물 시연 및 발표

## 발표 준비
- 프로젝트 소개
- 기술 스택 설명
- 주요 기능 시연
- 개발 과정 공유
- Q&A

---

## 시연 체크리스트
1. 드론 배터리 확인
2. WiFi 연결 상태 점검
3. 안전 구역 확보
4. 백업 코드 준비
5. 비상 착륙 절차 숙지

---

## 발표 평가 기준
- 기술적 완성도
- 창의성
- 실용성
- 발표 능력
- 질문 대응

---

# 과정 마무리

## 학습 내용 정리
1. 드론 기초 및 프로그래밍
2. AI 기반 제어 시스템
3. 실전 프로젝트 수행

---

## 향후 발전 방향
- 고급 AI 모델 활용
- 다중 드론 제어
- 실제 현장 적용
- 새로운 응용 분야 개척 