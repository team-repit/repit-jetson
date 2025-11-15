# Re:PiT 데스크톱 애플리케이션

실시간 카메라 영상을 기반으로 스쿼트·런지·플랭크 자세를 분석하고, 음성 피드백(TTS)과 서버 연동을 제공하는 PySide6 GUI 애플리케이션입니다. Jetson (Ubuntu 22.04)과 macOS/Windows 환경에서 실행 및 배포할 수 있도록 PyInstaller 기반 빌드 스크립트를 포함하고 있습니다.

---

## 주요 기능

- **실시간 자세 분석**: MediaPipe Pose를 활용한 스쿼트(squat), 런지(lunge), 플랭크(plank) 평가
- **음성 피드백(TTS)**: 자세 오류를 실시간 안내, 격려 멘트 제공
- **토큰 기반 서버 연동**: 운동 기록, 분석 리포트, 영상 자동 업로드(Presigned URL)
- **자동 파일 관리**: 전송 성공 시 로컬 MP4/TXT/JSON 정리, 실패·토큰 미입력 시 로컬 보존
- **Jetson 친화적 UI**: PySide6를 활용한 카메라 프리뷰, 상태 패널, 분석 결과 표시

전체 흐름과 파일 구조는 `APP_FILE_OVERVIEW.md`에 요약되어 있습니다.

---

## 실행 구조 요약

| 구성 요소 | 설명 |
|-----------|------|
| `main_pyside6.py` | PySide6 앱 엔트리포인트. `AppController`를 표시하고 토큰 화면 ↔ 메인 화면을 전환합니다. |
| `ui_pyside6/token_input_widget.py` | API 토큰 입력/저장/삭제 UI. 토큰 없이 계속하기 옵션 제공. |
| `ui_pyside6/main_window.py` | 메인 UI. 운동 선택, 카메라 스트림, 분석 스레드 실행, 서버 전송 결과를 관리합니다. |
| `squat_real_tts.py` 등 | 운동별 분석 로직(TTS 포함)과 리포트/JSON/영상 생성. |
| `analysis_postprocess.py` | API 전송 + Presigned URL 기반 영상 업로드를 담당하는 헬퍼. 세 운동 모듈에서 재사용. |

자세한 흐름과 빌드 스크립트 소개는 [`APP_FILE_OVERVIEW.md`](APP_FILE_OVERVIEW.md)를 참고하세요.

---

## 개발 환경 실행

```bash
cd ai/application
python3 -m venv .venv         # (선택) 가상환경 생성
source .venv/bin/activate
pip install -r requirements.txt
python main_pyside6.py
```

Jetson에서 시스템 전역 패키지를 사용하는 경우 `requirements_jetson.txt`, `setup_jetson_path.py` 등을 참고하세요.

---

## 테스트

단위 테스트는 `pytest` 기반입니다.

```bash
cd ai/application
pytest tests
```

- `tests/test_api_client_video.py` : Presigned URL 흐름 검증  
- `tests/test_save_json_report.py` : 분석 리포트 문자열 저장 검사

---

## 빌드 & 배포

| 플랫폼 | 권장 스크립트 | 결과물 |
|--------|---------------|--------|
| **macOS / Windows / 일반 Linux** | `python3 build_exe.py` | 현재 OS에 맞는 PyInstaller 결과. macOS에선 `dist/RePiT.app` → 옵션으로 `RePiT.dmg`까지 생성 |
| **Jetson (Ubuntu 22.04, aarch64)** | `python3 build_jetson_app.py` | `dist_jetson/RePiT-Jetson/` + 설치 디렉터리 복사 + `.desktop` 아이콘 |

두 스크립트 모두 실행 중인 플랫폼에서 PyInstaller를 호출하므로, **Mac에서 만든 결과물을 Jetson에서 사용할 수는 없습니다** (아키텍처 차이). Jetson 전용 빌드는 Jetson 장비에서 실행해 주세요.

### macOS 빌드 예시

```bash
cd ai/application
rm -rf build dist             # (선택) 기존 산출물 정리
python3 build_exe.py          # onedir 모드 권장, 끝나면 DMG 여부 질문
```

- `dist/RePiT.app`을 직접 실행하거나, `dist/RePiT.dmg`를 사용자에게 배포합니다.
- 보안 경고가 나오면 `System Settings > Privacy & Security > Open Anyway` 또는 `xattr -cr dist/RePiT.app`를 실행하세요.

### Jetson 빌드 & 설치 예시

```bash
cd ai/application
python3 build_jetson_app.py \
    --install-dir ~/RePiT-Jetson \
    --desktop-path ~/Desktop/RePiT.desktop \
    --launcher-name RePiT

# 바탕화면에 생성된 RePiT.desktop 더블클릭 → '신뢰 및 실행' 선택
```

- 설치만 필요한 Jetson에 배포하려면 `dist_jetson/RePiT-Jetson/`을 압축(`tar -czf ...`)해서 옮긴 뒤 풀고, `.desktop` 파일의 `Exec`/`Icon` 경로를 그 위치에 맞게 조정하세요.

---

## 로컬 출력 파일

- 분석 완료 시 항상 `output/` 아래에 MP4, TXT, JSON이 생성됩니다.
- 토큰 미입력 또는 서버 오류 → 파일 유지  
- 토큰 입력 + 서버/영상 업로드 성공 → UI에 내용을 표시한 후 로컬 파일 삭제 (콘솔 로그로 삭제 여부 출력)

---

## 참고 자료

- `APP_FILE_OVERVIEW.md` : 앱 엔트리포인트 및 빌드 스크립트 개요
- `order/API_DOCUMENTATION.md` : 서버 API 명세, 점수 체계, Presigned URL 절차
- `order/video1_jetson.md` : Jetson에서 Presigned URL을 사용할 때 주의사항

---

Re:PiT 앱은 Jetson 현장에서 바로 사용할 수 있는 자세 분석 도구를 목표로 합니다. 문제가 발생하면 토큰 설정 상태, 카메라 권한, API 연결을 확인한 뒤 필요 시 빌드 스크립트를 다시 실행해 주세요. 즐거운 운동 분석 되세요! 🏋️‍♀️