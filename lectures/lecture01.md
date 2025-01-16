---
marp: false
theme: default
paginate: true
header: "드론 프로그래밍 기초 - 1일차"
footer: "Tello 드론 프로그래밍 with Python"
---

# 드론 기초 및 프로그래밍 입문
## 1차시 (3시간)

---

# 강의 개요

1. 드론의 기본 원리와 구조 
2. Tello 드론 기본 조작법 
3. 파이썬 SDK 소개 및 기본 제어 실습 
4. 모터 제어 프로그래밍 

---

# 1. 드론의 기본 원리와 구조

## 드론이란?
- 무인 항공기(UAV: Unmanned Aerial Vehicle)
- 조종사 없이 원격으로 조종되는 비행체
- 다양한 분야에서 활용 (촬영, 배송, 측량 등)

---

## 드론의 기본 구조
- 프레임: 드론의 기본 골격
- 모터와 프로펠러: 비행을 위한 추진력 제공
- 비행 제어 장치(FC): 드론의 '두뇌' 역할
- 배터리: 전원 공급
- 센서: 자이로스코프, 가속도계 등

---

## 드론의 비행 원리
- 쿼드콥터의 기본 움직임
  - 상승/하강 (Throttle)
  - 전진/후진 (Pitch)
  - 좌/우 이동 (Roll)
  - 좌/우 회전 (Yaw)

---

# 2. Tello 드론 기본 조작법

## Tello 드론 소개
- DJI와 Ryze Tech이 공동 개발
- 교육용 프로그래밍 드론
- 내장 카메라와 비전 포지셔닝 시스템
- WiFi를 통한 통신

---

## Tello 드론 기본 조작
- 전원 켜기/끄기
- WiFi 연결 방법
- 기본 비행 조작
- 안전 수칙과 주의사항

---

# 3. 파이썬 SDK 소개 및 기본 제어 실습

## DJITelloPy 소개
- 파이썬 기반 Tello 드론 제어 라이브러리
- 설치 방법
```python
pip install djitellopy
```

---

## 기본 연결 및 테스트
```python
from djitellopy import Tello

# 드론 객체 생성
tello = Tello()

# 드론 연결
tello.connect()

# 배터리 확인
print(f"배터리 잔량: {tello.get_battery()}%")
```

---

## 기본 비행 명령어
```python
# 이륙
tello.takeoff()

# 전진 30cm
tello.move_forward(30)

# 좌회전 90도
tello.rotate_counter_clockwise(90)

# 착륙
tello.land()
```

---

# 4. 모터 제어 프로그래밍

## 모터 제어 기초
- RC(Remote Control) 값 이해
- 각 채널의 역할
  - left_x: 좌우 이동
  - left_y: 상승/하강
  - right_x: 좌우 회전
  - right_y: 전진/후진

---

## RC 제어 예제
```python
# RC 값 설정 (-100 ~ 100)
tello.send_rc_control(left_right, forward_backward, up_down, yaw)

# 예: 전진 50% 속도
tello.send_rc_control(0, 50, 0, 0)
```

---

# 실습 과제

1. 드론 연결 및 기본 상태 확인
2. 간단한 비행 시퀀스 프로그래밍
3. RC 제어를 활용한 8자 비행

---

# 다음 차시 예고

- LLM Agent IDE 'Cursor' 활용
- 음성 인식 기술 소개
- Voice Control 기초 실습 