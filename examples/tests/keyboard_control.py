from djitellopy import Tello
import time

def keyboard_control():
    print("드론 키보드 제어를 시작합니다...")
    
    # 드론 초기화
    tello = Tello()
    
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
        
        print("\n사용 가능한 키보드 명령어:")
        print("- 't': 이륙")
        print("- 'l': 착륙")
        print("- 'w': 위로 30cm")
        print("- 's': 아래로 30cm")
        print("- 'a': 왼쪽으로 30cm")
        print("- 'd': 오른쪽으로 30cm")
        print("- 'i': 앞으로 30cm")
        print("- 'k': 뒤로 30cm")
        print("- 'r': 오른쪽으로 90도 회전")
        print("- 'q': 프로그램 종료")
        
        # 기본 이동 거리 (cm)
        distance = 30
        
        # 메인 루프
        while True:
            command = input("\n명령을 입력하세요: ").lower().strip()
            
            if command == 'q':
                print("프로그램을 종료합니다.")
                break
                
            try:
                if command == 't':
                    print("이륙!")
                    tello.takeoff()
                elif command == 'l':
                    print("착륙!")
                    tello.land()
                elif command == 'w':
                    print(f"위로 {distance}cm 이동")
                    tello.move_up(distance)
                elif command == 's':
                    print(f"아래로 {distance}cm 이동")
                    tello.move_down(distance)
                elif command == 'a':
                    print(f"왼쪽으로 {distance}cm 이동")
                    tello.move_left(distance)
                elif command == 'd':
                    print(f"오른쪽으로 {distance}cm 이동")
                    tello.move_right(distance)
                elif command == 'i':
                    print(f"앞으로 {distance}cm 이동")
                    tello.move_forward(distance)
                elif command == 'k':
                    print(f"뒤로 {distance}cm 이동")
                    tello.move_back(distance)
                elif command == 'r':
                    print("오른쪽으로 90도 회전")
                    tello.rotate_clockwise(90)
                else:
                    print("알 수 없는 명령입니다.")
                    continue
                    
                time.sleep(1)  # 명령 사이에 잠시 대기
                
            except Exception as e:
                print(f"명령 실행 중 오류 발생: {e}")
                
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
    keyboard_control() 