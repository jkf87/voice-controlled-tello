from djitellopy import Tello
import time
import socket
import os

def cleanup_port(port):
    try:
        # Create a test socket
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_socket.bind(('', port))
        temp_socket.close()
        return True
    except:
        # Port is in use, try to force close it
        try:
            os.system(f'kill -9 $(lsof -t -i:{port})')
            time.sleep(1)
            return True
        except:
            return False

def test_drone_connection():
    print("드론 연결 테스트를 시작합니다...")
    
    # Clean up the Tello ports before connecting
    print("1. 포트 정리 중...")
    if cleanup_port(8889):
        print("✓ 포트 8889 정리 완료")
    else:
        print("❌ 포트 8889를 정리할 수 없습니다")
        print("컴퓨터를 재시작해주세요")
        return False
    
    time.sleep(1)
    tello = Tello()
    
    try:
        print("\n2. 드론에 연결 시도 중...")
        tello.connect()
        print("✓ 드론 연결 성공!")
        
        print("\n3. 드론 상태 확인 중...")
        print(f"✓ SDK 버전: {tello.get_sdk_version()}")
        print(f"✓ 시리얼 넘버: {tello.get_serial_number()}")
        print(f"✓ 배터리 잔량: {tello.get_battery()}%")
        print(f"✓ 드론 온도: {tello.get_temperature()}°C")
        
        print("\n모든 테스트가 성공적으로 완료되었습니다!")
        return True
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        print("\n문제 해결 방법:")
        print("1. 드론의 전원이 켜져 있는지 확인")
        print("2. WiFi가 'TELLO-XXXXXX'에 연결되어 있는지 확인")
        print("3. 드론과 충분히 가까운 거리에 있는지 확인")
        print("4. 드론을 재시작해보기")
        return False
        
    finally:
        tello.end()

if __name__ == "__main__":
    test_drone_connection() 