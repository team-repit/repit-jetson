#!/bin/bash

# 젯슨에서 tkinter 기반 스쿼트 분석 애플리케이션 실행 스크립트

echo "=== 스쿼트 분석 시스템 (tkinter 버전) ==="
echo "젯슨에서 실행 중..."

# Python 가상환경 활성화 (있는 경우)
if [ -d "app-env" ]; then
    echo "가상환경 활성화 중..."
    source app-env/bin/activate
fi

# 필요한 패키지 설치 확인
echo "의존성 확인 중..."
pip install -r requirements_tkinter.txt

# tkinter 사용 가능 여부 확인
python3 -c "import tkinter; print('tkinter 사용 가능')" || {
    echo "오류: tkinter를 사용할 수 없습니다."
    echo "Python이 tkinter와 함께 설치되었는지 확인하세요."
    exit 1
}

# 애플리케이션 실행
echo "애플리케이션 시작 중..."
python3 main_tkinter.py

echo "애플리케이션 종료됨" 