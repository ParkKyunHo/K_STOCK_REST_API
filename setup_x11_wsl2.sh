#!/bin/bash
# WSL2에서 X11 GUI 지원을 위한 설정 스크립트

echo "🖥️  WSL2 X11 설정 스크립트"
echo "=========================="
echo ""

# 1. 시스템 패키지 업데이트
echo "📦 시스템 패키지 업데이트 중..."
sudo apt-get update

# 2. X11 관련 패키지 설치
echo ""
echo "📦 X11 관련 패키지 설치 중..."
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
    libqt5dbus5 \
    qt5-gtk-platformtheme \
    x11-apps \
    xauth

# 3. 폰트 설치
echo ""
echo "🔤 한글 폰트 설치 중..."
sudo apt-get install -y fonts-nanum fonts-nanum-coding fonts-noto-cjk

# 4. .bashrc에 DISPLAY 설정 추가
echo ""
echo "⚙️  환경 변수 설정 중..."

BASHRC_FILE="$HOME/.bashrc"
DISPLAY_SETUP='# WSL2 X11 Display 설정
if grep -q microsoft /proc/version; then
    # 기본 게이트웨이 IP 사용 (더 안정적)
    export DISPLAY=$(ip route show | grep -i default | awk '"'"'{ print $3 }'"'"'):0
    # 대체 방법 (위가 작동하지 않을 경우)
    # export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '"'"'{print $2}'"'"'):0
    # Wayland와의 충돌 방지
    unset WAYLAND_DISPLAY
fi'

if ! grep -q "WSL2 X11 Display" "$BASHRC_FILE"; then
    echo "" >> "$BASHRC_FILE"
    echo "$DISPLAY_SETUP" >> "$BASHRC_FILE"
    echo "✅ .bashrc에 DISPLAY 설정 추가됨"
else
    echo "✅ DISPLAY 설정이 이미 존재합니다"
fi

# 5. Windows 방화벽 규칙 안내
echo ""
echo "🔥 Windows 방화벽 설정 안내"
echo "=========================="
echo ""
echo "Windows PowerShell을 관리자 권한으로 실행하고 다음 명령을 실행하세요:"
echo ""
echo 'New-NetFirewallRule -DisplayName "WSL2 X11 Server" -Direction Inbound -LocalPort 6000 -Protocol TCP -Action Allow'
echo ""

# 6. VcXsrv 설치 안내
echo "📥 VcXsrv 설치 안내"
echo "==================="
echo ""
echo "1. https://sourceforge.net/projects/vcxsrv/ 에서 VcXsrv 다운로드"
echo "2. VcXsrv 설치 후 XLaunch 실행"
echo "3. 다음 설정으로 실행:"
echo "   - Display number: 0"
echo "   - Multiple windows 선택"
echo "   - Start no client 선택"
echo "   - ⚠️ 'Disable access control' 체크 (중요!)"
echo "   - Save configuration으로 설정 저장"
echo ""

# 7. 테스트
echo "🧪 X11 연결 테스트"
echo "================="
echo ""
echo "현재 셸에서 DISPLAY 설정:"
# 기본 게이트웨이 IP 사용
GATEWAY_IP=$(ip route show | grep -i default | awk '{ print $3 }')
if [ -n "$GATEWAY_IP" ]; then
    export DISPLAY=$GATEWAY_IP:0
    echo "DISPLAY=$DISPLAY (게이트웨이 IP)"
else
    export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
    echo "DISPLAY=$DISPLAY (resolv.conf)"
fi
unset WAYLAND_DISPLAY
echo ""

echo "xclock 실행으로 테스트 중..."
if timeout 3 xclock &>/dev/null; then
    echo "✅ X11 연결 성공!"
else
    echo "❌ X11 연결 실패. VcXsrv가 실행 중인지 확인하세요."
fi

echo ""
echo "✨ 설정 완료!"
echo ""
echo "다음 명령으로 Trading UI를 실행하세요:"
echo "  source ~/.bashrc"
echo "  ./run_trading_ui_wsl.sh"