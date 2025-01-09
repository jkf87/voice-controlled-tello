from djitellopy import Tello
import speech_recognition as sr
from typing import Dict, Any
import openai

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

    def execute_function(self, function_name: str, parameters: Dict[str, Any] = None):
        """Function calling 결과를 실제 드론 명령으로 실행"""
        if function_name == "takeoff":
            return self.tello.takeoff()
            
        elif function_name == "land":
            return self.tello.land()
            
        elif function_name == "move":
            direction = parameters["direction"]
            distance = parameters["distance"]
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
            if direction == "clockwise":
                return self.tello.rotate_clockwise(angle)
            else:
                return self.tello.rotate_counter_clockwise(angle)

def process_voice_command(audio_text: str) -> Dict:
    """음성 명령을 Function calling 형식으로 변환"""
    functions = [
        {
            "name": "control_drone",
            "description": "음성 명령을 드론 제어 명령으로 변환",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["takeoff", "land", "move", "rotate"]
                    },
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "direction": {
                                "type": "string"
                            },
                            "distance": {
                                "type": "integer"
                            },
                            "angle": {
                                "type": "integer"
                            }
                        }
                    }
                },
                "required": ["command"]
            }
        }
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "드론 제어 명령을 처리하는 시스템입니다."},
            {"role": "user", "content": audio_text}
        ],
        functions=functions,
        function_call={"name": "control_drone"}
    )

    return response.choices[0].message.function_call

def main():
    controller = TelloController()
    recognizer = sr.Recognizer()
    
    try:
        controller.tello.connect()
        print(f"배터리 잔량: {controller.tello.get_battery()}%")
        
        with sr.Microphone() as source:
            while True:
                print("명령을 말씀해주세요...")
                audio = recognizer.listen(source)
                try:
                    text = recognizer.recognize_google(audio, language='ko-KR')
                    print(f"인식된 명령: {text}")
                    
                    # Function calling으로 명령 처리
                    function_call = process_voice_command(text)
                    command = function_call.name
                    parameters = eval(function_call.arguments)
                    
                    # 드론 제어 실행
                    controller.execute_function(command, parameters)
                    
                except sr.UnknownValueError:
                    print("음성을 인식하지 못했습니다.")
                except Exception as e:
                    print(f"오류 발생: {str(e)}")
                
    finally:
        controller.tello.end()

if __name__ == "__main__":
    main() 