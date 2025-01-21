from flask import Flask, render_template, Response, jsonify, request, send_from_directory
import cv2
import threading
from queue import Queue
import os
import json
from djitellopy import Tello
import time
from datetime import datetime
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import base64
from gtts import gTTS
import pygame
import tempfile
from smolagents import CodeAgent, ToolCallingAgent, LiteLLMModel, tool, TOOL_CALLING_SYSTEM_PROMPT
from typing import Optional
import sounddevice as sd
import soundfile as sf
import wave
import io

# .env 파일 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = Flask(__name__)

class TelloController:
    def __init__(self):
        self.tello = Tello()
        self.frame_reader = None
        self.is_streaming = False
        self.frame_queue = Queue(maxsize=10)
        self.stream_thread = None
        self.is_flying = False
        pygame.mixer.init()

    def connect(self):
        """드론 연결 및 상태 확인"""
        try:
            # 기존 연결이 있다면 정리
            if self.is_streaming:
                self.stop_video_stream()
            
            print("드론에 연결 중...")
            self.tello.connect()
            print("✓ 연결 성공!")
            
            battery = self.tello.get_battery()
            print(f"✓ 배터리 잔량: {battery}%")
            
            if battery < 20:
                raise Exception("배터리가 너무 부족합니다")
            
            return True
        except Exception as e:
            print(f"연결 오류: {str(e)}")
            raise

    def stop_video_stream(self):
        """비디오 스트리밍 중지"""
        print("비디오 스트림 정지 중...")
        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=2)
        try:
            self.tello.streamoff()
        except:
            pass
        # 큐 비우기
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except:
                pass

    def start_video_stream(self):
        """비디오 스트리밍 시작"""
        if not self.is_streaming:
            self.tello.streamon()
            time.sleep(2)  # 스트림 초기화 대기
            self.frame_reader = self.tello.get_frame_read()
            self.is_streaming = True
            
            self.stream_thread = threading.Thread(target=self._stream_loop)
            self.stream_thread.daemon = True
            self.stream_thread.start()
            print("비디오 스트리밍 시작됨")

    def _stream_loop(self):
        """비디오 스트리밍 루프"""
        while self.is_streaming:
            if self.frame_reader:
                frame = self.frame_reader.frame
                if frame is not None:
                    frame = cv2.resize(frame, (640, 480))
                    
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                        except:
                            pass
                    
                    try:
                        self.frame_queue.put_nowait(frame.copy())
                    except:
                        pass
            time.sleep(0.03)

    def take_photo(self):
        """사진 촬영"""
        if not os.path.exists('photos'):
            os.makedirs('photos')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'photos/tello_scan_{timestamp}.jpg'
        
        frame = self.frame_reader.frame
        cv2.imwrite(filename, frame)
        print(f"사진 저장됨: {filename}")
        return filename, frame

    def create_panorama(self):
        """파노라마 촬영"""
        try:
            print("파노라마 촬영 시작...")
            images = []
            
            # 360도 회전하면서 사진 촬영 (90도씩 4장)
            for i in range(4):
                print(f"사진 {i+1}/4 촬영 중...")
                frame = self.frame_reader.frame
                if frame is not None:
                    images.append(frame.copy())
                else:
                    raise Exception("프레임을 가져올 수 없습니다")
                
                if i < 3:  # 마지막 사진 후에는 회전하지 않음
                    print(f"{90}도 회전 중...")
                    self.tello.rotate_clockwise(90)
                    time.sleep(2)  # 회전 후 안정화 대기
            
            print("파노라마 이미지 생성 중...")
            stitcher = cv2.Stitcher.create()
            status, panorama = stitcher.stitch(images)
            
            if status == cv2.Stitcher_OK:
                if not os.path.exists('panoramas'):
                    os.makedirs('panoramas')
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'panoramas/tello_panorama_{timestamp}.jpg'
                cv2.imwrite(filename, panorama)
                print(f"파노라마 저장됨: {filename}")
                return filename
            else:
                raise Exception(f"파노라마 스티칭 실패 (status: {status})")
                
        except Exception as e:
            print(f"파노라마 촬영 오류: {str(e)}")
            raise

    def analyze_image(self, image_path: str) -> str:
        """GPT Vision으로 이미지 분석"""
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "이 이미지에서 보이는 것을 자세히 설명해주세요."},
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
        except Exception as e:
            print(f"이미지 분석 오류: {str(e)}")
            return f"이미지 분석 중 오류가 발생했습니다: {str(e)}"

    def speak(self, text: str):
        """텍스트를 음성으로 변환하여 재생"""
        try:
            tts = gTTS(text=text, lang='ko')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_filename = fp.name
                tts.save(temp_filename)
            
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            os.unlink(temp_filename)
        except Exception as e:
            print(f"TTS 오류: {str(e)}")

    def scan_surroundings(self):
        """현재 보이는 장면을 촬영하고 분석"""
        try:
            print("사진 촬영 중...")
            filename, _ = self.take_photo()
            
            print("이미지 분석 중...")
            analysis = self.analyze_image(filename)
            print(f"분석 결과: {analysis}")
            
            try:
                self.speak(analysis)
            except Exception as e:
                print(f"TTS 오류: {str(e)}")
            
            return filename, analysis
        except Exception as e:
            print(f"스캔 오류: {str(e)}")
            return None, f"스캔 중 오류가 발생했습니다: {str(e)}"

    def takeoff(self):
        """드론 이륙"""
        try:
            print("이륙 준비...")
            if not self.is_streaming:
                raise Exception("드론이 연결되지 않았습니다.")
            
            print("이륙!")
            self.tello.takeoff()
            time.sleep(3)  # 이륙 완료 대기
            self.is_flying = True
            print("이륙 완료!")
        except Exception as e:
            print(f"이륙 오류: {str(e)}")
            raise

    def land(self):
        """드론 착륙"""
        try:
            print("착륙!")
            self.tello.land()
            self.is_flying = False
            print("착륙 완료!")
        except Exception as e:
            print(f"착륙 오류: {str(e)}")
            raise

    def move(self, direction: str, distance: int):
        """드론 이동"""
        if not self.is_flying:
            raise Exception("드론이 이륙하지 않았습니다. 먼저 이륙해주세요.")
            
        print(f"{direction} 방향으로 {distance}cm 이동")
        if direction == "up":
            self.tello.move_up(distance)
        elif direction == "down":
            self.tello.move_down(distance)
        elif direction == "left":
            self.tello.move_left(distance)
        elif direction == "right":
            self.tello.move_right(distance)
        elif direction == "forward":
            self.tello.move_forward(distance)
        elif direction == "back":
            self.tello.move_back(distance)
        else:
            raise Exception(f"알 수 없는 방향입니다: {direction}")

    def rotate(self, direction: str, angle: int):
        """드론 회전
        direction: clockwise, counter_clockwise
        angle: 회전 각도
        """
        if not self.is_flying:
            raise Exception("드론이 이륙하지 않았습니다. 먼저 이륙해주세요.")
            
        print(f"{direction} 방향으로 {angle}도 회전")
        if direction == "clockwise":
            self.tello.rotate_clockwise(angle)
        elif direction == "counter_clockwise":
            self.tello.rotate_counter_clockwise(angle)
        else:
            raise Exception(f"알 수 없는 회전 방향입니다: {direction}")

# 전역 컨트롤러 인스턴스
controller = None

# 드론 제어를 위한 도구 함수들 정의
def tool_takeoff() -> str:
    if controller and not controller.is_flying:
        controller.takeoff()
        return "드론이 이륙했습니다."
    return "드론이 이미 이륙했거나 연결되지 않았습니다."
tool_takeoff.name = "takeoff"
tool_takeoff.description = "드론을 이륙시킵니다."
tool_takeoff.inputs = {}


def tool_land() -> str:
    if controller and controller.is_flying:
        controller.land()
        return "드론이 착륙했습니다."
    return "드론이 이미 착륙했거나 연결되지 않았습니다."
tool_land.name = "land"
tool_land.description = "드론을 착륙시킵니다."
tool_land.inputs = {}

def tool_move(direction: str, distance: int) -> str:
    """
    Args:
        direction: 이동 방향 (up, down, left, right, forward, back)
        distance: 이동 거리 (cm)
    """
    if not controller or not controller.is_flying:
        return "드론이 연결되지 않았거나 이륙하지 않았습니다."
    
    try:
        controller.move(direction, distance)
        return f"{direction} 방향으로 {distance}cm 이동했습니다."
    except Exception as e:
        return f"이동 중 오류가 발생했습니다: {str(e)}"
tool_move.name = "move"
tool_move.description = "드론을 지정된 방향으로 이동시킵니다."
tool_move.inputs = {
    "type": "object",
    "properties": {
        "direction": {
            "type": "string",
            "description": "이동 방향 (up, down, left, right, forward, back 중 하나)"
        },
        "distance": {
            "type": "integer",
            "description": "이동 거리 (cm)"
        }
    },
    "required": ["direction", "distance"]
}

def tool_rotate(direction: str, angle: int) -> str:
    """
    Args:
        direction: 회전 방향 (clockwise, counter_clockwise)
        angle: 회전 각도 (도)
    """
    if not controller or not controller.is_flying:
        return "드론이 연결되지 않았거나 이륙하지 않았습니다."
    
    try:
        controller.rotate(direction, angle)
        return f"{direction} 방향으로 {angle}도 회전했습니다."
    except Exception as e:
        return f"회전 중 오류가 발생했습니다: {str(e)}"
tool_rotate.name = "rotate"
tool_rotate.description = "드론을 회전시킵니다."
tool_rotate.inputs = {
    "type": "object",
    "properties": {
        "direction": {
            "type": "string",
            "description": "회전 방향 (clockwise, counter_clockwise 중 하나)"
        },
        "angle": {
            "type": "integer",
            "description": "회전 각도 (도)"
        }
    },
    "required": ["direction", "angle"]
}

def tool_take_photo() -> str:
    if controller:
        filename, _ = controller.take_photo()
        return f"사진이 {filename}에 저장되었습니다."
    return "드론이 연결되지 않았습니다."
tool_take_photo.name = "take_photo"
tool_take_photo.description = "드론 카메라로 사진을 촬영합니다."
tool_take_photo.inputs = {}

def tool_analyze_view() -> str:
    if controller:
        _, analysis = controller.scan_surroundings()
        return analysis
    return "드론이 연결되지 않았습니다."
tool_analyze_view.name = "analyze_view"
tool_analyze_view.description = "드론 카메라의 현재 시야를 분석합니다."
tool_analyze_view.inputs = {}

# 드론 제어 에이전트
def create_drone_agent():
    system_prompt = """{{managed_agents_descriptions}}
당신은 Tello 드론을 제어하는 전문가입니다.
주어진 자연어 명령을 이해하고, djitellopy 라이브러리를 사용하여 드론을 제어하는 파이썬 코드를 생성해야 합니다.
생성된 코드는 반드시 실행 가능한 형태여야 합니다.
다음과 같은 명령어를 이해하고 실행할 수 있습니다:
1. 이륙/착륙 명령
2. 상하좌우/전진/후진 이동 (거리 단위: cm)
3. 시계/반시계 방향 회전 (각도 단위: 도)

예시:
- "이륙해줘" -> `tello.takeoff()`
- "착륙해줘" -> `tello.land()`
- "3미터 앞으로 가줘" -> `tello.move_forward(300)`
- "90도 시계방향으로 회전해줘" -> `tello.rotate_clockwise(90)`

생성된 코드는 반드시 다음과 같은 형식으로 반환해야 합니다:
```
tello.takeoff()
```
또는
```
tello.land()
```
또는
```
tello.move_forward(300)
```
또는
```
tello.rotate_clockwise(90)
```
등등
"""
    @tool
    def drone_control(command: str) -> str:
        """
        드론을 제어하는 도구입니다.
        Args:
            command: 실행할 드론 명령어 (예: 'takeoff', 'land', 'move_forward(100)')
        Returns:
            str: 명령 실행 결과 메시지
        """
        if not controller:
            return "드론이 연결되지 않았습니다."
            
        tello = controller.tello
        try:
            # JSON 파싱 시도
            try:
                parsed = json.loads(command)
                if "command" in parsed:
                    command = parsed["command"]  # "takeoff" 같은 순수 문자열로 치환
            except json.JSONDecodeError:
                pass  # JSON이 아닌 경우 원래 command 사용
            
            # tello. 접두사가 있다면 제거
            if command.startswith('tello.'):
                command = command[6:]
                
            # 괄호가 없는 경우 추가
            if '(' not in command:
                command = f"{command}()"
                
            # 명령어 실행
            getattr(tello, command.split('(')[0])(*eval(f"[{command.split('(')[1][:-1]}]" if '(' in command else "[]"))
            return f"명령 실행 완료: {command}"
        except Exception as e:
            return f"명령 실행 실패: {str(e)}"
            
    return ToolCallingAgent(
        tools=[drone_control],
        model=LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY")),
        system_prompt=system_prompt
    )

# 카메라 제어 에이전트
def create_camera_agent():
    system_prompt = """{{managed_agents_descriptions}}
당신은 드론의 카메라 제어와 영상 분석을 담당하는 전문가입니다.
사진 촬영과 장면 분석을 수행할 수 있습니다.

자연어 명령을 받으면 적절한 도구를 선택하여 실행하세요.
예시:
- "사진 찍어줘" -> take_photo()
- "지금 보이는 장면을 분석해줘" -> analyze_view()
"""
    return ToolCallingAgent(
        tools=[tool_take_photo, tool_analyze_view],
        model=LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY")),
        system_prompt=system_prompt
    )

# 코드 에이전트 (예시)
def create_code_agent():
    system_prompt = """{{managed_agents_descriptions}}
당신은 파이썬 코드를 실행할 수 있는 에이전트입니다.
주어진 명령을 수행하는 파이썬 코드를 작성하고 실행하세요.
"""
    return CodeAgent(
        model=LiteLLMModel(model_id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY")),
        system_prompt=system_prompt
    )


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(get_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/connect', methods=['POST'])
def connect_drone():
    global controller
    try:
        if controller is None:
            controller = TelloController()
        
        controller.connect()
        controller.start_video_stream()
        return jsonify({"status": "success", "message": "드론이 연결되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/scan', methods=['POST'])
def scan_surroundings():
    try:
        if controller:
            filename, analysis = controller.scan_surroundings()
            image_url = f'/photos/{os.path.basename(filename)}'
            return jsonify({
                "status": "success",
                "message": "스캔이 완료되었습니다.",
                "analysis": analysis,
                "image_url": image_url
            })
        return jsonify({"status": "error", "message": "드론이 연결되지 않았습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/panorama', methods=['POST'])
def create_panorama():
    try:
        if controller:
            panorama_path = controller.create_panorama()
            analysis = controller.analyze_image(panorama_path)
            return jsonify({
                "status": "success",
                "message": "파노라마 촬영이 완료되었습니다.",
                "analysis": analysis
            })
        return jsonify({"status": "error", "message": "드론이 연결되지 않았습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/photos/<path:filename>')
def serve_photo(filename):
    return send_from_directory('photos', filename)

@app.route('/control', methods=['POST'])
def control_drone():
    try:
        if controller:
            command = request.json.get('command')
            params = request.json.get('parameters', {})
            
            if command == "takeoff":
                controller.takeoff()
            elif command == "land":
                controller.land()
            elif command == "move":
                controller.move(params['direction'], params['distance'])
            elif command == "rotate":
                controller.rotate(params['direction'], params['angle'])
            else:
                return jsonify({"status": "error", "message": "알 수 없는 명령입니다."})
                
            return jsonify({"status": "success", "message": "명령이 실행되었습니다."})
        return jsonify({"status": "error", "message": "드론이 연결되지 않았습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/agent_control', methods=['POST'])
def agent_control():
    try:
        if controller:
            command = request.json.get('command')
            agent_type = request.json.get('agent_type')
            
            if agent_type == "drone":
                agent = create_drone_agent()
            elif agent_type == "camera":
                agent = create_camera_agent()
            elif agent_type == "code":
                agent = create_code_agent()
            else:
                return jsonify({"status": "error", "message": "알 수 없는 에이전트 유형입니다."})
            
            result = agent.run(command)
            return jsonify({"status": "success", "message": result})
        return jsonify({"status": "error", "message": "드론이 연결되지 않았습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/start_recording', methods=['POST'])
def start_recording():
    try:
        # 음성 녹음 설정
        duration = 5  # 녹음 시간 (초)
        fs = 44100  # 샘플링 레이트
        channels = 1  # 모노 녹음
        
        print("음성 녹음 시작...")
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=channels)
        sd.wait()  # 녹음이 끝날 때까지 대기
        
        # 임시 WAV 파일 생성
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            wav_path = temp_wav.name
            sf.write(wav_path, recording, fs)
        
        try:
            # Whisper API로 음성을 텍스트로 변환
            with open(wav_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ko"
                )
            
            command = transcript.text
            print(f"인식된 명령: {command}")
            
            # 드론 에이전트로 명령 처리
            agent = create_drone_agent()
            result = agent.run(command)
            
            return jsonify({
                "status": "success",
                "command": command,
                "result": result
            })
            
        finally:
            # 임시 파일 삭제
            os.unlink(wav_path)
            
    except Exception as e:
        print(f"Error in voice processing: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        })

def get_frame():
    """프레임 스트리밍을 위한 제너레이터 함수"""
    while True:
        if controller and not controller.frame_queue.empty():
            frame = controller.frame_queue.get()
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            time.sleep(0.03)

def ensure_template_exists():
    """템플릿 디렉토리와 파일이 존재하는지 확인하고 생성"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    template_path = os.path.join(template_dir, 'index.html')
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Tello Drone Scanner</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f0f0f0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .video-container {
            margin: 20px 0;
            text-align: center;
            background: #000;
            padding: 10px;
            border-radius: 10px;
        }
        .video-container img {
            border-radius: 5px;
        }
        .controls {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 20px 0;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        #status {
            margin: 20px 0;
            padding: 15px;
            border-radius: 5px;
            font-weight: bold;
        }
        .success {
            background-color: #dff0d8;
            color: #3c763d;
            border: 1px solid #d6e9c6;
        }
        .error {
            background-color: #f2dede;
            color: #a94442;
            border: 1px solid #ebccd1;
        }
        #analysis {
            margin: 20px 0;
            padding: 20px;
            background-color: #fff;
            border-radius: 5px;
            border: 1px solid #ddd;
            min-height: 100px;
        }
        .agent-control {
            margin: 20px 0;
            padding: 20px;
            background-color: #fff;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .agent-control h2 {
            margin-top: 0;
            color: #333;
            font-size: 1.5em;
            margin-bottom: 15px;
        }
        .agent-input {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-top: 15px;
        }
        .agent-control select,
        .agent-control input[type="text"] {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        .agent-control select {
            width: 200px;
        }
        .agent-control input[type="text"] {
            flex-grow: 1;
        }
        .agent-control button {
            min-width: 120px;
        }
        .section {
            margin-bottom: 30px;
        }
        .section-title {
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 5px;
            border-bottom: 2px solid #4CAF50;
        }
        .voice-control {
            margin: 20px 0;
            text-align: center;
        }
        .voice-button {
            padding: 15px 30px;
            font-size: 18px;
            background-color: #e74c3c;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .voice-button:hover {
            background-color: #c0392b;
        }
        .voice-button.recording {
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Tello Drone Scanner</h1>
        
        <div class="section">
            <h2 class="section-title">드론 카메라</h2>
            <div class="video-container">
                <img src="{{ url_for('video_feed') }}" width="640" height="480">
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">기본 제어</h2>
            <div class="controls">
                <button onclick="connectDrone()">드론 연결</button>
                <button onclick="scanSurroundings()">주변 스캔</button>
                <button onclick="createPanorama()">파노라마 촬영</button>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">AI 에이전트 제어</h2>
            <div class="agent-control">
                <div class="agent-input">
                    <select id="agentType">
                        <option value="drone">드론 제어 에이전트</option>
                        <option value="camera">카메라 제어 에이전트</option>
                        <option value="code">코드 에이전트 (실험적)</option>
                    </select>
                    <input type="text" id="command" placeholder="자연어로 명령을 입력하세요 (예: '3미터 앞으로 이동하고 90도 회전해줘')">
                    <button onclick="sendAgentCommand()">명령 전송</button>
                </div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">음성 제어</h2>
            <div class="voice-control">
                <button id="voiceButton" class="voice-button" onclick="startVoiceControl()">
                    음성 명령하기
                </button>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">상태 및 분석</h2>
            <div id="status"></div>
            <div id="analysis"></div>
        </div>
    </div>

    <script>
        function updateStatus(message, isError = false) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = isError ? 'error' : 'success';
        }

        function updateAnalysis(text) {
            const analysisDiv = document.getElementById('analysis');
            analysisDiv.textContent = text;
        }

        async function connectDrone() {
            try {
                updateStatus("드론 연결 중...");
                const response = await fetch('/connect', {
                    method: 'POST'
                });
                const data = await response.json();
                updateStatus(data.message, data.status === 'error');
            } catch (error) {
                updateStatus('연결 중 오류가 발생했습니다: ' + error, true);
            }
        }

        async function scanSurroundings() {
            try {
                updateStatus("주변 스캔 중...");
                const response = await fetch('/scan', {
                    method: 'POST'
                });
                const data = await response.json();
                updateStatus(data.message, data.status === 'error');
                if (data.analysis) {
                    updateAnalysis(data.analysis);
                }
            } catch (error) {
                updateStatus('스캔 중 오류가 발생했습니다: ' + error, true);
            }
        }

        async function createPanorama() {
            try {
                updateStatus("파노라마 촬영 중...");
                const response = await fetch('/panorama', {
                    method: 'POST'
                });
                const data = await response.json();
                updateStatus(data.message, data.status === 'error');
                if (data.analysis) {
                    updateAnalysis(data.analysis);
                }
            } catch (error) {
                updateStatus('파노라마 촬영 중 오류가 발생했습니다: ' + error, true);
            }
        }

        async function sendAgentCommand() {
            try {
                const agentType = document.getElementById('agentType').value;
                const command = document.getElementById('command').value;
                
                if (!command) {
                    updateStatus('명령어를 입력해주세요.', true);
                    return;
                }
                
                updateStatus("에이전트에게 명령 전송 중...");
                const response = await fetch('/agent_control', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        agent_type: agentType,
                        command: command
                    })
                });
                const data = await response.json();
                updateStatus(data.message, data.status === 'error');
            } catch (error) {
                updateStatus('명령 실행 중 오류가 발생했습니다: ' + error, true);
            }
        }

        async function startVoiceControl() {
            const button = document.getElementById('voiceButton');
            button.classList.add('recording');
            button.textContent = '듣는 중...';
            button.disabled = true;
            
            try {
                updateStatus("음성 명령을 듣는 중...");
                const response = await fetch('/start_recording', {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    updateStatus(`명령 실행 완료: ${data.command}`);
                    if (data.result) {
                        updateAnalysis(data.result);
                    }
                } else {
                    updateStatus(data.message, true);
                }
            } catch (error) {
                updateStatus('음성 명령 처리 중 오류가 발생했습니다: ' + error, true);
            } finally {
                button.classList.remove('recording');
                button.textContent = '음성 명령하기';
                button.disabled = false;
            }
        }

        // Enter 키로 명령 전송
        document.getElementById('command').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendAgentCommand();
            }
        });
    </script>
</body>
</html>
"""
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

if __name__ == '__main__':
    # 템플릿 생성
    ensure_template_exists()
    # Flask 서버 실행
    app.run(host='0.0.0.0', port=3000, debug=False) 