from djitellopy import Tello
import cv2
import time
import os
from datetime import datetime
import speech_recognition as sr
from openai import OpenAI
import json
from dotenv import load_dotenv
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
import sys
import base64
import threading
from gtts import gTTS
import pygame
import tempfile

# .env 파일 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
if not client.api_key:
    raise ValueError(".env 파일에 OPENAI_API_KEY를 설정해주세요!")

class TelloGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tello Camera")
        self.image_label = QLabel(self)
        self.setCentralWidget(self.image_label)
        self.resize(960, 720)
        
        # GUI 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_gui)
        self.update_timer.start(30)  # 30ms 간격으로 업데이트 (약 33fps)
        
        self.current_frame = None

    def update_gui(self):
        """GUI 업데이트 (타이머에 의해 호출)"""
        if self.current_frame is not None:
            self.update_image(self.current_frame)

    def update_image(self, cv_img):
        """OpenCV 이미지를 GUI에 표시"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

class TelloScanner:
    def __init__(self):
        self.tello = Tello()
        self.gui = None
        self.frame_reader = None
        self.streaming = False
        self.scan_commands = {
            "scan": {
                "name": "scan",
                "description": "현재 보이는 장면을 촬영하고 분석합니다",
                "parameters": {}
            }
        }
        
        # TTS 초기화
        pygame.mixer.init()

    def connect(self):
        """드론 연결 및 상태 확인"""
        print("드론에 연결 중...")
        self.tello.connect()
        print("✓ 연결 성공!")
        
        battery = self.tello.get_battery()
        print(f"✓ 배터리 잔량: {battery}%")
        
        if battery < 20:
            raise Exception("배터리가 너무 부족합니다")
            
        # GUI 초기화
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        self.gui = TelloGUI()
        
        return True

    def start_streaming(self):
        """카메라 스트리밍 시작"""
        self.tello.streamon()
        time.sleep(2)
        self.frame_reader = self.tello.get_frame_read()
        self.streaming = True
        
        # 스트리밍 스레드 시작
        self.stream_thread = threading.Thread(target=self._stream_loop)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        
        # GUI 표시
        self.gui.show()

    def _stream_loop(self):
        """실시간 스트리밍 루프"""
        while self.streaming:
            frame = self.frame_reader.frame
            if frame is not None:
                self.gui.current_frame = frame.copy()
            time.sleep(0.01)

    def take_photo(self):
        """사진 촬영 및 저장"""
        # 사진 저장 디렉토리 생성
        if not os.path.exists('photos'):
            os.makedirs('photos')
            
        # 현재 시간을 파일명으로 사용
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'photos/tello_scan_{timestamp}.jpg'
        
        # 프레임 캡처 및 저장
        frame = self.frame_reader.frame
        cv2.imwrite(filename, frame)
        print(f"사진 저장됨: {filename}")
        return filename, frame

    def analyze_image(self, image_path: str) -> str:
        """GPT Vision을 사용하여 이미지 분석"""
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "이 이미지에서 보이는 것을 자세히 설명해주세요. 한국어로 답변해주세요. 말하듯이 줄글로 답변해."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        return response.choices[0].message.content

    def speak(self, text: str):
        """텍스트를 음성으로 변환하여 재생"""
        try:
            # gTTS를 사용하여 음성 파일 생성
            tts = gTTS(text=text, lang='ko')
            
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_filename = fp.name
                tts.save(temp_filename)
            
            # pygame으로 재생
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # 임시 파일 삭제
            os.unlink(temp_filename)
            
        except Exception as e:
            print(f"TTS 오류: {str(e)}")

    def scan_current_view(self):
        """현재 보이는 장면을 촬영하고 분석"""
        try:
            # 사진 촬영
            filename, _ = self.take_photo()
            
            # 이미지 분석
            print("이미지 분석 중...")
            analysis = self.analyze_image(filename)
            print(f"분석 결과: {analysis}")
            
            # TTS로 결과 읽기
            self.speak(analysis)
            
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            error_msg = "이미지 분석 중 오류가 발생했습니다."
            print(error_msg)
            self.speak(error_msg)

def process_voice_command(audio_text: str) -> dict:
    """음성 명령을 Function calling 형식으로 변환"""
    system_prompt = """
    당신은 드론 제어 시스템입니다. 사용자의 자연어 명령을 드론 제어 명령으로 변환합니다.
    
    가능한 명령어:
    1. scan - 현재 보이는 장면을 촬영하고 분석합니다.
    
    예시:
    - "지금 장면을 분석해줘" -> scan()
    - "사진 찍고 설명해줘" -> scan()
    - "이 장면을 설명해줘" -> scan()
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "scan",
                "description": "현재 보이는 장면을 촬영하고 분석합니다",
                "parameters": {}
            }
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": audio_text}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "scan"}}
        )

        return {"command": "scan"}

    except Exception as e:
        print(f"OpenAI API 오류: {str(e)}")
        raise

def main():
    scanner = TelloScanner()
    recognizer = sr.Recognizer()
    
    print("\n드론 카메라 시스템을 시작합니다...")
    print("\n사용 가능한 명령어 예시:")
    print("- '지금 장면을 분석해줘'")
    print("- '사진 찍고 설명해줘'")
    print("- '이 장면을 설명해줘'")
    print("- '종료' - 프로그램을 종료합니다")
    
    try:
        scanner.connect()
        scanner.start_streaming()
        
        while True:
            with sr.Microphone() as source:
                print("\n명령을 말씀해주세요... (종료하려면 '종료'라고 말씀해주세요)")
                
                # 음성 인식
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source)
                
                try:
                    # 음성을 텍스트로 변환
                    text = recognizer.recognize_google(audio, language='ko-KR')
                    print(f"\n인식된 명령: {text}")
                    
                    # 종료 명령 확인
                    if "종료" in text:
                        print("프로그램을 종료합니다.")
                        break
                    
                    # GPT를 통한 명령 해석
                    command = process_voice_command(text)
                    print(f"해석된 명령: {json.dumps(command, ensure_ascii=False)}")
                    
                    # 스캔 실행
                    scanner.scan_current_view()
                    
                except sr.UnknownValueError:
                    print("음성을 인식하지 못했습니다.")
                except sr.RequestError as e:
                    print(f"음성 인식 서비스 오류: {e}")
                except Exception as e:
                    print(f"오류 발생: {str(e)}")
                    
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
    finally:
        scanner.tello.streamoff()
        scanner.tello.end()
        QApplication.quit()

if __name__ == "__main__":
    main() 