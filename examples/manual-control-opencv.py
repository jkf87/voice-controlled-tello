# 키보드를 사용하여 Tello를 제어하는 간단한 예제입니다.
# 더 많은 기능이 포함된 예제는 manual-control-pygame.py를 참조하세요.
#
# W, A, S, D 키로 이동하고, E, Q 키로 회전하며, R, F 키로 상승 및 하강합니다.
# 스크립트 시작 시 Tello가 이륙하며, ESC 키를 누르면 착륙하고
# 프로그램이 종료됩니다.

from djitellopy import Tello
import cv2, math, time

tello = Tello()
tello.connect()

tello.streamon()
frame_read = tello.get_frame_read()

tello.takeoff()

while True:
    # 실제로는 별도의 스레드에서 프레임을 표시해야 합니다. 그렇지 않으면
    # 드론이 이동하는 동안 화면이 정지됩니다.
    img = frame_read.frame
    cv2.imshow("drone", img)

    key = cv2.waitKey(1) & 0xff
    if key == 27: # ESC
        break
    elif key == ord('w'):
        tello.move_forward(30)
    elif key == ord('s'):
        tello.move_back(30)
    elif key == ord('a'):
        tello.move_left(30)
    elif key == ord('d'):
        tello.move_right(30)
    elif key == ord('e'):
        tello.rotate_clockwise(30)
    elif key == ord('q'):
        tello.rotate_counter_clockwise(30)
    elif key == ord('r'):
        tello.move_up(30)
    elif key == ord('f'):
        tello.move_down(30)

tello.land()
