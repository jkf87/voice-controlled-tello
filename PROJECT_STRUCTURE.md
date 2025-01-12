# DJITelloPy 프로젝트 구조

## 디렉토리 구조

```
DJITelloPy/
├── djitellopy/                # 메인 소스 코드
│   ├── __init__.py           # 패키지 초기화
│   ├── enforce_types.py      # 타입 체크 유틸리티
│   ├── swarm.py              # 드론 군집 제어
│   └── tello.py              # 핵심 Tello 드론 제어 클래스
│
├── examples/                  # 예제 코드
│   ├── record-video.py       # 비디오 녹화 예제
│   ├── simple-swarm.py       # 간단한 군집 제어 예제
│   ├── simple.py             # 기본 제어 예제
│   ├── take-picture.py       # 사진 촬영 예제
│   ├── manual-control-opencv.py  # OpenCV 기반 수동 제어
│   ├── manual-control-pygame.py  # Pygame 기반 수동 제어
│   ├── mission-pads.py       # 미션 패드 활용 예제
│   └── panorama/             # 파노라마 관련 예제
│
├── docs/                      # 문서
├── requirements.txt           # 프로젝트 의존성
├── setup.py                  # 패키지 설치 설정
└── README.md                 # 프로젝트 설명서
```

## 주요 구성 요소 설명

### 1. 코어 라이브러리 (`djitellopy/`)
- **tello.py**: Tello 드론의 모든 기본 기능을 구현한 메인 클래스입니다. 비행 제어, 카메라 제어, 상태 모니터링 등의 기능을 포함합니다.
- **swarm.py**: 여러 대의 Tello 드론을 동시에 제어하기 위한 기능을 제공합니다.
- **enforce_types.py**: 함수 파라미터와 반환값의 타입 검사를 위한 유틸리티 기능을 제공합니다.

### 2. 예제 코드 (`examples/`)
- 기본적인 드론 제어 예제
- 비디오 녹화 및 사진 촬영 예제
- OpenCV와 Pygame을 활용한 수동 제어 인터페이스
- 드론 군집 제어 예제
- 미션 패드를 활용한 고급 제어 예제
- 파노라마 촬영 관련 예제

### 3. 문서화 및 설정 파일
- **docs/**: 프로젝트의 상세 문서
- **requirements.txt**: 프로젝트 실행에 필요한 Python 패키지 목록
- **setup.py**: 패키지 설치 및 배포를 위한 설정
- **README.md**: 프로젝트 소개 및 사용 방법 (영문)
- **README_CN.md**: 프로젝트 소개 및 사용 방법 (중문) 