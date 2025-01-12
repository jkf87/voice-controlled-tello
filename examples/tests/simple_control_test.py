from djitellopy import Tello
import time

def control_test():
    print("드론 제어 테스트를 시작합니다...")
    tello = Tello()
    
    try:
        # 연결
        print("1. 드론에 연결 중...")
        tello.connect()
        print("✓ 연결 성공!")
        
        # 배터리 확인
        battery = tello.get_battery()
        print(f"✓ 배터리 잔량: {battery}%")
        
        if battery < 10:
            raise Exception("배터리가 너무 부족합니다")
            
        input("\n이륙 준비가 되었다면 Enter를 눌러주세요... (충분한 공간 확보 필요)")
        
        # 이륙
        print("\n2. 이륙 시도...")
        tello.takeoff()
        print("✓ 이륙 성공!")
        time.sleep(3)
        
        # 상승
        print("\n3. 50cm 상승...")
        tello.move_up(50)
        time.sleep(2)
        
        # 착륙
        print("\n4. 착륙 중...")
        tello.land()
        print("✓ 착륙 완료!")
        
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
    control_test() 