#!/bin/bash
# Offscreen 모드로 UI 테스트 (GUI 없이 실행)

echo "🖥️  Trading UI - Offscreen 모드"
echo "==============================="
echo ""
echo "GUI 없이 백그라운드에서 실행됩니다."
echo ""

# 환경 변수 설정
export QT_QPA_PLATFORM=offscreen

# 가상환경 확인
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  가상환경이 활성화되지 않았습니다."
    echo "   다음 명령을 실행하세요: source venv/bin/activate"
    exit 1
fi

# 실행
echo "🚀 Trading UI를 Offscreen 모드로 시작합니다..."
python run_trading_ui.py