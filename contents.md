# Tello 드론 사용 가이드

## 맥에서 텔로 연결하는 법
1. Tello 드론의 전원을 켭니다.
2. Mac의 Wi-Fi 설정을 엽니다.
3. 사용 가능한 네트워크 목록에서 'TELLO-XXXXXX' 형식의 네트워크를 찾아 연결합니다.
4. 연결이 완료되면 터미널에서 다음 명령어로 연결을 테스트할 수 있습니다:
```python
from djitellopy import Tello
tello = Tello()
tello.connect()
print(tello.get_battery())  # 배터리 잔량 확인
```

## 윈도우에서 텔로 연결하는 법
1. Tello 드론의 전원을 켭니다.
2. Windows의 네트워크 설정을 엽니다.
3. Wi-Fi 네트워크 목록에서 'TELLO-XXXXXX'를 선택하여 연결합니다.
4. 연결이 완료되면 Python 스크립트로 연결을 테스트할 수 있습니다:
```python
from djitellopy import Tello
tello = Tello()
tello.connect()
print(tello.get_battery())  # 배터리 잔량 확인
```

## 기초 제어하기
### 1. 기본 비행 명령어
```python
from djitellopy import Tello
tello = Tello()
tello.connect()

# 이륙
tello.takeoff()

# 기본 이동
tello.move_forward(100)  # 앞으로 100cm 이동
tello.move_back(100)     # 뒤로 100cm 이동
tello.move_left(100)     # 왼쪽으로 100cm 이동
tello.move_right(100)    # 오른쪽으로 100cm 이동
tello.move_up(100)       # 위로 100cm 이동
tello.move_down(100)     # 아래로 100cm 이동

# 회전
tello.rotate_clockwise(90)           # 시계 방향으로 90도 회전
tello.rotate_counter_clockwise(90)   # 반시계 방향으로 90도 회전

# 착륙
tello.land()
```

### 2. 상태 확인
```python
# 배터리 잔량 확인
battery = tello.get_battery()
print(f"배터리 잔량: {battery}%")

# 높이 확인
height = tello.get_height()
print(f"현재 높이: {height}cm")

# 비행 시간 확인
flight_time = tello.get_flight_time()
print(f"비행 시간: {flight_time}초")
```

### 3. 카메라 제어
```python
# 비디오 스트림 시작
tello.streamon()

# 사진 촬영
frame = tello.get_frame_read().frame
cv2.imwrite("photo.jpg", frame)

# 비디오 스트림 종료
tello.streamoff()
```

### 4. 안전 주의사항
- 첫 비행 전 반드시 배터리 잔량을 확인하세요.
- 실내 비행 시 충분한 공간을 확보하세요.
- 비행 전 주변에 장애물이 없는지 확인하세요.
- 비상시를 대비해 `emergency()` 명령어를 숙지하세요.
- 초보자는 낮은 높이에서 연습하는 것을 추천합니다.

