# DJITelloPy 설치 가이드

## 사전 요구사항 체크리스트
- Python 3.6 이상 설치
- pip 패키지 관리자 설치
- (선택) Visual Studio Build Tools - av 패키지 설치 시 필요

## 기본 설치 방법

1. pip를 최신 버전으로 업그레이드:
    ```powershell
    python -m pip install --upgrade pip
    ```

2. DJITelloPy 설치:
    ```powershell
    pip install djitellopy
    ```


## git clone 명령어가 없는 경우

1. git 설치 또는 다운로드
    ```powershell
    winget install -e --id Git.Git
    ```

    https://git-scm.com/downloads/win




## SSL 인증서 오류 발생 시

SSL 인증서 오류가 발생하는 경우 다음 방법들을 순서대로 시도해보세요:

1. trusted-host 옵션 사용:
    ```powershell
    pip install djitellopy --trusted-host pypi.org --trusted-host files.pythonhosted.org
    ```

2. pip 설정 파일 생성:
    ```powershell
    mkdir ~\pip
    echo "[global]
    trusted-host = 
        pypi.python.org
        pypi.org
        files.pythonhosted.org" | Out-File ~\pip\pip.ini -Encoding ascii
    ```

## 의존성 패키지 개별 설치

기본 패키지 설치가 실패하는 경우, 다음과 같이 의존성 패키지를 개별적으로 설치해볼 수 있습니다:

1. NumPy 설치:
    ```powershell
    pip install numpy
    ```

2. OpenCV 설치 (컴파일 오류 발생 시 바이너리 버전 사용):
    ```powershell
    pip install --only-binary :all: opencv-python
    ```

3. Pillow 설치:
    ```powershell
    pip install pillow
    ```

## av 패키지 설치 문제

av 패키지는 비디오 스트리밍에 사용되는 선택적 의존성입니다. 설치가 어려운 경우 다음과 같이 처리할 수 있습니다:

1. av 패키지 설치를 위한 요구사항:
   - Microsoft Visual C++ 14.0 이상
   - Visual Studio Build Tools 설치 필요
   - 설치 링크: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - "Desktop development with C++" 워크로드 선택 필요

   ![alt text](image.png)

2. av 패키지 없이 설치:
   - 비디오 스트리밍 기능을 사용하지 않는 경우 av 패키지 설치를 건너뛸 수 있습니다
   - 기본 드론 제어 기능은 정상적으로 사용 가능

## 문제 해결

1. SSL 인증서 오류가 지속되는 경우:
   - Python 설치 경로의 인증서 업데이트 필요
   - certifi 패키지 설치 및 업데이트 시도
   - 기업 환경의 경우 네트워크 관리자에게 문의

2. 의존성 패키지 설치 실패 시:
   - 각 패키지의 호환 버전 확인
   - Python 버전 호환성 체크
   - 오프라인 설치 패키지(.whl) 사용 고려

3. 빌드 도구 관련 오류:
   - Visual Studio Build Tools 설치 상태 확인
   - 시스템 환경 변수 설정 확인
   - Windows SDK 설치 여부 확인

## 설치 확인

설치가 완료된 후 다음 Python 코드로 테스트할 수 있습니다:

```python
from djitellopy import Tello

# Tello 객체 생성
tello = Tello()

# Tello 연결 테스트
tello.connect()
print(f"배터리 잔량: {tello.get_battery()}%") 
```

## 가상 환경 설정 및 설치 과정

1. 가상 환경 생성 및 활성화:
    ```powershell
    python -m venv venv
    .\venv\Scripts\activate
    ```

2. pip 업그레이드:
    ```powershell
    python -m pip install --upgrade pip
    ```

3. DJITelloPy 설치 시도 시 발생할 수 있는 문제:
   - av 패키지 설치 실패
   - Cython 관련 오류
   - 빌드 의존성 문제

4. 해결 방법:
   - av 패키지를 제외하고 설치:
     ```powershell
     pip install djitellopy --no-deps
     pip install numpy opencv-python pillow
     ```
   - 또는 이전 버전의 av 패키지 시도:
     ```powershell
     pip install av==9.2.0
     pip install djitellopy
     ``` 