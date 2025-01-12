from djitellopy import Tello
import speech_recognition as sr
import time

def process_command(command_text):
    """음성 명령을 처리하는 함수"""
    command_text = command_text.lower().strip()
    print(f"인식된 명령: {command_text}")
    
    # 명령어 사전
    commands = {
        "이륙": "takeoff",
        "착륙": "land", 
        "위로": "up",
        "아래로": "down",
        "왼쪽": "left",
        "오른쪽": "right",
        "앞으로": "forward",
        "뒤로": "back",
        "회전": "rotate"
    }
    
    # 기본 이동 거리 (cm)
    distance = 30
    
    for key in commands:
        if key in command_text:
            return commands[key], distance
            
    return None, None

def voice_control():
    print("드론 음성/키보드 제어를 시작합니다...")
    
    # 드론 초기화
    tello = Tello()
    recognizer = sr.Recognizer()
    
    try:
        # 드론 연결
        print("1. 드론에 연결 중...")
        tello.connect()
        print("✓ 연결 성공!")
        
        # 배터리 확인
        battery = tello.get_battery()
        print(f"✓ 배터리 잔량: {battery}%")
        
        if battery < 10:
            raise Exception("배터리가 너무 부족합니다")
        
        print("\n사용 가능한 명령어:")
        print("- '이륙': 드론을 이륙시킵니다")
        print("- '착륙': 드론을 착륙시킵니다")
        print("- '위로': 드론을 위로 이동시킵니다")
        print("- '아래로': 드론을 아래로 이동시킵니다")
        print("- '왼쪽': 드론을 왼쪽으로 이동시킵니다")
        print("- '오른쪽': 드론을 오른쪽으로 이동시킵니다")
        print("- '앞으로': 드론을 앞으로 이동시킵니다")
        print("- '뒤로': 드론을 뒤로 이동시킵니다")
        print("- '회전': 드론을 오른쪽으로 회전시킵니다")
        print("\n'종료'를 입력하거나 말하면 프로그램이 종료됩니다")
        print("'음성'을 입력하면 음성 인식 모드로 전환됩니다")
        
        # 메인 루프
        while True:
            print("\n명령을 입력하거나 '음성'을 입력하여 음성 명령을 사용하세요...")
            
            # 키보드 입력 받기
            user_input = input("> ").strip()
            
            # 음성 인식 모드
            if user_input.lower() == "음성":
                print("음성 명령을 기다리는 중...")
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source)
                    audio = recognizer.listen(source)
                try:
                    command_text = recognizer.recognize_google(audio, language='ko-KR')
                except sr.UnknownValueError:
                    print("음성을 인식하지 못했습니다.")
                    continue
                except sr.RequestError as e:
                    print(f"음성 인식 서비스 오류: {e}")
                    continue
            else:
                command_text = user_input
            
            # 종료 명령 확인
            if "종료" in command_text.lower():
                print("프로그램을 종료합니다.")
                break
            
            # 명령 처리
            command, distance = process_command(command_text)
            
            if command:
                print(f"명령 실행: {command}")
                
                if command == "takeoff":
                    tello.takeoff()
                elif command == "land":
                    tello.land()
                elif command == "up":
                    tello.move_up(distance)
                elif command == "down":
                    tello.move_down(distance)
                elif command == "left":
                    tello.move_left(distance)
                elif command == "right":
                    tello.move_right(distance)
                elif command == "forward":
                    tello.move_forward(distance)
                elif command == "back":
                    tello.move_back(distance)
                elif command == "rotate":
                    tello.rotate_clockwise(90)
                
                time.sleep(1)
            else:
                print("인식된 명령이 없습니다.")
                    
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        print("안전을 위해 착륙을 시도합니다...")
        try:
            tello.land()
        except:
            pass
    
    finally:
        tello.end()

if __name__ == "__main__":
    voice_control()