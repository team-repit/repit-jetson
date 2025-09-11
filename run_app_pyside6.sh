#!/bin/bash

echo "🚀 스쿼트 분석 GUI 애플리케이션 시작 - PySide6 버전!"
echo "=========================================================="
echo "ℹ️  젯슨 ARM64 최적화 - PySide6 사용 (PyQt5보다 안정적)"

# 가상환경 확인 및 활성화
if [ -d "app-env-pyside6" ]; then
    echo "🔍 PySide6 가상환경 발견, 활성화 중..."
    source app-env-pyside6/bin/activate
    echo "✅ PySide6 가상환경 활성화됨"
elif [ -d "app-env" ]; then
    echo "🔍 기본 가상환경 발견, 활성화 중..."
    source app-env/bin/activate
    echo "✅ 기본 가상환경 활성화됨"
else
    echo "ℹ️  가상환경 없음, 시스템 Python 사용"
    echo "   권장: python3 -m venv app-env-pyside6 && source app-env-pyside6/bin/activate"
fi

# PySide6 설치 확인
echo "🔍 PySide6 설치 확인 중..."
if python3 -c "import PySide6" 2>/dev/null; then
    echo "✅ PySide6 설치됨"
    # 버전 확인
    PYSIDE6_VERSION=$(python3 -c "import PySide6; print(PySide6.__version__)" 2>/dev/null || echo "알 수 없음")
    echo "   버전: $PYSIDE6_VERSION"
else
    echo "❌ PySide6가 설치되지 않았습니다."
    echo "   젯슨 ARM64용 설치 중..."
    
    # 시스템 의존성 먼저 설치 시도
    echo "   시스템 의존성 확인 중..."
    if command -v apt >/dev/null 2>&1; then
        echo "   Qt6 라이브러리 설치 중..."
        sudo apt update
        sudo apt install -y libqt6-core6 libqt6-gui6 libqt6-widgets6 libqt6-multimedia6
    fi
    
    # PySide6 설치
    pip3 install PySide6
    if [ $? -eq 0 ]; then
        echo "✅ PySide6 설치 완료"
    else
        echo "❌ PySide6 설치 실패"
        echo "   대안 1: sudo apt install python3-pyside6.qtwidgets"
        echo "   대안 2: conda install pyside6"
        exit 1
    fi
fi

# 필수 의존성 확인
echo "🔍 필수 의존성 확인 중..."
missing_deps=()

# 의존성 체크 함수
check_dependency() {
    local package=$1
    local import_name=$2
    
    if ! python3 -c "import $import_name" 2>/dev/null; then
        missing_deps+=("$package")
        return 1
    fi
    return 0
}

# 각 패키지 확인
check_dependency "opencv-python" "cv2" || echo "   ❌ OpenCV 누락"
check_dependency "mediapipe" "mediapipe" || echo "   ❌ MediaPipe 누락"
check_dependency "numpy" "numpy" || echo "   ❌ NumPy 누락"
check_dependency "pillow" "PIL" || echo "   ❌ Pillow 누락"
check_dependency "gtts" "gtts" || echo "   ❌ gTTS 누락"
check_dependency "pydub" "pydub" || echo "   ❌ pydub 누락"

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo "❌ 누락된 의존성: ${missing_deps[*]}"
    echo "   설치 중..."
    
    # 젯슨 최적화 설치
    if [[ " ${missing_deps[*]} " =~ " opencv-python " ]]; then
        echo "   젯슨용 OpenCV 설치 중..."
        # 젯슨에서는 시스템 OpenCV를 권장하지만, pip 버전도 지원
        pip3 install opencv-python
    fi
    
    # 나머지 패키지 설치
    other_deps=($(printf '%s\n' "${missing_deps[@]}" | grep -v opencv-python))
    if [ ${#other_deps[@]} -gt 0 ]; then
        pip3 install ${other_deps[*]}
    fi
    
    if [ $? -ne 0 ]; then
        echo "❌ 의존성 설치 실패"
        echo "   수동 설치 시도: pip3 install -r requirements_pyside6.txt"
        exit 1
    fi
    echo "✅ 의존성 설치 완료"
else
    echo "✅ 모든 의존성 설치됨"
fi

# 젯슨 GPU 가속 확인 (옵션)
echo "🔍 젯슨 GPU 가속 확인 중..."
if [ -f "/usr/local/cuda/version.txt" ] || command -v nvidia-smi >/dev/null 2>&1; then
    echo "✅ CUDA 환경 감지됨 - GPU 가속 가능"
    export CUDA_VISIBLE_DEVICES=0
else
    echo "ℹ️  CUDA 환경 없음 - CPU 모드로 실행"
fi

# 카메라 장치 확인
echo "🔍 카메라 장치 확인 중..."
if [ -e "/dev/video0" ]; then
    echo "✅ 카메라 장치 발견: /dev/video0"
elif [ -e "/dev/video1" ]; then
    echo "✅ 카메라 장치 발견: /dev/video1"
    export CAMERA_DEVICE=1
else
    echo "⚠️  카메라 장치를 찾을 수 없습니다"
    echo "   연결된 카메라를 확인하세요"
fi

# 메모리 최적화 설정 (젯슨용)
echo "🔧 젯슨 메모리 최적화 설정..."
export PYTHONHASHSEED=0
export PYTHONUNBUFFERED=1
export MALLOC_TRIM_THRESHOLD_=0

# 애플리케이션 실행
echo "🎯 PySide6 기반 애플리케이션 실행 중..."
echo "   파일: main_pyside6.py"
echo "   GUI: PySide6 (Qt6)"
echo "   타겟: 젯슨 ARM64"

python3 main_pyside6.py

exit_code=$?

echo ""
echo "👋 애플리케이션이 종료되었습니다."
echo "   종료 코드: $exit_code"

if [ $exit_code -ne 0 ]; then
    echo "❌ 애플리케이션이 비정상 종료되었습니다."
    echo "   로그를 확인하고 오류를 해결해주세요."
else
    echo "✅ 정상 종료되었습니다."
fi

exit $exit_code 