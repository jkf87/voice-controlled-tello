"""
DJI Tello 드론을 제어하기 위한 라이브러리.
이 라이브러리는 공식 Tello SDK를 기반으로 만들어졌습니다.
"""

# coding=utf-8
import logging
import socket
import time
from datetime import datetime
from collections import deque
from threading import Thread, Lock
from typing import Optional, Union, Type, Dict

from .enforce_types import enforce_types

import av
import numpy as np


threads_initialized = False
drones: Optional[dict] = {}
client_socket: socket.socket


class TelloException(Exception):
    """Tello 드론 관련 예외를 처리하기 위한 클래스"""
    pass


@enforce_types
class Tello:
    """
    Ryze Tello 드론을 제어하기 위한 Python 래퍼 클래스.
    공식 Tello SDK를 사용하여 드론과 통신합니다.
    
    주요 기능:
    - 기본적인 비행 제어 (이륙, 착륙, 이동, 회전)
    - 카메라 스트리밍
    - 상태 모니터링 (배터리, 높이, 속도 등)
    - 미션 패드 감지 (Tello EDU 전용)
    """
    # 통신 관련 상수
    RESPONSE_TIMEOUT = 7  # 응답 대기 시간 (초)
    TAKEOFF_TIMEOUT = 20  # 이륙 대기 시간 (초)
    FRAME_GRAB_TIMEOUT = 5  # 프레임 획득 타임아웃
    TIME_BTW_COMMANDS = 0.1  # 명령어 사이의 대기 시간 (초)
    TIME_BTW_RC_CONTROL_COMMANDS = 0.001  # RC 제어 명령어 사이의 대기 시간 (초)
    RETRY_COUNT = 3  # 실패한 명령어 재시도 횟수
    TELLO_IP = '192.168.10.1'  # Tello 드론의 IP 주소

    # 비디오 스트리밍 관련 상수
    VS_UDP_IP = '0.0.0.0'
    DEFAULT_VS_UDP_PORT = 11111
    VS_UDP_PORT = DEFAULT_VS_UDP_PORT

    # UDP 통신 포트
    CONTROL_UDP_PORT = 8889  # 제어 명령 포트
    STATE_UDP_PORT = 8890    # 상태 정보 포트

    # 비디오 설정 관련 상수
    BITRATE_AUTO = 0        # 자동 비트레이트
    BITRATE_1MBPS = 1       # 1Mbps
    BITRATE_2MBPS = 2       # 2Mbps
    BITRATE_3MBPS = 3       # 3Mbps
    BITRATE_4MBPS = 4       # 4Mbps
    BITRATE_5MBPS = 5       # 5Mbps
    RESOLUTION_480P = 'low'  # 480p 해상도
    RESOLUTION_720P = 'high' # 720p 해상도
    FPS_5 = 'low'           # 5fps
    FPS_15 = 'middle'       # 15fps
    FPS_30 = 'high'         # 30fps
    CAMERA_FORWARD = 0      # 전방 카메라
    CAMERA_DOWNWARD = 1     # 하방 카메라

    # Set up logger
    HANDLER = logging.StreamHandler()
    FORMATTER = logging.Formatter('[%(levelname)s] %(filename)s - %(lineno)d - %(message)s')
    HANDLER.setFormatter(FORMATTER)

    LOGGER = logging.getLogger('djitellopy')
    LOGGER.addHandler(HANDLER)
    LOGGER.setLevel(logging.INFO)
    # Use Tello.LOGGER.setLevel(logging.<LEVEL>) in YOUR CODE
    # to only receive logs of the desired level and higher

    # Conversion functions for state protocol fields
    INT_STATE_FIELDS = (
        # Tello EDU with mission pads enabled only
        'mid', 'x', 'y', 'z',
        # 'mpry': (custom format 'x,y,z')
        # Common entries
        'pitch', 'roll', 'yaw',
        'vgx', 'vgy', 'vgz',
        'templ', 'temph',
        'tof', 'h', 'bat', 'time'
    )
    FLOAT_STATE_FIELDS = ('baro', 'agx', 'agy', 'agz')

    state_field_converters: Dict[str, Union[Type[int], Type[float]]]
    state_field_converters = {key : int for key in INT_STATE_FIELDS}
    state_field_converters.update({key : float for key in FLOAT_STATE_FIELDS})

    # VideoCapture object
    background_frame_read: Optional['BackgroundFrameRead'] = None

    stream_on = False
    is_flying = False

    def __init__(self,
                 host=TELLO_IP,
                 retry_count=RETRY_COUNT,
                 vs_udp=VS_UDP_PORT):

        global threads_initialized, client_socket, drones

        self.address = (host, Tello.CONTROL_UDP_PORT)
        self.stream_on = False
        self.retry_count = retry_count
        self.last_received_command_timestamp = time.time()
        self.last_rc_control_timestamp = time.time()

        if not threads_initialized:
            # Run Tello command responses UDP receiver on background
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.bind(("", Tello.CONTROL_UDP_PORT))
            response_receiver_thread = Thread(target=Tello.udp_response_receiver)
            response_receiver_thread.daemon = True
            response_receiver_thread.start()

            # Run state UDP receiver on background
            state_receiver_thread = Thread(target=Tello.udp_state_receiver)
            state_receiver_thread.daemon = True
            state_receiver_thread.start()

            threads_initialized = True

        drones[host] = {'responses': [], 'state': {}}

        self.LOGGER.info("Tello instance was initialized. Host: '{}'. Port: '{}'.".format(host, Tello.CONTROL_UDP_PORT))

        self.vs_udp_port = vs_udp


    def change_vs_udp(self, udp_port):
        """Change the UDP Port for sending video feed from the drone.
        """
        self.vs_udp_port = udp_port
        self.send_control_command(f'port 8890 {self.vs_udp_port}')

    def get_own_udp_object(self):
        """Get own object from the global drones dict. This object is filled
        with responses and state information by the receiver threads.
        Internal method, you normally wouldn't call this yourself.
        """
        global drones

        host = self.address[0]
        return drones[host]

    @staticmethod
    def udp_response_receiver():
        """Setup drone UDP receiver. This method listens for responses of Tello.
        Must be run from a background thread in order to not block the main thread.
        Internal method, you normally wouldn't call this yourself.
        """
        while True:
            try:
                data, address = client_socket.recvfrom(1024)

                address = address[0]
                Tello.LOGGER.debug('Data received from {} at client_socket'.format(address))

                if address not in drones:
                    continue

                drones[address]['responses'].append(data)

            except Exception as e:
                Tello.LOGGER.error(e)
                break

    @staticmethod
    def udp_state_receiver():
        """Setup state UDP receiver. This method listens for state information from
        Tello. Must be run from a background thread in order to not block
        the main thread.
        Internal method, you normally wouldn't call this yourself.
        """
        state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        state_socket.bind(("", Tello.STATE_UDP_PORT))

        while True:
            try:
                data, address = state_socket.recvfrom(1024)

                address = address[0]
                Tello.LOGGER.debug('Data received from {} at state_socket'.format(address))

                if address not in drones:
                    continue

                data = data.decode('ASCII')
                data = Tello.parse_state(data)
                data['received_at'] = datetime.now()
                drones[address]['state'] = data

            except Exception as e:
                Tello.LOGGER.error(e)
                break

    @staticmethod
    def parse_state(state: str) -> Dict[str, Union[int, float, str]]:
        """Parse a state line to a dictionary
        Internal method, you normally wouldn't call this yourself.
        """
        state = state.strip()
        Tello.LOGGER.debug('Raw state data: {}'.format(state))

        if state == 'ok':
            return {}

        state_dict = {}
        for field in state.split(';'):
            split = field.split(':')
            if len(split) < 2:
                continue

            key = split[0]
            value: Union[int, float, str] = split[1]

            if key in Tello.state_field_converters:
                num_type = Tello.state_field_converters[key]
                try:
                    value = num_type(value)
                except ValueError as e:
                    Tello.LOGGER.debug('Error parsing state value for {}: {} to {}'
                                       .format(key, value, num_type))
                    Tello.LOGGER.error(e)
                    continue

            state_dict[key] = value

        return state_dict

    def get_current_state(self) -> dict:
        """Call this function to attain the state of the Tello. Returns a dict
        with all fields.
        Internal method, you normally wouldn't call this yourself.
        """
        return self.get_own_udp_object()['state']

    def get_state_field(self, key: str):
        """Get a specific sate field by name.
        Internal method, you normally wouldn't call this yourself.
        """
        state = self.get_current_state()

        if key in state:
            return state[key]
        else:
            raise TelloException('Could not get state property: {}'.format(key))

    def get_last_state_update(self) -> datetime:
        """Get the datetime of when the last state packet was received.
        You may use this function to check the age of values returned by all other get_* functions.
        Returns:
            datetime: last state update
        """
        return self.get_state_field('received_at')

    def get_mission_pad_id(self) -> int:
        """Mission pad ID of the currently detected mission pad
        Only available on Tello EDUs after calling enable_mission_pads
        Returns:
            int: -1 if none is detected, else 1-8
        """
        return self.get_state_field('mid')

    def get_mission_pad_distance_x(self) -> int:
        """X distance to current mission pad
        Only available on Tello EDUs after calling enable_mission_pads
        Returns:
            int: distance in cm
        """
        return self.get_state_field('x')

    def get_mission_pad_distance_y(self) -> int:
        """Y distance to current mission pad
        Only available on Tello EDUs after calling enable_mission_pads
        Returns:
            int: distance in cm
        """
        return self.get_state_field('y')

    def get_mission_pad_distance_z(self) -> int:
        """Z distance to current mission pad
        Only available on Tello EDUs after calling enable_mission_pads
        Returns:
            int: distance in cm
        """
        return self.get_state_field('z')

    def get_pitch(self) -> int:
        """Get pitch in degree
        Returns:
            int: pitch in degree
        """
        return self.get_state_field('pitch')

    def get_roll(self) -> int:
        """Get roll in degree
        Returns:
            int: roll in degree
        """
        return self.get_state_field('roll')

    def get_yaw(self) -> int:
        """Get yaw in degree
        Returns:
            int: yaw in degree
        """
        return self.get_state_field('yaw')

    def get_speed_x(self) -> int:
        """X-Axis Speed
        Returns:
            int: speed
        """
        return self.get_state_field('vgx')

    def get_speed_y(self) -> int:
        """Y-Axis Speed
        Returns:
            int: speed
        """
        return self.get_state_field('vgy')

    def get_speed_z(self) -> int:
        """Z-Axis Speed
        Returns:
            int: speed
        """
        return self.get_state_field('vgz')

    def get_acceleration_x(self) -> float:
        """X-Axis Acceleration
        Returns:
            float: acceleration
        """
        return self.get_state_field('agx')

    def get_acceleration_y(self) -> float:
        """Y-Axis Acceleration
        Returns:
            float: acceleration
        """
        return self.get_state_field('agy')

    def get_acceleration_z(self) -> float:
        """Z-Axis Acceleration
        Returns:
            float: acceleration
        """
        return self.get_state_field('agz')

    def get_lowest_temperature(self) -> int:
        """
        드론의 최저 온도를 반환합니다.
        
        반환값:
            int: 최저 온도 (°C)
        """
        return self.get_state_field('templ')

    def get_highest_temperature(self) -> int:
        """
        드론의 최고 온도를 반환합니다.
        
        반환값:
            float: 최고 온도 (°C)
        """
        return self.get_state_field('temph')

    def get_temperature(self) -> float:
        """
        현재 드론의 평균 온도를 반환합니다.
        
        반환값:
            float: 온도 (°C)
        """
        templ = self.get_lowest_temperature()
        temph = self.get_highest_temperature()
        return (templ + temph) / 2

    def get_height(self) -> int:
        """
        현재 높이를 반환합니다.
        
        반환값:
            int: 높이 (cm)
        """
        return self.get_state_field('h')

    def get_distance_tof(self) -> int:
        """
        TOF(Time of Flight) 센서로 측정한 현재 거리를 반환합니다.
        
        반환값:
            int: TOF 거리 (cm)
        """
        return self.get_state_field('tof')

    def get_barometer(self) -> int:
        """
        현재 기압계 측정값을 반환합니다.
        절대 고도를 나타냅니다.
        
        반환값:
            int: 기압계 측정값 (cm)
        """
        return self.get_state_field('baro') * 100

    def get_flight_time(self) -> int:
        """
        모터가 작동한 시간을 반환합니다.
        
        반환값:
            int: 비행 시간 (초)
        """
        return self.get_state_field('time')

    def get_battery(self) -> int:
        """
        현재 배터리 잔량을 반환합니다.
        
        반환값:
            int: 배터리 잔량 (0-100%)
        """
        return self.get_state_field('bat')

    def get_udp_video_address(self) -> str:
        """
        비디오 스트리밍을 위한 UDP 주소를 반환합니다.
        내부 메서드로, 직접 호출할 필요는 없습니다.
        """
        address_schema = 'udp://@{ip}:{port}'
        address = address_schema.format(ip=self.VS_UDP_IP, port=self.vs_udp_port)
        return address

    def get_frame_read(self, with_queue = False, max_queue_len = 32) -> 'BackgroundFrameRead':
        """Get the BackgroundFrameRead object from the camera drone. Then, you just need to call
        backgroundFrameRead.frame to get the actual frame received by the drone.
        Returns:
            BackgroundFrameRead
        """
        if self.background_frame_read is None:
            address = self.get_udp_video_address()
            self.background_frame_read = BackgroundFrameRead(self, address, with_queue, max_queue_len)
            self.background_frame_read.start()
        return self.background_frame_read

    def send_command_with_return(self, command: str, timeout: int = RESPONSE_TIMEOUT) -> str:
        """Send command to Tello and wait for its response.
        Internal method, you normally wouldn't call this yourself.
        Return:
            bool/str: str with response text on success, False when unsuccessfull.
        """
        # Commands very consecutive makes the drone not respond to them.
        # So wait at least self.TIME_BTW_COMMANDS seconds
        diff = time.time() - self.last_received_command_timestamp
        if diff < self.TIME_BTW_COMMANDS:
            self.LOGGER.debug('Waiting {} seconds to execute command: {}...'.format(diff, command))
            time.sleep(diff)

        self.LOGGER.info("Send command: '{}'".format(command))
        timestamp = time.time()

        client_socket.sendto(command.encode('utf-8'), self.address)

        responses = self.get_own_udp_object()['responses']

        while not responses:
            if time.time() - timestamp > timeout:
                message = "Aborting command '{}'. Did not receive a response after {} seconds".format(command, timeout)
                self.LOGGER.warning(message)
                return message
            time.sleep(0.1)  # Sleep during send command

        self.last_received_command_timestamp = time.time()

        first_response = responses.pop(0)  # first datum from socket
        try:
            response = first_response.decode("utf-8")
        except UnicodeDecodeError as e:
            self.LOGGER.error(e)
            return "response decode error"
        response = response.rstrip("\r\n")

        self.LOGGER.info("Response {}: '{}'".format(command, response))
        return response

    def send_command_without_return(self, command: str):
        """Send command to Tello without expecting a response.
        Internal method, you normally wouldn't call this yourself.
        """
        # Commands very consecutive makes the drone not respond to them. So wait at least self.TIME_BTW_COMMANDS seconds

        self.LOGGER.info("Send command (no response expected): '{}'".format(command))
        client_socket.sendto(command.encode('utf-8'), self.address)

    def send_control_command(self, command: str, timeout: int = RESPONSE_TIMEOUT) -> bool:
        """Send control command to Tello and wait for its response.
        Internal method, you normally wouldn't call this yourself.
        """
        response = "max retries exceeded"
        for i in range(0, self.retry_count):
            response = self.send_command_with_return(command, timeout=timeout)

            if 'ok' in response.lower():
                return True

            self.LOGGER.debug("Command attempt #{} failed for command: '{}'".format(i, command))

        self.raise_result_error(command, response)
        return False # never reached

    def send_read_command(self, command: str) -> str:
        """Send given command to Tello and wait for its response.
        Internal method, you normally wouldn't call this yourself.
        """

        response = self.send_command_with_return(command)

        try:
            response = str(response)
        except TypeError as e:
            self.LOGGER.error(e)

        if any(word in response for word in ('error', 'ERROR', 'False')):
            self.raise_result_error(command, response)
            return "Error: this code should never be reached"

        return response

    def send_read_command_int(self, command: str) -> int:
        """Send given command to Tello and wait for its response.
        Parses the response to an integer
        Internal method, you normally wouldn't call this yourself.
        """
        response = self.send_read_command(command)
        return int(response)

    def send_read_command_float(self, command: str) -> float:
        """Send given command to Tello and wait for its response.
        Parses the response to an integer
        Internal method, you normally wouldn't call this yourself.
        """
        response = self.send_read_command(command)
        return float(response)

    def raise_result_error(self, command: str, response: str) -> bool:
        """Used to reaise an error after an unsuccessful command
        Internal method, you normally wouldn't call this yourself.
        """
        tries = 1 + self.retry_count
        raise TelloException("Command '{}' was unsuccessful for {} tries. Latest response:\t'{}'"
                             .format(command, tries, response))

    def connect(self, wait_for_state=True):
        """
        SDK 모드로 진입합니다. 다른 제어 함수를 사용하기 전에 반드시 호출해야 합니다.
        
        매개변수:
            wait_for_state (bool): 상태 패킷을 기다릴지 여부
        """
        self.send_control_command("command")

        if wait_for_state:
            REPS = 20
            for i in range(REPS):
                if self.get_current_state():
                    t = i / REPS
                    Tello.LOGGER.debug("'.connect()' 첫 상태 패킷 수신 ({}초 후)".format(t))
                    break
                time.sleep(1 / REPS)

            if not self.get_current_state():
                raise TelloException('Tello로부터 상태 패킷을 받지 못했습니다')

    def send_keepalive(self):
        """
        15초 후 자동 착륙을 방지하기 위한 keepalive 패킷을 전송합니다.
        """
        self.send_control_command("keepalive")

    def turn_motor_on(self):
        """
        비행하지 않고 모터만 켭니다 (주로 냉각 목적).
        """
        self.send_control_command("motoron")

    def turn_motor_off(self):
        """
        모터 냉각 모드를 종료합니다.
        """
        self.send_control_command("motoroff")

    def initiate_throw_takeoff(self):
        """
        드론을 던져서 이륙하는 모드를 활성화합니다.
        명령 후 5초 이내에 드론을 던져야 합니다.
        """
        self.send_control_command("throwfly")
        self.is_flying = True

    def takeoff(self):
        """
        자동 이륙을 수행합니다.
        이륙이 완료될 때까지 대기합니다.
        """
        self.send_control_command("takeoff", timeout=Tello.TAKEOFF_TIMEOUT)
        self.is_flying = True

    def land(self):
        """
        자동 착륙을 수행합니다.
        """
        self.send_control_command("land")
        self.is_flying = False

    def streamon(self):
        """
        비디오 스트리밍을 시작합니다.
        이후 tello.get_frame_read()를 사용하여 프레임을 받을 수 있습니다.
        """
        if self.DEFAULT_VS_UDP_PORT != self.vs_udp_port:
            self.change_vs_udp(self.vs_udp_port)
        self.send_control_command("streamon")
        self.stream_on = True

    def streamoff(self):
        """
        비디오 스트리밍을 종료합니다.
        """
        self.send_control_command("streamoff")
        self.stream_on = False

        if self.background_frame_read is not None:
            self.background_frame_read.stop()
            self.background_frame_read = None

    def emergency(self):
        """
        비상 정지: 모든 모터를 즉시 정지시킵니다.
        긴급 상황에서만 사용하세요!
        """
        self.send_command_without_return("emergency")
        self.is_flying = False

    def move(self, direction: str, x: int):
        """
        지정된 방향으로 x cm만큼 이동합니다.
        
        매개변수:
            direction: 이동 방향 (up, down, left, right, forward, back)
            x: 이동 거리 (20-500cm)
        """
        self.send_control_command("{} {}".format(direction, x))

    def move_up(self, x: int):
        """
        위로 x cm 이동합니다.
        
        매개변수:
            x: 이동 거리 (20-500cm)
        """
        self.move("up", x)

    def move_down(self, x: int):
        """
        아래로 x cm 이동합니다.
        
        매개변수:
            x: 이동 거리 (20-500cm)
        """
        self.move("down", x)

    def move_left(self, x: int):
        """
        왼쪽으로 x cm 이동합니다.
        
        매개변수:
            x: 이동 거리 (20-500cm)
        """
        self.move("left", x)

    def move_right(self, x: int):
        """
        오른쪽으로 x cm 이동합니다.
        
        매개변수:
            x: 이동 거리 (20-500cm)
        """
        self.move("right", x)

    def move_forward(self, x: int):
        """
        앞으로 x cm 이동합니다.
        
        매개변수:
            x: 이동 거리 (20-500cm)
        """
        self.move("forward", x)

    def move_back(self, x: int):
        """
        뒤로 x cm 이동합니다.
        
        매개변수:
            x: 이동 거리 (20-500cm)
        """
        self.move("back", x)

    def rotate_clockwise(self, x: int):
        """
        시계 방향으로 x도 회전합니다.
        
        매개변수:
            x: 회전 각도 (1-360도)
        """
        self.send_control_command("cw {}".format(x))

    def rotate_counter_clockwise(self, x: int):
        """
        반시계 방향으로 x도 회전합니다.
        
        매개변수:
            x: 회전 각도 (1-360도)
        """
        self.send_control_command("ccw {}".format(x))

    def flip(self, direction: str):
        """
        지정된 방향으로 플립(공중제비) 동작을 수행합니다.
        일반적으로 flip_x 함수들을 대신 사용합니다.
        
        매개변수:
            direction: l (왼쪽), r (오른쪽), f (앞쪽) 또는 b (뒤쪽)
        """
        self.send_control_command("flip {}".format(direction))

    def flip_left(self):
        """
        왼쪽으로 플립(공중제비) 동작을 수행합니다.
        """
        self.flip("l")

    def flip_right(self):
        """
        오른쪽으로 플립(공중제비) 동작을 수행합니다.
        """
        self.flip("r")

    def flip_forward(self):
        """
        앞으로 플립(공중제비) 동작을 수행합니다.
        """
        self.flip("f")

    def flip_back(self):
        """
        뒤로 플립(공중제비) 동작을 수행합니다.
        """
        self.flip("b")

    def go_xyz_speed(self, x: int, y: int, z: int, speed: int):
        """
        현재 위치를 기준으로 x, y, z 좌표로 이동합니다.
        speed로 이동 속도를 지정합니다.
        
        매개변수:
            x: x축 이동 거리 (-500~500cm)
            y: y축 이동 거리 (-500~500cm)
            z: z축 이동 거리 (-500~500cm)
            speed: 이동 속도 (10-100cm/s)
        """
        cmd = 'go {} {} {} {}'.format(x, y, z, speed)
        self.send_control_command(cmd)

    def stop(self):
        """
        드론을 현재 위치에서 정지(호버링)시킵니다.
        언제든지 사용 가능합니다.
        """
        self.send_control_command("stop")

    def curve_xyz_speed(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int):
        """Fly to x2 y2 z2 in a curve via x1 y1 z1. Speed defines the traveling speed in cm/s.

        - Both points are relative to the current position
        - The current position and both points must form a circle arc.
        - If the arc radius is not within the range of 0.5-10 meters, it raises an Exception
        - x1/x2, y1/y2, z1/z2 can't both be between -20-20 at the same time, but can both be 0.

        Arguments:
            x1: -500-500
            x2: -500-500
            y1: -500-500
            y2: -500-500
            z1: -500-500
            z2: -500-500
            speed: 10-60
        """
        cmd = 'curve {} {} {} {} {} {} {}'.format(x1, y1, z1, x2, y2, z2, speed)
        self.send_control_command(cmd)

    def go_xyz_speed_mid(self, x: int, y: int, z: int, speed: int, mid: int):
        """Fly to x y z relative to the mission pad with id mid.
        Speed defines the traveling speed in cm/s.
        Arguments:
            x: -500-500
            y: -500-500
            z: -500-500
            speed: 10-100
            mid: 1-8
        """
        cmd = 'go {} {} {} {} m{}'.format(x, y, z, speed, mid)
        self.send_control_command(cmd)

    def curve_xyz_speed_mid(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int, mid: int):
        """Fly to x2 y2 z2 in a curve via x1 y1 z1. Speed defines the traveling speed in cm/s.

        - Both points are relative to the mission pad with id mid.
        - The current position and both points must form a circle arc.
        - If the arc radius is not within the range of 0.5-10 meters, it raises an Exception
        - x1/x2, y1/y2, z1/z2 can't both be between -20-20 at the same time, but can both be 0.

        Arguments:
            x1: -500-500
            y1: -500-500
            z1: -500-500
            x2: -500-500
            y2: -500-500
            z2: -500-500
            speed: 10-60
            mid: 1-8
        """
        cmd = 'curve {} {} {} {} {} {} {} m{}'.format(x1, y1, z1, x2, y2, z2, speed, mid)
        self.send_control_command(cmd)

    def go_xyz_speed_yaw_mid(self, x: int, y: int, z: int, speed: int, yaw: int, mid1: int, mid2: int):
        """Fly to x y z relative to mid1.
        Then fly to 0 0 z over mid2 and rotate to yaw relative to mid2's rotation.
        Speed defines the traveling speed in cm/s.
        Arguments:
            x: -500-500
            y: -500-500
            z: -500-500
            speed: 10-100
            yaw: -360-360
            mid1: 1-8
            mid2: 1-8
        """
        cmd = 'jump {} {} {} {} {} m{} m{}'.format(x, y, z, speed, yaw, mid1, mid2)
        self.send_control_command(cmd)

    def enable_mission_pads(self):
        """Enable mission pad detection
        """
        self.send_control_command("mon")

    def disable_mission_pads(self):
        """Disable mission pad detection
        """
        self.send_control_command("moff")

    def set_mission_pad_detection_direction(self, x):
        """Set mission pad detection direction. enable_mission_pads needs to be
        called first. When detecting both directions detecting frequency is 10Hz,
        otherwise the detection frequency is 20Hz.
        Arguments:
            x: 0 downwards only, 1 forwards only, 2 both directions
        """
        self.send_control_command("mdirection {}".format(x))

    def set_speed(self, x: int):
        """
        드론의 이동 속도를 설정합니다.
        
        매개변수:
            x: 속도 (10-100cm/s)
        """
        self.send_control_command("speed {}".format(x))

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int,
                        yaw_velocity: int):
        """Send RC control via four channels. Command is sent every self.TIME_BTW_RC_CONTROL_COMMANDS seconds.
        Arguments:
            left_right_velocity: -100~100 (left/right)
            forward_backward_velocity: -100~100 (forward/backward)
            up_down_velocity: -100~100 (up/down)
            yaw_velocity: -100~100 (yaw)
        """
        def clamp100(x: int) -> int:
            return max(-100, min(100, x))

        if time.time() - self.last_rc_control_timestamp > self.TIME_BTW_RC_CONTROL_COMMANDS:
            self.last_rc_control_timestamp = time.time()
            cmd = 'rc {} {} {} {}'.format(
                clamp100(left_right_velocity),
                clamp100(forward_backward_velocity),
                clamp100(up_down_velocity),
                clamp100(yaw_velocity)
            )
            self.send_command_without_return(cmd)

    def set_wifi_credentials(self, ssid: str, password: str):
        """
        드론의 WiFi SSID와 비밀번호를 설정합니다.
        설정 후 드론이 재부팅됩니다.
        
        매개변수:
            ssid: WiFi 네트워크 이름
            password: WiFi 비밀번호
        """
        cmd = 'wifi {} {}'.format(ssid, password)
        self.send_control_command(cmd)

    def connect_to_wifi(self, ssid: str, password: str):
        """WiFi에 SSID와 비밀번호로 연결합니다.
        이 명령어 실행 후 텔로가 재부팅됩니다.
        Tello EDU 모델에서만 작동합니다.
        """
        cmd = 'ap {} {}'.format(ssid, password)
        self.send_control_command(cmd)

    def set_network_ports(self, state_packet_port: int, video_stream_port: int):
        """상태 패킷과 비디오 스트리밍을 위한 포트를 설정합니다.
        이 명령어로 텔로를 재구성할 수 있지만 현재 이 라이브러리는
        기본 포트가 아닌 포트는 지원하지 않습니다 (TODO!)
        """
        cmd = 'port {} {}'.format(state_packet_port, video_stream_port)
        self.send_control_command(cmd)

    def reboot(self):
        """드론을 재부팅합니다
        """
        self.send_command_without_return('reboot')

    def set_video_bitrate(self, bitrate: int):
        """비디오 스트림의 비트레이트를 설정합니다
        비트레이트 인자로 다음 중 하나를 사용하세요:
            Tello.BITRATE_AUTO
            Tello.BITRATE_1MBPS
            Tello.BITRATE_2MBPS
            Tello.BITRATE_3MBPS
            Tello.BITRATE_4MBPS
            Tello.BITRATE_5MBPS
        """
        cmd = 'setbitrate {}'.format(bitrate)
        self.send_control_command(cmd)

    def set_video_resolution(self, resolution: str):
        """비디오 스트림의 해상도를 설정합니다
        해상도 인자로 다음 중 하나를 사용하세요:
            Tello.RESOLUTION_480P
            Tello.RESOLUTION_720P
        """
        cmd = 'setresolution {}'.format(resolution)
        self.send_control_command(cmd)

    def set_video_fps(self, fps: str):
        """비디오 스트림의 초당 프레임 수를 설정합니다
        fps 인자로 다음 중 하나를 사용하세요:
            Tello.FPS_5
            Tello.FPS_15
            Tello.FPS_30
        """
        cmd = 'setfps {}'.format(fps)
        self.send_control_command(cmd)

    def set_video_direction(self, direction: int):
        """비디오 스트리밍을 위한 두 카메라 중 하나를 선택합니다
        전방 카메라는 일반 1080x720 컬러 카메라입니다
        하방 카메라는 320x240 흑백 IR 감지 카메라입니다
        방향 인자로 다음 중 하나를 사용하세요:
            Tello.CAMERA_FORWARD
            Tello.CAMERA_DOWNWARD
        """
        cmd = 'downvision {}'.format(direction)
        self.send_control_command(cmd)

    def send_expansion_command(self, expansion_cmd: str):
        """Tello Talent에 연결된 ESP32 확장 보드로 명령을 전송합니다
        예: tello.send_expansion_command("led 255 0 0")로 상단 LED를 빨간색으로 설정
        """
        cmd = 'EXT {}'.format(expansion_cmd)
        self.send_control_command(cmd)

    def query_speed(self) -> int:
        """속도 설정을 조회합니다 (cm/s)
        반환값:
            int: 1-100
        """
        return self.send_read_command_int('speed?')

    def query_battery(self) -> int:
        """쿼리 명령을 통해 현재 배터리 잔량을 가져옵니다
        get_battery를 사용하는 것이 일반적으로 더 빠릅니다
        반환값:
            int: 0-100 (%)
        """
        return self.send_read_command_int('battery?')

    def query_flight_time(self) -> int:
        """현재 비행 시간을 조회합니다 (초).
        get_flight_time을 사용하는 것이 일반적으로 더 빠릅니다.
        반환값:
            int: 비행 중 경과된 시간(초).
        """
        return self.send_read_command_int('time?')

    def query_height(self) -> int:
        """쿼리 명령을 통해 높이를 cm 단위로 가져옵니다.
        get_height를 사용하는 것이 일반적으로 더 빠릅니다
        반환값:
            int: 0-3000
        """
        return self.send_read_command_int('height?')

    def query_temperature(self) -> int:
        """온도를 조회합니다 (°C).
        get_temperature를 사용하는 것이 일반적으로 더 빠릅니다.
        반환값:
            int: 0-90
        """
        return self.send_read_command_int('temp?')

    def query_attitude(self) -> dict:
        """IMU 자세 데이터를 조회합니다.
        get_pitch, get_roll, get_yaw를 사용하는 것이 일반적으로 더 빠릅니다.
        반환값:
            {'pitch': int, 'roll': int, 'yaw': int}
        """
        response = self.send_read_command('attitude?')
        return Tello.parse_state(response)

    def query_barometer(self) -> int:
        """기압계 값을 가져옵니다 (cm)
        get_barometer를 사용하는 것이 일반적으로 더 빠릅니다.
        반환값:
            int: 0-100
        """
        baro = self.send_read_command_int('baro?')
        return baro * 100

    def query_distance_tof(self) -> float:
        """TOF 센서로부터 거리 값을 가져옵니다 (cm)
        get_distance_tof를 사용하는 것이 일반적으로 더 빠릅니다.
        반환값:
            float: 30-1000
        """
        # 응답 예시: 801mm
        tof = self.send_read_command('tof?')
        return int(tof[:-2]) / 10

    def query_wifi_signal_noise_ratio(self) -> str:
        """Wi-Fi SNR을 가져옵니다
        반환값:
            str: snr
        """
        return self.send_read_command('wifi?')

    def query_sdk_version(self) -> str:
        """SDK 버전을 가져옵니다
        반환값:
            str: SDK 버전
        """
        return self.send_read_command('sdk?')

    def query_serial_number(self) -> str:
        """시리얼 번호를 가져옵니다
        반환값:
            str: 시리얼 번호
        """
        return self.send_read_command('sn?')

    def query_active(self) -> str:
        """활성 상태를 가져옵니다
        반환값:
            str
        """
        return self.send_read_command('active?')

    def end(self):
        """
        드론과의 연결을 안전하게 종료합니다.
        프로그램 종료 전에 반드시 호출해야 합니다.
        """
        try:
            if self.is_flying:
                self.land()
            if self.stream_on:
                self.streamoff()
        except TelloException:
            pass

        if self.background_frame_read is not None:
            self.background_frame_read.stop()
            self.background_frame_read = None

        host = self.address[0]
        if host in drones:
            del drones[host]

    def __del__(self):
        self.end()


class BackgroundFrameRead:
    """
    이 클래스는 백그라운드에서 PyAV를 사용하여 프레임을 읽습니다.
    현재 프레임을 가져오려면 backgroundFrameRead.frame을 사용하세요.
    """

    def __init__(self, tello, address, with_queue = False, maxsize = 32):
        self.address = address
        self.lock = Lock()
        self.frame = np.zeros([300, 400, 3], dtype=np.uint8)
        self.frames = deque([], maxsize)
        self.with_queue = with_queue

        # PyAV로 프레임 가져오기 시도
        # 이슈 #90에 따르면 디코더가 시간이 필요할 수 있음
        # https://github.com/damiafuentes/DJITelloPy/issues/90#issuecomment-855458905
        try:
            Tello.LOGGER.debug('비디오 프레임 가져오기 시도 중...')
            self.container = av.open(self.address, timeout=(Tello.FRAME_GRAB_TIMEOUT, None))
        except av.error.ExitError:
            raise TelloException('비디오 스트림에서 비디오 프레임을 가져오는데 실패했습니다')

        self.stopped = False
        self.worker = Thread(target=self.update_frame, args=(), daemon=True)

    def start(self):
        """프레임 업데이트 워커를 시작합니다
        내부 메서드로, 일반적으로 직접 호출하지 않습니다.
        """
        self.worker.start()

    def update_frame(self):
        """PyAV를 사용하여 프레임을 가져오는 스레드 워커 함수
        내부 메서드로, 일반적으로 직접 호출하지 않습니다.
        """
        try:
            for frame in self.container.decode(video=0):
                if self.with_queue:
                    self.frames.append(np.array(frame.to_image()))
                else:
                    self.frame = np.array(frame.to_image())

                if self.stopped:
                    self.container.close()
                    break
        except av.error.ExitError:
            raise TelloException('디코딩을 위한 충분한 프레임이 없습니다. 다시 시도하거나 get_frame_read() 전에 비디오 fps를 높이세요')
    
    def get_queued_frame(self):
        """
        큐에서 프레임을 가져옵니다
        """
        with self.lock:
            try:
                return self.frames.popleft()
            except IndexError:
                return None

    @property
    def frame(self):
        """
        frame 변수에 직접 접근
        """
        if self.with_queue:
            return self.get_queued_frame()

        with self.lock:
            return self._frame

    @frame.setter
    def frame(self, value):
        with self.lock:
            self._frame = value

    def stop(self):
        """프레임 업데이트 워커를 중지합니다
        내부 메서드로, 일반적으로 직접 호출하지 않습니다.
        """
        self.stopped = True
