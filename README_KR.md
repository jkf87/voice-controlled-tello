# DJITelloPy
## [English](README.md) | [中文](README_CN.md)

DJI Tello 드론을 위한 파이썬 인터페이스로, 공식 [Tello SDK](https://dl-cdn.ryzerobotics.com/downloads/tello/20180910/Tello%20SDK%20Documentation%20EN_1.3.pdf)와 [Tello EDU SDK](https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf)를 기반으로 합니다. 

## 주요 기능
- 모든 Tello 명령어 구현
- 간편한 비디오 스트림 수신
- 드론 상태 패킷 수신 및 파싱
- 드론 군집 제어 지원
- Python 3.6 이상 지원

## pip를 이용한 설치
```
pip install djitellopy
```

Linux 배포판에서 Python2와 Python3가 모두 설치된 경우 (예: Debian, Ubuntu 등):
```
pip3 install djitellopy
```

## 개발자 모드로 설치
아래 명령어를 사용하여 저장소를 _수정 가능한_ 방식으로 설치할 수 있습니다. 이를 통해 라이브러리를 수정하고 수정된 버전을 일반 설치처럼 사용할 수 있습니다.

```
git clone https://github.com/damiafuentes/DJITelloPy.git
cd DJITelloPy
pip install -e .
```

## 사용법
### API 참조
모든 클래스와 메서드에 대한 전체 참조는 [djitellopy.readthedocs.io](https://djitellopy.readthedocs.io/en/latest/)에서 확인할 수 있습니다.

### 간단한 예제
```python
from djitellopy import Tello

tello = Tello()

tello.connect()
tello.takeoff()

tello.move_left(100)
tello.rotate_counter_clockwise(90)
tello.move_forward(100)

tello.land()
```

### 추가 예제
[examples](examples/) 디렉토리에서 다음과 같은 예제 코드를 확인할 수 있습니다:

- [사진 촬영](examples/take-picture.py)
- [비디오 녹화](examples/record-video.py)
- [드론 군집 비행](examples/simple-swarm.py)
- [키보드를 이용한 기본 제어](examples/manual-control-opencv.py)
- [미션 패드 감지](examples/mission-pads.py)
- [Pygame을 이용한 고급 수동 제어](examples/manual-control-pygame.py)

### 주의사항
- `streamon` 명령에 대해 `Unknown command` 응답이 나오면 Tello 펌웨어를 업데이트해야 합니다. Tello 앱을 통해 업데이트할 수 있습니다.
- 미션 패드 감지 및 내비게이션은 Tello EDU에서만 지원됩니다.
- 미션 패드를 성공적으로 사용하기 위해서는 밝은 환경이 필요합니다.
- 기존 WiFi 네트워크 연결은 Tello EDU에서만 지원됩니다.
- 기존 WiFi 네트워크에 연결된 경우 비디오 스트리밍을 사용할 수 없습니다.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE.txt](LICENSE.txt) 파일을 참조하세요.

## 기여

프로젝트에 기여하고 싶으시다면 언제든 환영합니다! Pull Request를 보내주세요. 