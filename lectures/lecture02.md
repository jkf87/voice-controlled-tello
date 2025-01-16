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

1. AI 기반 드론 제어 시스템 구조 (45분)
2. 음성 인식과 AI 통합 (45분)
3. 드론 제어 시스템 구현 (45분)
4. GUI와 안전 기능 구현 (45분)

---

# 1. AI 기반 드론 제어 시스템 구조

## 필수 라이브러리 소개
- DJITelloPy: 텔로 드론 제어
- SpeechRecognition: 음성 인식
- OpenAI/Google Gemini: AI 명령 처리
- PyQt5: GUI 인터페이스
- gTTS: 텍스트 음성 변환

---

## 환경 설정

### 1. API 키 설정
```python
# .env 파일 설정
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_gemini_key

# 코드에서 로드
from dotenv import load_dotenv
load_dotenv()
```

### 2. 기본 패키지 설치
```bash
pip install djitellopy opencv-python
pip install speechrecognition openai
pip install google-generativeai
pip install PyQt5 gtts pygame
```

---

## 드론 컨트롤러 기본 구조
```python
class DroneController:
    def __init__(self):
        self.tello = Tello()
        self.frame_reader = None
        self.is_streaming = False
        
    def connect(self):
        """드론 연결 및 상태 확인"""
        print("드론에 연결 중...")
        self.tello.connect()
        
        battery = self.tello.get_battery()
        print(f"배터리 잔량: {battery}%")
        
        if battery < 20:
            raise Exception("배터리 부족")
```

---

# 2. 음성 인식과 AI 통합

## 음성 인식 시스템
```python
def setup_voice_recognition():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        # 주변 소음 조정
        recognizer.adjust_for_ambient_noise(source)
        print("음성 인식 준비 완료")
    return recognizer

def recognize_speech(recognizer):
    with sr.Microphone() as source:
        print("명령을 말씀해주세요...")
        audio = recognizer.listen(source)
        return recognizer.recognize_google(
            audio, language='ko-KR'
        )
```

---

## AI 명령 처리 시스템

### 1. OpenAI GPT 활용
```python
def process_voice_command(audio_text: str) -> Dict:
    system_prompt = """
    당신은 드론 제어 시스템입니다.
    사용자의 자연어 명령을 드론 제어 명령으로 변환합니다.
    
    예시:
    - "위로 1미터 올라가줘" -> move(up, 100)
    - "앞으로 30센티미터" -> move(forward, 30)
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
                        "command": {
                            "type": "string",
                            "enum": ["takeoff", "land", "move"]
                        }
                    }
                }
            }
        }]
    )
    return response
```

---

### 2. Google Gemini 활용
```python
def process_voice_command(audio_text: str) -> Dict:
    prompt = """
    드론 제어 시스템입니다. 명령을 JSON으로 변환합니다.
    
    가능한 명령:
    1. 이륙: {"command": "takeoff"}
    2. 착륙: {"command": "land"}
    3. 이동: {
        "command": "move",
        "parameters": {
            "direction": "up/down/left/right",
            "distance": 20-500
        }
    }
    """
    
    response = model.generate_content(prompt + audio_text)
    return json.loads(response.text)
```

---

# 3. 드론 제어 시스템 구현

## 명령 실행 시스템
```python
def execute_function(self, command: str, params: Dict = None):
    try:
        if command == "takeoff":
            self.tello.takeoff()
        elif command == "land":
            self.tello.land()
        elif command == "move":
            direction = params["direction"]
            distance = params["distance"]
            
            if direction == "up":
                self.tello.move_up(distance)
            elif direction == "forward":
                self.tello.move_forward(distance)
            # ... 기타 방향 처리
            
        time.sleep(1)  # 명령 실행 후 대기
        
    except Exception as e:
        print(f"명령 실행 오류: {str(e)}")
        self.emergency_land()
```

---

## 비디오 스트리밍 처리
```python
def start_video_stream(self):
    """비디오 스트리밍 시작"""
    self.tello.streamon()
    time.sleep(2)  # 스트림 초기화 대기
    self.frame_reader = self.tello.get_frame_read()
    self.is_streaming = True
    
    # 스트리밍 스레드 시작
    self.stream_thread = threading.Thread(
        target=self._stream_loop
    )
    self.stream_thread.daemon = True
    self.stream_thread.start()
```

---

# 4. GUI와 안전 기능 구현

## PyQt5 기반 GUI
```python
class DroneGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tello Control")
        self.image_label = QLabel(self)
        self.setCentralWidget(self.image_label)
        self.resize(960, 720)
        
        # GUI 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_gui)
        self.update_timer.start(30)  # 30ms (약 33fps)
```

---

## 안전 기능 구현

### 1. 배터리 모니터링
```python
def check_battery(self):
    battery = self.tello.get_battery()
    if battery < 20:
        print(f"경고: 배터리 부족 ({battery}%)")
        return False
    return True
```

### 2. 비상 착륙
```python
def emergency_land(self):
    try:
        print("비상 착륙 시도...")
        self.tello.land()
    except:
        print("강제 종료")
        self.tello.emergency()
```

---

## 통합 시스템 구현
```python
def main():
    controller = DroneController()
    recognizer = setup_voice_recognition()
    
    try:
        controller.connect()
        controller.start_video_stream()
        
        while True:
            # 음성 명령 처리
            text = recognize_speech(recognizer)
            if "종료" in text:
                break
                
            # AI 명령 해석 및 실행
            command = process_voice_command(text)
            if controller.check_battery():
                controller.execute_function(
                    command["command"],
                    command.get("parameters")
                )
            
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        controller.emergency_land()
```

---

# 실습 과제

## 1. 기본 기능 구현
- 드론 연결 및 상태 확인
- 비디오 스트리밍 설정
- 기본 명령어 처리

## 2. AI 통합
- OpenAI/Gemini API 연동
- 음성 명령 처리 구현
- 자연어 해석 시스템

## 3. 안전 기능
- 배터리 모니터링
- 비상 착륙 시스템
- 에러 처리

---

# 참고 자료

## 1. API 문서
- DJITelloPy: https://djitellopy.readthedocs.io/
- OpenAI: https://platform.openai.com/docs
- Gemini: https://ai.google.dev/docs

## 2. 예제 코드
- tello-scan-surroundings.py
- voice-control-tello-gemini.py
- tello-webui.py