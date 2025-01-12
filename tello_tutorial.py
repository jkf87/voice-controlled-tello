"""
# Tello 드론 실습 가이드

이 스크립트는 DJI Tello 드론의 기본적인 조작과 프로그래밍을 실습하기 위한 가이드입니다.
각 섹션의 코드를 순차적으로 실행하면서 드론의 기능을 테스트할 수 있습니다.
"""

# 1. 필요한 라이브러리 설치
# !pip install djitellopy opencv-python

# 2. 드론 연결 테스트
def test_connection():
    from djitellopy import Tello
    
    # Tello 객체 생성
    tello = Tello()
    
    # 드론에 연결
    tello.connect()
    
    # 배터리 잔량 확인
    battery = tello.get_battery()
    print(f"배터리 잔량: {battery}%")
    
    # SDK 버전 확인
    sdk = tello.get_sdk_version()
    print(f"SDK 버전: {sdk}")
    
    return tello

# # 3. 기본 비행 명령어
# def basic_flight(tello):
#     """
#     ⚠️ 주의: 이 함수를 실행하기 전에 충분한 공간이 확보되어 있는지 확인하세요.
#     """
#     # 이륙
#     tello.takeoff()
    
#     # 위로 50cm 이동
#     tello.move_up(50)
    
#     # 정사각형 패턴 비행
#     for _ in range(4):
#         tello.move_forward(50)
#         tello.rotate_clockwise(90)
    
#     # 착륙
#     tello.land()

# # 4. 상태 모니터링
# def monitor_status(tello):
#     # 현재 높이
#     height = tello.get_height()
#     print(f"현재 높이: {height}cm")
    
#     # 비행 시간
#     flight_time = tello.get_flight_time()
#     print(f"비행 시간: {flight_time}초")
    
#     # 온도
#     temp = tello.get_temperature()
#     print(f"온도: {temp}°C")
    
#     # 기압
#     barometer = tello.get_barometer()
#     print(f"기압: {barometer}cm")

# # 5. 카메라 제어
# def camera_control(tello):
#     import cv2
    
#     # 비디오 스트림 시작
#     tello.streamon()
    
#     # 프레임 읽기
#     frame = tello.get_frame_read().frame
    
#     # 사진 저장
#     cv2.imwrite('tello_photo.jpg', frame)
    
#     # 비디오 스트림 종료
#     tello.streamoff()
    
#     print("사진이 'tello_photo.jpg'로 저장되었습니다.")

# # 6. 실시간 비디오 스트림
# def video_stream(tello):
#     import cv2
#     import time
    
#     # 비디오 스트림 시작
#     tello.streamon()
#     frame_read = tello.get_frame_read()
    
#     try:
#         while True:
#             # 프레임 읽기
#             frame = frame_read.frame
            
#             # 프레임 표시
#             cv2.imshow("Tello Camera", frame)
            
#             # 'q' 키를 누르면 종료
#             if cv2.waitKey(1) & 0xFF == ord('q'):
#                 break
                
#             time.sleep(1/30)  # FPS 제한
            
#     finally:
#         # 정리
#         cv2.destroyAllWindows()
#         tello.streamoff()

def main():
    # 드론 연결
    tello = test_connection()
    
    # 메뉴 출력
    while True:
        print("\n=== Tello 드론 제어 메뉴 ===")
        print("1. 상태 모니터링")
        print("2. 기본 비행 테스트")
        print("3. 사진 촬영")
        print("4. 실시간 비디오 스트림")
        print("5. 종료")
        
        choice = input("원하는 기능의 번호를 입력하세요: ")
        
        if choice == "1":
            monitor_status(tello)
        elif choice == "2":
            print("⚠️ 주의: 충분한 공간이 확보되어 있는지 확인하세요.")
            input("계속하려면 Enter를 누르세요...")
            basic_flight(tello)
        elif choice == "3":
            camera_control(tello)
        elif choice == "4":
            video_stream(tello)
        elif choice == "5":
            print("프로그램을 종료합니다.")
            tello.end()
            break
        else:
            print("잘못된 입력입니다. 다시 시도해주세요.")

if __name__ == "__main__":
    main() 