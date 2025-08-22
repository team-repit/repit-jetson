#!/bin/bash

echo "🍎 맥북용 스쿼트 분석 GUI 애플리케이션 시작!"
echo "=========================================="

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Python 가상환경 확인 (맥북용)
if [ -d "../repit-env" ]; then
    echo "✅ 가상환경 발견, 활성화 중..."
    source ../repit-env/bin/activate
elif [ -d "../venv" ]; then
    echo "✅ 가상환경 발견, 활성화 중..."
    source ../venv/bin/activate
else
    echo "⚠️ 가상환경을 찾을 수 없습니다."
    echo "   ../repit-env 또는 ../venv 디렉토리가 존재하는지 확인하세요."
    echo "   또는 새 가상환경을 생성하세요:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    exit 1
fi

# PyQt5 설치 확인
echo "🔍 PyQt5 설치 확인 중..."
if python -c "import PyQt5" 2>/dev/null; then
    echo "✅ PyQt5 설치됨"
else
    echo "❌ PyQt5가 설치되지 않았습니다."
    echo "   설치 중..."
    pip install PyQt5
    if [ $? -eq 0 ]; then
        echo "✅ PyQt5 설치 완료"
    else
        echo "❌ PyQt5 설치 실패"
        echo "   맥북에서는 다음 명령어로 설치해보세요:"
        echo "   pip install PyQt5"
        echo "   또는"
        echo "   brew install pyqt@5"
        exit 1
    fi
fi

# 기타 필요한 패키지 설치
echo "🔍 기타 패키지 설치 확인 중..."
pip install numpy pillow

# 애플리케이션 실행
echo "🎯 애플리케이션 실행 중..."
python main.py

echo "👋 애플리케이션이 종료되었습니다." 