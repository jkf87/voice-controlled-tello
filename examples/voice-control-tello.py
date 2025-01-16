from djitellopy import Tello
import speech_recognition as sr
from typing import Dict, Any
from openai import OpenAI
import os
import json
import time
from dotenv import load_dotenv
import cv2
from datetime import datetime
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
import sys
from ultralytics import YOLO
import numpy as np

# YOLO 모델 로드 및 최적화
model = YOLO('yolov8n.pt')
model.to('cpu')  # CPU 모드로 설정

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
        self.resize(640, 480)
        self.detected_objects = []
        
        # FPS 계산을 위한 변수들
        self.prev_frame_time = time.time()
        self.fps_array = []  # 최근 FPS 값들을 저장할 배열
        self.fps_array_size = 30  # 평균을 계산할 FPS 샘플 수
        
        # GUI 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_gui)
        self.update_timer.start(30)  # 30ms 간격으로 업데이트 (약 33fps)
        
        self.current_frame = None
        self.current_detections = None

    def update_gui(self):
        """GUI 업데이트 (타이머에 의해 호출)"""
        if self.current_frame is not None:
            self.update_image(self.current_frame, self.current_detections)

    def update_image(self, cv_img, detections=None):
        display_img = cv_img.copy()
        
        # FPS 계산
        current_time = time.time()
        fps = 1.0 / (current_time - self.prev_frame_time)
        self.prev_frame_time = current_time
        
        # FPS 이동 평균 계산
        self.fps_array.append(fps)
        if len(self.fps_array) > self.fps_array_size:
            self.fps_array.pop(0)
        avg_fps = sum(self.fps_array) / len(self.fps_array)
        
        # FPS 텍스트 표시
        fps_text = f"FPS: {avg_fps:.1f}"
        cv2.putText(display_img, fps_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 객체 감지 결과 표시
        if detections is not None:
            for r in detections:
                boxes = r.boxes
                for box in boxes:
                    # 박스 좌표
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    # 클래스와 신뢰도
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    # 정수로 변환
                    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                    
                    # 박스 그리기
                    cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # 라벨 표시
                    label = f"{model.names[cls]} {conf:.2f}"
                    cv2.putText(display_img, label, (x1, y1 - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # 이미지 변환 및 표시
        rgb_image = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

class TelloController:
    def __init__(self):
        self.tello = Tello()
        self.camera_thread = None
        self.processing_thread = None
        self.stop_camera = False
        self.detect_objects = False
        self.continuous_detection = False
        self.frame_count = 0
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        self.gui = TelloGUI()
        
        # 프레임 버퍼
        self.frame_buffer = None
        self.frame_ready = threading.Event()
        self.frame_lock = threading.Lock()
        
        # 프레임 스킵용 변수
        self.frame_skip = 5  # 예: 5프레임마다 한 번만 감지
        self.frame_counter = 0

    def start_camera(self):
        """카메라 스트리밍 시작"""
        print("카메라 스트리밍 시작...")
        self.tello.streamon()
        time.sleep(2)  # 스트림 초기화를 위한 대기
        self.frame_reader = self.tello.get_frame_read()  # 프레임 리더 초기화
        self.stop_camera = False
        self.gui.show()
        
        # 카메라 스트리밍 스레드 시작
        self.camera_thread = threading.Thread(target=self._camera_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        
        # 프레임 처리 스레드 시작
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def stop_camera(self):
        """카메라 스트리밍 중지"""
        self.stop_camera = True
        if self.camera_thread:
            self.camera_thread.join()
        if self.processing_thread:
            self.processing_thread.join()
        self.tello.streamoff()
        self.gui.close()
        
    def _camera_loop(self):
        """카메라 스트리밍 루프 (프레임 캡처만 담당)"""
        print("카메라 루프 시작")
        
        while not self.stop_camera:
            try:
                frame = self.frame_reader.frame
                if frame is not None:
                    with self.frame_lock:
                        self.frame_buffer = frame.copy()
                    self.frame_ready.set()
                else:
                    print("프레임이 None입니다")
                time.sleep(0.01)  # 대기 시간 감소
            except Exception as e:
                print(f"프레임 캡처 중 오류 발생: {str(e)}")
                time.sleep(0.1)
            
    def _processing_loop(self):
        """프레임 처리 루프 (객체 감지 및 GUI 업데이트 담당)"""
        print("처리 루프 시작")
        while not self.stop_camera:
            if self.frame_ready.wait(timeout=0.1):
                with self.frame_lock:
                    if self.frame_buffer is not None:
                        frame = self.frame_buffer.copy()
                    else:
                        frame = None
                self.frame_ready.clear()
                
                if frame is not None:
                    # 표시/추론용 해상도 축소 (예: 320x240)
                    display_frame = cv2.resize(frame, (320, 240))
                    
                    # 프레임 스킵을 위해 카운터 증가
                    self.frame_counter += 1
                    
                    # 스킵 조건: (continuous_detection 또는 detect_objects) && (frame_counter % frame_skip == 0)
                    if (self.continuous_detection or self.detect_objects) and (self.frame_counter % self.frame_skip == 0):
                        try:
                            results = model(display_frame, conf=0.5, iou=0.45)
                            self.gui.current_frame = display_frame
                            self.gui.current_detections = results
                            
                            # detect_objects가 True였다면, 감지 후 즉시 False로
                            if self.detect_objects:
                                detected = []
                                for r in results:
                                    for box in r.boxes:
                                        cls = int(box.cls[0])
                                        conf = float(box.conf[0])
                                        label = f"{model.names[cls]} ({conf:.2f})"
                                        detected.append(label)
                                self.gui.detected_objects = detected
                                self.detect_objects = False
                        except Exception as e:
                            print(f"객체 감지 중 오류 발생: {str(e)}")
                            self.gui.current_frame = display_frame
                            self.gui.current_detections = None
                    else:
                        # 감지 없이 화면만 업데이트
                        self.gui.current_frame = display_frame
                        self.gui.current_detections = None
                    
                    self.frame_count += 1

    def get_detected_objects(self) -> list:
        """현재 감지된 객체 목록 반환"""
        self.detect_objects = True
        time.sleep(0.2)  # 대기 시간 단축
        return self.gui.detected_objects

    def connect(self):
        """드론 연결 및 상태 확인"""
        print("드론에 연결 중...")
        self.tello.connect()
        print("✓ 연결 성공!")
        
        # IMU 안정화를 위한 대기
        print("IMU 센서 안정화 대기 중...")
        time.sleep(3)
        
        battery = self.tello.get_battery()
        print(f"✓ 배터리 잔량: {battery}%")
        
        if battery < 10:
            raise Exception("배터리가 너무 부족합니다")
            
        # 카메라 스트리밍 시작
        self.start_camera()
        
        return True
        
    def __del__(self):
        """소멸자: 프로그램 종료 시 정리"""
        self.stop_camera = True
        if self.camera_thread:
            self.camera_thread.join()
        if self.processing_thread:
            self.processing_thread.join()
        self.tello.end()

    # 드론 제어를 위한 함수들을 Function Calling 형태로 정의
    available_functions = {
        "takeoff": {
            "name": "takeoff",
            "description": "드론을 이륙시킵니다",
            "parameters": {}
        },
        "land": {
            "name": "land",
            "description": "드론을 착륙시킵니다",
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
        },
        "rotate": {
            "name": "rotate",
            "description": "드론을 회전시킵니다",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["clockwise", "counter_clockwise"]
                    },
                    "angle": {
                        "type": "integer",
                        "description": "회전 각도",
                        "minimum": 1,
                        "maximum": 360
                    }
                },
                "required": ["direction", "angle"]
            }
        },
        "detect_objects": {
            "name": "detect_objects",
            "description": "현재 카메라에 보이는 물체를 감지합니다",
            "parameters": {}
        }
    }

    def execute_function(self, function_name: str, parameters: Dict[str, Any] = None):
        """Function calling 결과를 실제 드론 명령으로 실행"""
        try:
            if function_name == "detect_objects":
                self.continuous_detection = True  # 연속 감지 모드 활성화
                detected = self.get_detected_objects()
                if detected:
                    print(f"감지된 물체들: {', '.join(detected)}")
                else:
                    print("감지된 물체가 없습니다.")
                return
                
            if function_name == "takeoff":
                print("이륙!")
                return self.tello.takeoff()
                
            elif function_name == "land":
                print("착륙!")
                return self.tello.land()
                
            elif function_name == "move":
                direction = parameters["direction"]
                distance = parameters["distance"]
                print(f"{direction} 방향으로 {distance}cm 이동")
                
                if direction == "up":
                    return self.tello.move_up(distance)
                elif direction == "down":
                    return self.tello.move_down(distance)
                elif direction == "left":
                    return self.tello.move_left(distance)
                elif direction == "right":
                    return self.tello.move_right(distance)
                elif direction == "forward":
                    return self.tello.move_forward(distance)
                elif direction == "back":
                    return self.tello.move_back(distance)
                
            elif function_name == "rotate":
                direction = parameters["direction"]
                angle = parameters["angle"]
                print(f"{direction} 방향으로 {angle}도 회전")
                
                if direction == "clockwise":
                    return self.tello.rotate_clockwise(angle)
                else:
                    return self.tello.rotate_counter_clockwise(angle)
                    
            time.sleep(1)  # 명령 실행 후 잠시 대기
            
        except Exception as e:
            print(f"명령 실행 중 오류 발생: {str(e)}")
            raise

def process_voice_command(audio_text: str) -> Dict:
    """음성 명령을 Function calling 형식으로 변환"""
    system_prompt = """
    당신은 드론 제어 시스템입니다. 사용자의 자연어 명령을 드론 제어 명령으로 변환합니다.
    
    가능한 명령어:
    1. 이륙 (takeoff)
    2. 착륙 (land)
    3. 이동 (move) - 방향: up, down, left, right, forward, back
    4. 회전 (rotate) - 방향: clockwise, counter_clockwise
    5. 물체 감지 (detect_objects) - 현재 카메라에 보이는 물체를 감지
    
    예시:
    - "위로 1미터 올라가줘" -> move(direction="up", distance=100)
    - "오른쪽으로 90도 돌아" -> rotate(direction="clockwise", angle=90)
    - "지금 뭐가 보이니?" -> detect_objects()
    - "주변에 뭐가 있어?" -> detect_objects()
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "control_drone",
                "description": "음성 명령을 드론 제어 명령으로 변환",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "enum": ["takeoff", "land", "move", "rotate", "detect_objects"]
                        },
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "direction": {
                                    "type": "string",
                                    "enum": ["up", "down", "left", "right", "forward", "back", "clockwise", "counter_clockwise"]
                                },
                                "distance": {
                                    "type": "integer",
                                    "description": "이동 거리 (cm)"
                                },
                                "angle": {
                                    "type": "integer",
                                    "description": "회전 각도"
                                }
                            }
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    ]

    try:
        # 물체 감지 관련 키워드 확인
        detection_keywords = ["뭐가 보이", "무엇이 보이", "뭐가 있", "무엇이 있", "물체", "감지"]
        if any(keyword in audio_text for keyword in detection_keywords):
            return {"command": "detect_objects"}
            
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
        command = json.loads(tool_call.function.arguments)
        return command
        
    except Exception as e:
        print(f"OpenAI API 오류: {str(e)}")
        raise

def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    controller = TelloController()
    recognizer = sr.Recognizer()
    
    print("\n드론 음성 제어 시스템을 시작합니다...")
    print("\n사용 가능한 명령어 예시:")
    print("- '이륙해줘' - 드론을 이륙시킵니다")
    print("- '착륙해' - 드론을 착륙시킵니다")
    print("- '위로 1미터 올라가' - 드론을 위로 이동시킵니다")
    print("- '왼쪽으로 30센티미터 가줘' - 드론을 왼쪽으로 이동시킵니다")
    print("- '오른쪽으로 90도 돌아' - 드론을 오른쪽으로 회전시킵니다")
    print("- '종료' - 프로그램을 종료합니다")
    
    try:
        controller.connect()
        
        def process_voice():
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
                        controller.stop_camera()
                        app.quit()
                        return
                    
                    # GPT를 통한 명령 해석
                    command = process_voice_command(text)
                    print(f"해석된 명령: {json.dumps(command, ensure_ascii=False)}")
                    
                    # 드론 제어 실행
                    controller.execute_function(command["command"], command.get("parameters"))
                    
                except sr.UnknownValueError:
                    print("음성을 인식하지 못했습니다.")
                except sr.RequestError as e:
                    print(f"음성 인식 서비스 오류: {e}")
                except Exception as e:
                    print(f"오류 발생: {str(e)}")
                    if "착륙" in str(e) or "land" in str(e):
                        controller.execute_function("land")
                
                # 다음 음성 명령을 위한 타이머 설정
                QTimer.singleShot(100, process_voice)
        
        # 첫 음성 인식 시작
        QTimer.singleShot(100, process_voice)
        
        # Qt 이벤트 루프 시작
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        print("안전을 위해 착륙을 시도합니다...")
        try:
            controller.execute_function("land")
        except:
            pass
        finally:
            controller.tello.end()
            app.quit()

if __name__ == "__main__":
    main()
