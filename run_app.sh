#!/bin/bash

echo "🚀 스쿼트 분석 GUI 애플리케이션 시작!"
echo "=========================================="

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
        exit 1
    fi
fi

# 애플리케이션 실행
echo "🎯 애플리케이션 실행 중..."
python main.py

echo "👋 애플리케이션이 종료되었습니다." 
