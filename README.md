# Voice-Controlled Tello Drone

DJI Tello 드론을 한국어 음성 명령으로 제어하는 프로젝트입니다.

## 기능

- 음성 인식을 통한 드론 제어
- OpenAI GPT를 활용한 자연어 명령 처리
- 기본적인 드론 조작 (이륙, 착륙, 이동, 회전)

## 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/jkf87/voice-controlled-tello.git
cd voice-controlled-tello
```

2. 가상환경 생성 및 활성화
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

3. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

4. OpenAI API 키 설정
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## 사용 방법

1. Tello 드론의 전원을 켜고 WiFi 연결
2. 프로그램 실행
```bash
python voice_controlled_tello.py
```

3. 음성 명령 예시
- "이륙해"
- "1미터 위로 올라가"
- "왼쪽으로 90도 회전해"
- "착륙해"

## 주의사항

- 실내에서 사용할 경우 충분한 공간을 확보하세요
- 배터리 잔량을 항상 확인하세요
- 비상시를 대비해 수동 제어 방법을 숙지하세요

## 라이선스

MIT License
