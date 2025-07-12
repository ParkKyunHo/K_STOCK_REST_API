#!/bin/bash
# -*- coding: utf-8 -*-
# WSL2에서 Trading UI 실행을 위한 스크립트

echo "🚀 K-Stock Trading UI for WSL2"
echo "================================"

# WSL2 환경 확인
if grep -q microsoft /proc/version; then
    echo "✅ WSL2 환경 감지됨"
else
    echo "⚠️  경고: WSL2 환경이 아닙니다"
fi

# X11 서버 연결 설정
echo ""
echo "📡 X11 서버 설정 중..."

# 기본 게이트웨이 IP 사용 (더 안정적)
GATEWAY_IP=$(ip route show | grep -i default | awk '{ print $3 }')
if [ -n "$GATEWAY_IP" ]; then
    export DISPLAY=$GATEWAY_IP:0
    echo "   DISPLAY 환경변수 설정: $GATEWAY_IP:0 (게이트웨이 IP)"
else
    # 대체 방법: resolv.conf 사용
    WSL_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
    export DISPLAY=$WSL_IP:0
    echo "   DISPLAY 환경변수 설정: $WSL_IP:0 (resolv.conf)"
fi

# Wayland 충돌 방지
unset WAYLAND_DISPLAY

# X11 연결 테스트
echo ""
echo "🔍 X11 서버 연결 테스트 중..."
if timeout 2 xset -q &>/dev/null; then
    echo "✅ X11 서버 연결 성공!"
else
    echo "❌ X11 서버 연결 실패!"
    echo ""
    echo "다음 단계를 따라주세요:"
    echo "1. Windows에 VcXsrv 또는 X410 설치"
    echo "2. VcXsrv 실행 시 다음 옵션 선택:"
    echo "   - Multiple windows"
    echo "   - Start no client"
    echo "   - Disable access control 체크"
    echo "3. Windows 방화벽에서 VcXsrv 허용"
    echo ""
    echo "Offscreen 모드로 실행하시겠습니까? (GUI 없이 백그라운드 실행) [y/N]"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        export QT_QPA_PLATFORM=offscreen
        echo "🖥️  Offscreen 모드로 실행합니다..."
    else
        exit 1
    fi
fi

# Qt 설정
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_SCALE_FACTOR=1.0

# 가상환경 활성화 확인
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo ""
    echo "⚠️  가상환경이 활성화되지 않았습니다."
    echo "   다음 명령을 실행하세요: source venv/bin/activate"
    exit 1
fi

# 필요한 패키지 확인
echo ""
echo "📦 필요한 시스템 패키지 확인 중..."
REQUIRED_PACKAGES=(
    "libxcb-xinerama0"
    "libxcb-icccm4"
    "libxcb-image0"
    "libxcb-keysyms1"
    "libxcb-randr0"
    "libxcb-render-util0"
    "libxcb-xfixes0"
    "libqt5gui5"
    "libqt5widgets5"
    "libqt5core5a"
)

MISSING_PACKAGES=()
for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if ! dpkg -l | grep -q "^ii  $pkg"; then
        MISSING_PACKAGES+=($pkg)
    fi
done

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo "❌ 다음 패키지가 필요합니다:"
    echo "   ${MISSING_PACKAGES[*]}"
    echo ""
    echo "설치하시겠습니까? [Y/n]"
    read -r response
    if [[ ! "$response" =~ ^([nN][oO]|[nN])$ ]]; then
        echo "패키지 설치 중..."
        sudo apt-get update
        sudo apt-get install -y "${MISSING_PACKAGES[@]}"
    fi
else
    echo "✅ 모든 필요한 패키지가 설치되어 있습니다."
fi

# PyQt5 확인
echo ""
echo "🐍 PyQt5 설치 확인 중..."
if python -c "import PyQt5" 2>/dev/null; then
    echo "✅ PyQt5가 설치되어 있습니다."
else
    echo "❌ PyQt5가 설치되지 않았습니다."
    echo "   pip install PyQt5==5.15.10 실행이 필요합니다."
    exit 1
fi

# Trading UI 실행
echo ""
echo "🚀 Trading UI를 시작합니다..."
echo "================================"
echo ""

# 실행
python run_trading_ui.py