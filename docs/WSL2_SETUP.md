# WSL2에서 Trading UI 실행 가이드

## 1. 개요

이 문서는 Windows Subsystem for Linux 2 (WSL2) 환경에서 PyQt5 기반 Trading UI를 실행하는 방법을 설명합니다.

## 2. 전제 조건

- Windows 10 버전 2004 이상 또는 Windows 11
- WSL2가 설치되어 있어야 함
- Ubuntu 20.04 이상 (WSL2)

## 3. X11 서버 설정

### 3.1 자동 설정 (권장)

프로젝트 루트에서 다음 스크립트를 실행하세요:

```bash
# X11 설정 스크립트 실행
./setup_x11_wsl2.sh

# 환경 변수 적용
source ~/.bashrc
```

### 3.2 수동 설정

#### Step 1: VcXsrv 설치 (Windows)

1. [VcXsrv 다운로드](https://sourceforge.net/projects/vcxsrv/)
2. 설치 완료 후 XLaunch 실행
3. 다음 설정으로 구성:
   - **Display number**: 0
   - **Select display settings**: Multiple windows
   - **Start no client** 선택
   - **Extra settings**: 
     - ✅ Disable access control (중요!)
     - ✅ Native opengl
4. "Save configuration" 버튼으로 설정 저장
   - 저장 위치: `C:\Users\[사용자명]\Documents\vcxsrv.xlaunch`
   - 파일명 예시: `vcxsrv_wsl2.xlaunch` 또는 `vcxsrv_trading_ui.xlaunch`

#### Step 2: Windows 방화벽 설정

PowerShell을 관리자 권한으로 실행하고:

```powershell
New-NetFirewallRule -DisplayName "WSL2 X11 Server" -Direction Inbound -LocalPort 6000 -Protocol TCP -Action Allow
```

#### Step 3: WSL2에서 필요한 패키지 설치

```bash
sudo apt-get update
sudo apt-get install -y \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libqt5gui5 \
    libqt5widgets5 \
    libqt5core5a \
    x11-apps
```

#### Step 4: DISPLAY 환경 변수 설정

`.bashrc` 파일에 다음 내용 추가:

```bash
# WSL2 X11 Display 설정
if grep -q microsoft /proc/version; then
    # 기본 게이트웨이 IP 사용 (더 안정적)
    export DISPLAY=$(ip route show | grep -i default | awk '{ print $3 }'):0
    # 대체 방법 (위가 작동하지 않을 경우)
    # export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
    # Wayland와의 충돌 방지
    unset WAYLAND_DISPLAY
fi
```

**중요**: `ip route show` 방법이 더 안정적이며, WSL2 네트워크 구성이 변경되어도 정확한 호스트 IP를 찾습니다.

## 4. VcXsrv 설정 파일 활용

### 4.1 저장된 설정 파일로 VcXsrv 실행

```bash
# Windows에서 저장한 .xlaunch 파일을 더블클릭하여 실행
# 또는 명령 프롬프트에서:
"C:\Program Files\VcXsrv\xlaunch.exe" -run "C:\Users\[사용자명]\Documents\vcxsrv.xlaunch"
```

### 4.2 Windows 시작 시 자동 실행 설정

1. Win + R → `shell:startup` 입력
2. 열린 폴더에 `vcxsrv.xlaunch` 파일 복사
3. Windows 부팅 시 자동으로 X 서버 시작

### 4.3 작업 표시줄에 고정

1. `vcxsrv.xlaunch` 파일 우클릭 → 바로가기 만들기
2. 바로가기를 작업 표시줄에 드래그하여 고정

## 5. Trading UI 실행

### 5.1 자동 실행 스크립트 사용 (권장)

```bash
# 가상환경 활성화
source venv/bin/activate

# WSL2용 실행 스크립트 사용
./run_trading_ui_wsl.sh
```

### 4.2 수동 실행

```bash
# 가상환경 활성화
source venv/bin/activate

# DISPLAY 설정 확인
echo $DISPLAY

# Trading UI 실행
python run_trading_ui.py
```

## 5. 문제 해결

### 5.1 "could not connect to display" 오류

```bash
# X11 서버 연결 테스트
xclock

# 실패 시 VcXsrv가 실행 중인지 확인
# Windows 트레이에서 VcXsrv 아이콘 확인
```

### 5.2 "No protocol specified" 오류

VcXsrv 설정에서 "Disable access control"이 체크되어 있는지 확인

### 5.3 Qt platform plugin 오류

```bash
# 필요한 Qt 라이브러리 재설치
sudo apt-get install --reinstall libqt5gui5 libqt5widgets5 libqt5core5a

# PyQt5 재설치
pip uninstall PyQt5
pip install PyQt5==5.15.10
```

### 5.4 한글 폰트 문제

```bash
# 한글 폰트 설치
sudo apt-get install fonts-noto-cjk fonts-nanum fonts-nanum-coding

# 폰트 캐시 업데이트
fc-cache -fv
```

### 5.5 DISPLAY 연결 문제

DISPLAY 환경변수 설정이 작동하지 않을 경우:

```bash
# 방법 1: 기본 게이트웨이 IP 사용 (권장)
export DISPLAY=$(ip route show | grep -i default | awk '{ print $3 }'):0

# 방법 2: resolv.conf 사용
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0

# 방법 3: 직접 IP 확인 후 설정
# Windows PowerShell에서: ipconfig
# vEthernet (WSL) 어댑터의 IPv4 주소 확인
export DISPLAY=172.27.112.1:0  # 예시, 실제 IP로 변경
```

## 6. Offscreen 모드 (GUI 없이 실행)

GUI 표시가 필요 없는 경우:

```bash
# Offscreen 모드로 실행
export QT_QPA_PLATFORM=offscreen
python run_trading_ui.py
```

## 7. 성능 최적화

### 7.1 GPU 가속 활성화

`.bashrc`에 추가:

```bash
export LIBGL_ALWAYS_INDIRECT=1
```

### 7.2 DPI 스케일링 조정

고해상도 디스플레이의 경우:

```bash
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_SCALE_FACTOR=1.5  # 필요에 따라 조정
```

## 8. 디버깅

### 8.1 Qt 디버그 정보 활성화

```bash
export QT_DEBUG_PLUGINS=1
export QT_LOGGING_RULES="qt.qpa.xcb*=true"
python run_trading_ui.py
```

### 8.2 X11 연결 정보 확인

```bash
# DISPLAY 변수 확인
echo $DISPLAY

# X11 서버 접근 가능 여부
xhost

# WSL2 IP 주소 확인
ip addr show eth0
```

## 9. 자주 묻는 질문

### Q: VcXsrv 대신 다른 X 서버를 사용할 수 있나요?

A: 네, 다음 대안들을 사용할 수 있습니다:
- X410 (유료, Microsoft Store)
- MobaXterm (무료/유료)
- Xming (무료)

### Q: WSLg (네이티브 GUI 지원)는 어떻게 사용하나요?

A: Windows 11 또는 Windows 10 Build 21364 이상에서는 WSLg가 기본 제공됩니다:

```bash
# WSLg 사용 시 별도 설정 불필요
# DISPLAY는 자동으로 설정됨
python run_trading_ui.py
```

### Q: 원격 데스크톱에서 사용할 수 있나요?

A: 원격 데스크톱 환경에서는 추가 설정이 필요합니다:
1. VcXsrv를 원격 세션에서 실행
2. 방화벽 규칙 확인
3. 네트워크 지연으로 인한 성능 저하 고려

---

**작성일**: 2025-07-13  
**버전**: 1.0.0