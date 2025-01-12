"""여러 대의 DJI Ryze Tello 드론을 제어하기 위한 라이브러리.
Library for controlling multiple DJI Ryze Tello drones.
"""

from threading import Thread, Barrier
from queue import Queue
from typing import List, Callable

from .tello import Tello, TelloException
from .enforce_types import enforce_types


@enforce_types
class TelloSwarm:
    """여러 대의 Tello를 동시에 제어하기 위한 스웜 라이브러리
    Swarm library for controlling multiple Tellos simultaneously
    """

    tellos: List[Tello]
    barrier: Barrier
    funcBarier: Barrier
    funcQueues: List[Queue]
    threads: List[Thread]

    @staticmethod
    def fromFile(path: str):
        """파일에서 TelloSwarm을 생성합니다. 파일은 한 줄당 하나의 IP 주소를 포함해야 합니다.
        Create TelloSwarm from file. The file should contain one IP address per line.

        Arguments:
            path: 파일 경로 / path to the file
        """
        with open(path, 'r') as fd:
            ips = fd.readlines()

        return TelloSwarm.fromIps(ips)

    @staticmethod
    def fromIps(ips: list):
        """IP 주소 목록에서 TelloSwarm을 생성합니다.
        Create TelloSwarm from a list of IP addresses.

        Arguments:
            ips: IP 주소 목록 / list of IP Addresses
        """
        if not ips:
            raise TelloException("No ips provided")

        tellos = []
        for ip in ips:
            tellos.append(Tello(ip.strip()))

        return TelloSwarm(tellos)

    def __init__(self, tellos: List[Tello]):
        """TelloSwarm 인스턴스를 초기화합니다.
        Initialize a TelloSwarm instance

        Arguments:
            tellos: [Tello][tello] 인스턴스 목록 / list of [Tello][tello] instances
        """
        self.tellos = tellos
        self.barrier = Barrier(len(tellos))
        self.funcBarrier = Barrier(len(tellos) + 1)
        self.funcQueues = [Queue() for tello in tellos]

        def worker(i):
            queue = self.funcQueues[i]
            tello = self.tellos[i]

            while True:
                func = queue.get()
                self.funcBarrier.wait()
                func(i, tello)
                self.funcBarrier.wait()

        self.threads = []
        for i, _ in enumerate(tellos):
            thread = Thread(target=worker, daemon=True, args=(i,))
            thread.start()
            self.threads.append(thread)

    def sequential(self, func: Callable[[int, Tello], None]):
        """각 Tello에 대해 순차적으로 `func`를 호출합니다. 함수는 두 개의 인자를 받습니다:
        현재 드론의 인덱스 `i`와 현재 [Tello][tello] 인스턴스 `tello`.
        Call `func` for each tello sequentially. The function retrieves
        two arguments: The index `i` of the current drone and `tello` the
        current [Tello][tello] instance.

        ```python
        swarm.parallel(lambda i, tello: tello.land())
        ```
        """

        for i, tello in enumerate(self.tellos):
            func(i, tello)

    def parallel(self, func: Callable[[int, Tello], None]):
        """각 Tello에 대해 병렬로 `func`를 호출합니다. 함수는 두 개의 인자를 받습니다:
        현재 드론의 인덱스 `i`와 현재 [Tello][tello] 인스턴스 `tello`.
        Call `func` for each tello in parallel. The function retrieves
        two arguments: The index `i` of the current drone and `tello` the
        current [Tello][tello] instance.

        스레드 간 동기화를 위해 `swarm.sync()`를 사용할 수 있습니다.
        You can use `swarm.sync()` for syncing between threads.

        ```python
        swarm.parallel(lambda i, tello: tello.move_up(50 + i * 10))
        ```
        """

        for queue in self.funcQueues:
            queue.put(func)

        self.funcBarrier.wait()
        self.funcBarrier.wait()

    def sync(self, timeout: float = None):
        """병렬 Tello 스레드를 동기화합니다. 모든 스레드가 `swarm.sync`를 호출할 때까지
        코드가 계속 실행되지 않습니다.
        Sync parallel tello threads. The code continues when all threads
        have called `swarm.sync`.

        ```python
        def doStuff(i, tello):
            tello.move_up(50 + i * 10)
            swarm.sync()

            if i == 2:
                tello.flip_back()
            # 한 드론이 플립을 완료할 때까지 다른 모든 드론이 대기
            # make all other drones wait for one to complete its flip
            swarm.sync()

        swarm.parallel(doStuff)
        ```
        """
        return self.barrier.wait(timeout)

    def __getattr__(self, attr):
        """모든 Tello에서 표준 Tello 함수를 병렬로 호출합니다.
        Call a standard tello function in parallel on all tellos.

        ```python
        swarm.command()
        swarm.takeoff()
        swarm.move_up(50)
        ```
        """
        def callAll(*args, **kwargs):
            self.parallel(lambda i, tello: getattr(tello, attr)(*args, **kwargs))

        return callAll

    def __iter__(self):
        """스웜의 모든 드론을 반복합니다.
        Iterate over all drones in the swarm.

        ```python
        for tello in swarm:
            print(tello.get_battery())
        ```
        """
        return iter(self.tellos)

    def __len__(self):
        """스웜의 Tello 수를 반환합니다.
        Return the amount of tellos in the swarm

        ```python
        print("Tello count: {}".format(len(swarm)))
        ```
        """
        return len(self.tellos)
