from djitellopy import Tello
import speech_recognition as sr
from typing import Dict, Any
import google.generativeai as genai
import os
import json
import time
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Gemini API 초기화
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError(".env 파일에 GOOGLE_API_KEY를 설정해주세요!")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class TelloController:
    def __init__(self):
        self.tello = Tello()
        
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
        }
    }

    def connect(self):
        """드론 연결 및 상태 확인"""
        print("드론에 연결 중...")
        self.tello.connect()
        print("✓ 연결 성공!")
        
        battery = self.tello.get_battery()
        print(f"✓ 배터리 잔량: {battery}%")
        
        if battery < 10:
            raise Exception("배터리가 너무 부족합니다")
        
        return True

    def execute_function(self, function_name: str, parameters: Dict[str, Any] = None):
        """Function calling 결과를 실제 드론 명령으로 실행"""
        try:
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
    prompt = """당신은 드론 제어 시스템입니다. 사용자의 자연어 명령을 드론 제어 명령으로 변환합니다.

가능한 명령어와 형식:
1. 이륙: {"command": "takeoff"}
2. 착륙: {"command": "land"}
3. 이동: {"command": "move", "parameters": {"direction": "[up/down/left/right/forward/back]", "distance": [20-500]}}
4. 회전: {"command": "rotate", "parameters": {"direction": "[clockwise/counter_clockwise]", "angle": [1-360]}}

예시:
- "위로 1미터 올라가줘" -> {"command": "move", "parameters": {"direction": "up", "distance": 100}}
- "오른쪽으로 90도 돌아" -> {"command": "rotate", "parameters": {"direction": "clockwise", "angle": 90}}

사용자 명령을 위 JSON 형식으로 변환하여 응답해주세요. 응답은 반드시 유효한 JSON 형식이어야 합니다.

사용자 명령: """ + audio_text

    try:
        response = model.generate_content(prompt)
        # JSON 문자열을 찾아 파싱
        response_text = response.text
        # JSON 부분만 추출 (중괄호로 둘러싸인 부분)
        json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
        command = json.loads(json_str)
        return command
        
    except Exception as e:
        print(f"Gemini API 오류: {str(e)}")
        raise

def main():
    controller = TelloController()
    recognizer = sr.Recognizer()
    
    print("\n드론 음성 제어 시스템을 시작합니다... (Gemini 버전)")
    print("\n사용 가능한 명령어 예시:")
    print("- '이륙해줘' - 드론을 이륙시킵니다")
    print("- '착륙해' - 드론을 착륙시킵니다")
    print("- '위로 1미터 올라가' - 드론을 위로 이동시킵니다")
    print("- '왼쪽으로 30센티미터 가줘' - 드론을 왼쪽으로 이동시킵니다")
    print("- '오른쪽으로 90도 돌아' - 드론을 오른쪽으로 회전시킵니다")
    print("- '종료' - 프로그램을 종료합니다")
    
    try:
        controller.connect()
        
        with sr.Microphone() as source:
            while True:
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
                    
                    # Gemini를 통한 명령 해석
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
                
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        print("안전을 위해 착륙을 시도합니다...")
        try:
            controller.execute_function("land")
        except:
            pass
    
    finally:
        controller.tello.end()

if __name__ == "__main__":
    main() 