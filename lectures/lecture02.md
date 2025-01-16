---
marp: true
theme: default
paginate: true
header: "드론 프로그래밍 기초 - 2차시"
footer: "AI 기반 드론 제어"
---

# AI 기반 드론 제어 기초
## 2차시 (3시간)

---

# 강의 개요

1. LLM Agent IDE 'Cursor' 활용법 (45분)
2. 음성 인식 기술 소개 (45분)
3. Voice Control 기초 실습 (45분)
4. AI 활용 드론 제어 예제 (45분)

---

# 1. LLM Agent IDE 'Cursor' 활용법

## Cursor IDE 소개
- VS Code 기반의 AI 강화 코드 에디터
- Claude 3.5 Sonnet 모델 통합
- 자연어 기반 코드 생성 및 편집
- 실시간 AI 페어 프로그래밍 지원

---

## Cursor IDE 설치 및 설정

### 1. 설치 방법
   - cursor.com 웹사이트에서 다운로드
   - macOS, Windows 지원
   
### 2. 초기 설정
   - 회원가입(구글, 깃헙)
   - API 키 설정 (Settings > AI > API Key)
   - 프로젝트 디렉토리 설정
   - Git 연동 설정

---

## Cursor IDE 설치 및 설정 (계속)

### 3. VS Code 설정 마이그레이션
   - 기존 VS Code 설정 자동 가져오기
   - 확장 프로그램 호환성 확인
   - 키보드 단축키 설정

---

## Cursor의 핵심 AI 기능

### 1. AI Chat (우측 패널)
   - 코드 관련 질문 및 답변
   - 컨텍스트 인식 코드 제안
   - 에러 디버깅 지원
   - 문서화 자동 생성

---

## Cursor의 핵심 AI 기능 (계속)

### 2. Composer (Cmd/Ctrl + I)
   - 자연어로 멀티 파일 생성
   - 프로젝트 구조 자동 생성
   - 보일러플레이트 코드 생성
   - 한 번에 여러 파일 수정

### 3. 인라인 편집 (Cmd/Ctrl + K)
   - 코드 블록 단위 AI 수정
   - 실시간 코드 개선 제안
   - 버그 수정 및 최적화
   - 타입 힌트 및 문서 추가

---

## 주요 단축키 및 명령어

| 기능 | Windows/Linux | macOS |
|------|--------------|-------|
| AI Chat | Ctrl + L | Cmd + L |
| Composer | Ctrl + I | Cmd + I |
| 인라인 편집 | Ctrl + K | Cmd + K |
| 파일 검색 | Ctrl + P | Cmd + P |
| 명령 팔레트 | Ctrl + Shift + P | Cmd + Shift + P |

---

## 고급 기능 활용

### 1. AI 코드 리뷰
   - PR 자동 분석
   - 코드 품질 개선 제안
   - 보안 취약점 탐지
   - 성능 최적화 제안

---

## 고급 기능 활용 (계속)

### 2. 멀티 파일 작업
   - 프로젝트 전체 리팩토링
   - 일관된 스타일 적용
   - 의존성 자동 관리
   - 테스트 코드 생성

### 3. 문서화 지원
   - README 자동 생성
   - API 문서 작성
   - 주석 자동 생성
   - 마크다운 미리보기

---

## Cursor IDE 주요 기능 요약
- 코드 자동 완성
- 자연어 코드 생성
- 코드 리팩토링
- 버그 찾기 및 수정
- 문서화 지원

---

# 2. 음성 인식 기술 소개

## 음성 인식의 기본 원리
- 음성 신호 처리
- 특징 추출
- 음성-텍스트 변환 (STT)
- 자연어 처리 (NLP)

---

## OpenAI Whisper 소개
- 고성능 음성 인식 모델
- 다국어 지원
- 실시간 처리 가능
- Python API 활용

---

## 음성 인식 시스템 구축 예시
```python
import whisper

# 모델 로드
model = whisper.load_model("base")

# 음성 파일에서 텍스트 추출
result = model.transcribe("audio.mp3")
print(result["text"])
```

---

# 3. Voice Control 기초 실습

## 음성 입력 시스템 구축
```python
import pyaudio
import wave

def record_audio(duration):
    # 오디오 녹음 설정
    frames = []
    stream = audio.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
    
    # 녹음 실행
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
```

---

## 음성 명령 처리 시스템
```python
def process_command(text):
    # 명령어 매핑
    commands = {
        "이륙": tello.takeoff,
        "착륙": tello.land,
        "앞으로": lambda: tello.move_forward(30),
        "뒤로": lambda: tello.move_back(30),
        "왼쪽": lambda: tello.move_left(30),
        "오른쪽": lambda: tello.move_right(30)
    }
    
    # 명령 실행
    if text in commands:
        commands[text]()
```

---

# 4. AI 활용 드론 제어 예제

## OpenAI Function Calling을 활용한 자연어 명령 처리

Function Calling은 자연어를 구조화된 함수 호출로 변환하는 기술입니다.

---

### 1. 함수 정의
```python
available_functions = {
    "takeoff": {
        "name": "takeoff",
        "description": "드론을 이륙시킵니다",
        "parameters": {}
    },
    "move": {
        "name": "move",
        "description": "드론을 지정된 방향으로 이동시킵니다",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down", "left", "right", "forward", "back"]
                },
                "distance": {
                    "type": "integer",
                    "description": "이동 거리 (cm)",
                    "minimum": 20,
                    "maximum": 500
                }
            },
            "required": ["direction", "distance"]
        }
    }
}
```

---

### 2. 음성 명령 처리
```python
def process_voice_command(audio_text: str) -> Dict:
    system_prompt = """
    당신은 드론 제어 시스템입니다. 사용자의 자연어 명령을 드론 제어 명령으로 변환합니다.
    
    예시:
    - "위로 1미터 올라가줘" -> move(direction="up", distance=100)
    - "앞으로 30센티미터" -> move(direction="forward", distance=30)
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": audio_text}
        ],
        tools=[{
            "type": "function",
            "function": {
                "name": "control_drone",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "enum": ["takeoff", "move"]},
                        "parameters": {"type": "object"}
                    }
                }
            }
        }],
        tool_choice={"type": "function", "function": {"name": "control_drone"}}
    )

    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)
```

---

## 음성 제어 시스템 구현

### 1. 음성 인식 설정
```python
def setup_voice_recognition():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        # 주변 소음 조정
        recognizer.adjust_for_ambient_noise(source)
        print("음성 인식 준비 완료")
    return recognizer
```

---

### 2. 메인 제어 루프
```python
def main():
    controller = TelloController()
    recognizer = setup_voice_recognition()
    
    try:
        controller.connect()
        
        while True:
            print("\n명령을 말씀해주세요...")
            
            # 음성 입력 받기
            text = recognize_speech(recognizer)
            if "종료" in text:
                break
                
            # 명령 처리 및 실행
            command = process_voice_command(text)
            controller.execute_function(
                command["command"], 
                command.get("parameters")
            )
            
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        controller.execute_function("land")
```

---

## 안전 기능 구현

### 1. 배터리 모니터링
```python
def check_battery():
    battery = tello.get_battery()
    if battery < 20:
        print(f"경고: 배터리 부족 ({battery}%)")
        return False
    return True
```

---

### 2. 비상 착륙 처리
```python
def emergency_land():
    try:
        print("비상 착륙 시도 중...")
        tello.land()
    except:
        print("강제 종료")
        tello.emergency()
```

---

# 실습 과제

1. Cursor IDE를 활용한 코드 생성
2. 기본 음성 인식 시스템 구현
3. 드론 음성 제어 프로그램 작성

---


## Cursor IDE 실습 (1/4) - 기본 코드 생성

자연어로 코드 생성하기:

## OpenAI를 활용한 자연어 명령 처리

```python
def process_voice_command(audio_text: str) -> Dict:
    system_prompt = """
    당신은 드론 제어 시스템입니다. 사용자의 자연어 명령을 드론 제어 명령으로 변환합니다.
    
    가능한 명령어:
    1. 이륙 (takeoff)
    2. 이동 (move) - 방향: up, down, left, right, forward, back
    """
```

---

## 툴 정의하기

```python
    tools = [{
        "type": "function",
        "function": {
            "name": "control_drone",
            "description": "음성 명령을 드론 제어 명령으로 변환",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["takeoff", "move"]
                    },
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "direction": {
                                "type": "string",
                                "enum": ["up", "down", "left", "right", "forward", "back"]
                            },
                            "distance": {
                                "type": "integer",
                                "description": "이동 거리 (cm)"
                            }
                        }
                    }
                },
                "required": ["command"]
            }
        }
    }]
```

---
## 연결하기
```python
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": audio_text}
        ],
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "control_drone"}}
    )

    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments)
```

---

## 음성 명령 실행 예시

```python
# 메인 실행 루프
while True:
    # 음성 입력 받기
    text = recognize_speech()
    
    # GPT를 통한 명령 해석
    command = process_voice_command(text)
    
    # 드론 제어 실행
    controller.execute_function(
        command["command"], 
        command.get("parameters")
    )
```

---

## Cursor IDE 실습 (1/4) - 기본 코드 생성

자연어로 코드 생성하기:
```python
# 프롬프트: "드론을 제어하는 기본 클래스를 만들어줘"
class DroneController:
    def __init__(self):
        self.tello = Tello()
        self.connected = False
        
    def connect(self):
        try:
            self.tello.connect()
            self.connected = True
            print("드론 연결 성공!")
        except Exception as e:
            print(f"연결 실패: {e}")
            
    def check_status(self):
        if not self.connected:
            return False
        battery = self.tello.get_battery()
        temp = self.tello.get_temperature()
        return {"battery": battery, "temperature": temp}
```

---

## Cursor IDE 실습 (2/4) - 코드 리팩토링

기존 코드를 AI로 개선하기:
```python
# 프롬프트: "에러 처리와 로깅을 추가해줘"
class DroneController:
    def __init__(self):
        self.tello = Tello()
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
    def connect(self):
        try:
            self.tello.connect()
            self.connected = True
            self.logger.info("드론 연결 성공!")
        except Exception as e:
            self.logger.error(f"연결 실패: {str(e)}")
            raise DroneConnectionError(f"드론 연결 실패: {str(e)}")
            
    def check_status(self):
        if not self.connected:
            self.logger.warning("드론이 연결되어 있지 않습니다.")
            return None
        try:
            status = {
                "battery": self.tello.get_battery(),
                "temperature": self.tello.get_temperature(),
                "flight_time": self.tello.get_flight_time()
            }
            self.logger.debug(f"드론 상태: {status}")
            return status
        except Exception as e:
            self.logger.error(f"상태 확인 실패: {str(e)}")
            return None
```

---

## Cursor IDE 실습 (3/4) - 문서화 자동 생성

AI를 활용한 문서 생성:
```python
"""DroneController 클래스는 Tello 드론의 기본 제어 기능을 제공합니다.

이 클래스는 다음과 같은 주요 기능을 제공합니다:
1. 드론 연결 및 상태 관리
2. 에러 처리 및 로깅
3. 실시간 상태 모니터링

사용 예시:
    controller = DroneController()
    controller.connect()
    status = controller.check_status()
    if status and status['battery'] > 20:
        print(f"배터리 잔량: {status['battery']}%")

Attributes:
    tello (Tello): DJI Tello 드론 객체
    connected (bool): 드론 연결 상태
    logger (Logger): 로깅을 위한 logger 객체
"""

class DroneController:
    # ...생략...
```

---

## Cursor IDE 실습 (4/4) - 테스트 코드 생성

AI를 활용한 테스트 케이스 작성:
```python
import unittest
from unittest.mock import Mock, patch

class TestDroneController(unittest.TestCase):
    def setUp(self):
        self.controller = DroneController()
        
    @patch('djitellopy.Tello')
    def test_connection_success(self, mock_tello):
        # 성공적인 연결 테스트
        self.controller.connect()
        self.assertTrue(self.controller.connected)
        
    @patch('djitellopy.Tello')
    def test_connection_failure(self, mock_tello):
        # 연결 실패 테스트
        mock_tello.connect.side_effect = Exception("Connection failed")
        with self.assertRaises(DroneConnectionError):
            self.controller.connect()
            
    def test_status_check_not_connected(self):
        # 연결되지 않은 상태에서의 상태 체크
        status = self.controller.check_status()
        self.assertIsNone(status)

if __name__ == '__main__':
    unittest.main()
```

---