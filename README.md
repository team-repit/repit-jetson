# 🏋️ 스쿼트 분석 GUI 애플리케이션

PyQt5를 사용하여 젯슨에서 실행 가능한 스쿼트 분석 GUI 애플리케이션입니다.

## ✨ 주요 기능

- **⏱️ 타이머 설정**: 10초 ~ 2분까지 분석 시간 설정 가능
- **🚀 원클릭 실행**: 버튼 하나로 스쿼트 분석 시작
- **🎥 실시간 카메라**: squat_real_tts.py와 연동하여 카메라 실행
- **📊 결과 표시**: 분석 비디오와 리포트를 GUI에서 확인
- **⏹️ 분석 중지**: 언제든지 분석을 중지할 수 있음

## 🏗️ 시스템 요구사항

- **OS**: Ubuntu 20.04+ (Jetson)
- **Python**: 3.8+
- **GUI**: PyQt5
- **카메라**: USB 웹캠 또는 Jetson 카메라

## 📦 설치 방법

### 1. 가상환경 설정
```bash
# jetson_tts_env 가상환경이 필요합니다
# setup_jetson.sh를 먼저 실행하세요
```

### 2. PyQt5 설치
```bash
# 가상환경 활성화
source jetson_tts_env/bin/activate

# PyQt5 설치
pip install PyQt5
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

## 🚀 실행 방법

### 방법 1: 실행 스크립트 사용 (권장)
```bash
cd application
./run_app.sh
```

### 방법 2: 직접 실행
```bash
cd application
source ../jetson_tts_env/bin/activate
python main.py
```

## 🎯 사용법

### 1. 분석 시간 설정
- **타이머**: 10초 ~ 2분 사이에서 원하는 시간 설정
- **권장**: 처음에는 30초로 테스트

### 2. 분석 시작
- **🚀 분석 시작** 버튼 클릭
- 카메라가 켜지고 스쿼트 분석 시작
- 진행률 바로 분석 진행 상황 확인

### 3. 분석 중지
- **⏹️ 분석 중지** 버튼으로 언제든지 중지 가능
- 중지 시 현재까지의 결과 저장

### 4. 결과 확인
- **🎥 분석 비디오**: 생성된 MP4 파일 정보 표시
- **📊 분석 리포트**: TTS 피드백과 등급 정보 표시

## 📁 파일 구조

```
application/
├── main.py              # 메인 실행 파일
├── ui/
│   └── main_window.py   # 메인 윈도우 UI
├── output/              # 결과 파일 저장 (자동 생성)
├── requirements.txt     # 의존성 패키지
├── run_app.sh          # 실행 스크립트
└── README.md           # 이 파일
```

## 🔧 문제 해결

### PyQt5 설치 오류
```bash
# 시스템 패키지로 설치
sudo apt-get install python3-pyqt5

# 또는 pip로 설치
pip install PyQt5
```

### 카메라 접근 오류
```bash
# 카메라 권한 확인
ls -la /dev/video*

# Jetson 카메라 설정
sudo usermod -aG video $USER
```

### 가상환경 문제
```bash
# 가상환경 재생성
python3 -m venv jetson_tts_env
source jetson_tts_env/bin/activate
pip install -r requirements.txt
```

## 🎨 UI 구성

- **제목**: 스쿼트 분석 시스템
- **설정 영역**: 타이머 설정, 시작/중지 버튼
- **진행률**: 분석 진행 상황 표시
- **결과 영역**: 비디오 정보 + 분석 리포트
- **상태 표시**: 현재 애플리케이션 상태

## 🚀 향후 개선 계획

- [ ] 비디오 플레이어 내장
- [ ] 실시간 분석 결과 표시
- [ ] 분석 히스토리 저장
- [ ] 설정 파일 지원
- [ ] 다국어 지원

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. 가상환경이 활성화되어 있는지
2. PyQt5가 설치되어 있는지
3. 카메라가 정상 작동하는지
4. squat_real_tts.py가 실행 가능한지

---

**🏋️ 스쿼트 분석을 GUI로 쉽게 실행하세요!** 