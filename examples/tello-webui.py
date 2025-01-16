from flask import Flask, render_template, Response, jsonify, request, send_from_directory
import cv2
import threading
from queue import Queue
import os
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
        self.is_flying = False  # 이륙 상태 추적
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
                model="gpt-4o-mini",
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
        print("착륙!")
        self.tello.land()
        self.is_flying = False

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

    def rotate(self, direction: str, angle: int):
        """드론 회전
        direction: clockwise, counter_clockwise
        angle: 회전 각도
        """
        print(f"{direction} 방향으로 {angle}도 회전")
        if direction == "clockwise":
            self.tello.rotate_clockwise(angle)
        else:
            self.tello.rotate_counter_clockwise(angle)

# 전역 컨트롤러 인스턴스
controller = None

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

def ensure_template_exists():
    """템플릿 디렉토리와 파일이 존재하는지 확인하고 생성"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    template_path = os.path.join(template_dir, 'index.html')
    if not os.path.exists(template_path):
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
        }
        .video-container {
            margin: 20px 0;
            text-align: center;
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
            padding: 10px;
            border-radius: 5px;
        }
        .success {
            background-color: #dff0d8;
            color: #3c763d;
        }
        .error {
            background-color: #f2dede;
            color: #a94442;
        }
        #analysis {
            margin: 20px 0;
            padding: 15px;
            background-color: #fff;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Tello Drone Scanner</h1>
        <div class="video-container">
            <img src="{{ url_for('video_feed') }}" width="640" height="480">
        </div>
        <div class="controls">
            <button onclick="connectDrone()">드론 연결</button>
            <button onclick="scanSurroundings()">주변 스캔</button>
            <button onclick="createPanorama()">파노라마 촬영</button>
        </div>
        <div id="status"></div>
        <div id="analysis"></div>
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