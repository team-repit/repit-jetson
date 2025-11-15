#!/usr/bin/env python3
"""
운동 자세 분석 메인 윈도우 UI - PySide6 버전
젯슨 ARM64에서 실행 가능한 PySide6 기반 GUI 애플리케이션
"""

import sys
import os
import time
import threading

# PyInstaller 환경에서 경로 처리
def resource_path(relative_path):
    """PyInstaller 환경에서 리소스 경로 가져오기"""
    try:
        # PyInstaller로 빌드된 경우 _MEIPASS 임시 폴더
        base_path = sys._MEIPASS
    except Exception:
        # 일반 Python 실행 환경
        base_path = os.path.dirname(os.path.abspath(__file__))
        # ui_pyside6 폴더에서 상위로 이동
        base_path = os.path.dirname(base_path)
    return os.path.join(base_path, relative_path)

# 젯슨/ARM64 최적화를 위한 환경변수 설정
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
os.environ['OPENCV_VIDEOIO_DEBUG'] = '1'
os.environ['QT_MAC_WANTS_LAYER'] = '1'

# PySide6 import (PyQt5에서 변경)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QPushButton, QLabel, QGroupBox,
                              QSpinBox, QTextEdit, QMessageBox, QFrame)
from PySide6.QtCore import QThread, Signal, Qt, QTimer, QMutex, QObject
from PySide6.QtGui import QPixmap, QImage, QFont, QIcon
import cv2
import numpy as np

# API 클라이언트 import
from api_client import RepitAPIClient

# OpenCV 백엔드 설정 (젯슨 안정성 향상)
try:
    cv2.setUseOptimized(True)
    cv2.setNumThreads(4)
except:
    pass

class TTSManager(QObject):
    """TTS 관리를 위한 Qt 객체 - 젯슨 안정성 강화"""
    feedback_ready = Signal(str, str)  # 메시지, 우선순위
    
    def __init__(self, exercise_type):
        super().__init__()
        self.exercise_type = exercise_type
        self.tts_worker = None
        self.feedback_timer = None
        self.setup_tts()
    
    def setup_tts(self):
        """TTS 워커 설정 - 시그널 없이 직접 사용"""
        try:
            # UniversalTTS import 및 생성 (메인 스레드에서 직접 생성)
            # PyInstaller 환경을 고려한 안전한 import
            if self.exercise_type == "squat":
                try:
                    from squat_real_tts import UniversalTTS
                except ImportError as e:
                    print(f"[ERROR] squat_real_tts import 실패: {e}")
                    import squat_real_tts
                    UniversalTTS = squat_real_tts.UniversalTTS
            elif self.exercise_type == "lunge":
                try:
                    from lunge_realtime import UniversalTTS
                except ImportError as e:
                    print(f"[ERROR] lunge_realtime import 실패: {e}")
                    import lunge_realtime
                    UniversalTTS = lunge_realtime.UniversalTTS
            elif self.exercise_type == "plank":
                try:
                    from plank import UniversalTTS
                except ImportError as e:
                    print(f"[ERROR] plank import 실패: {e}")
                    import plank
                    UniversalTTS = plank.UniversalTTS
            else:
                return
            
            # 메인 스레드에서 직접 생성 (시그널 사용 안 함)
            self.tts_worker = UniversalTTS()
            
            # 피드백 워커 시작 (시그널 없이 직접 처리)
            self.start_feedback_worker()
            
            print("[DEBUG] TTS 매니저 설정 완료 (시그널 없이)")
        except Exception as e:
            print(f"TTS 설정 오류: {e}")
    
    def start_feedback_worker(self):
        """TTS 피드백 워커를 시작하는 메서드 - UniversalTTS가 자체적으로 처리"""
        print("[DEBUG] TTS 워커가 자체적으로 피드백을 처리합니다")
        # UniversalTTS가 자체적으로 피드백을 처리하므로 별도 작업 불필요
    
    def stop_tts(self):
        """TTS 정리 - 메인 스레드에서 실행"""
        # TTS 워커 정리
        if self.tts_worker:
            self.tts_worker.running = False
            self.tts_worker.stop()

class ExerciseAnalyzerThread(QThread):
    """운동 분석을 위한 스레드 - 젯슨 ARM64 안정성 강화"""
    # PySide6 Signal 사용 (pyqtSignal → Signal)
    analysis_finished = Signal(str, str, str, dict, dict)  # video_path, report_path, json_path, json_data, api_result
    error_occurred = Signal(str)
    status_updated = Signal(str)
    frame_processed = Signal(np.ndarray)  # 처리된 프레임을 GUI로 전달

    def __init__(self, exercise_type, duration_seconds, api_client=None):
        super().__init__()
        self.exercise_type = exercise_type
        self.duration_seconds = duration_seconds
        self.api_client = api_client
        self.running = True
        self.mutex = QMutex()

    def run(self):
        """안전한 분석 실행"""
        try:
            # 메모리 정리
            import gc
            gc.collect()

            print(f"[DEBUG] 분석 스레드 시작: {self.exercise_type}")
            video_path, report_path, result = None, None, None

            # 안전한 모듈 import 및 실행
            if self.exercise_type == "squat":
                self.status_updated.emit("스쿼트 분석 모듈 로드 중...")

                try:
                    # 동적 import로 메모리 충돌 방지
                    import importlib
                    import sys
                    
                    # PyInstaller 환경에서 모듈 경로 처리
                    try:
                        # 모듈이 이미 로드되어 있다면 재로드
                        if 'squat_real_tts' in sys.modules:
                            squat_module = sys.modules['squat_real_tts']
                            importlib.reload(squat_module)
                        else:
                            squat_module = importlib.import_module('squat_real_tts')
                    except ImportError as import_err:
                        # PyInstaller 환경에서 모듈을 찾지 못하는 경우
                        print(f"[ERROR] squat_real_tts 모듈 import 실패: {import_err}")
                        print(f"[DEBUG] sys.path: {sys.path}")
                        print(f"[DEBUG] sys.modules에 있는 모듈들: {[m for m in sys.modules.keys() if 'squat' in m]}")
                        # 직접 import 시도
                        try:
                            import squat_real_tts as squat_module
                        except Exception as e2:
                            raise ImportError(f"squat_real_tts를 찾을 수 없습니다: {e2}")

                    self.status_updated.emit("스쿼트 분석 시작...")

                    # 함수가 존재하는지 확인
                    if hasattr(squat_module, 'run_squat_analysis'):
                        result = squat_module.run_squat_analysis(
                            self.duration_seconds, self.should_stop, self.frame_callback, is_gui_mode=True, api_client=self.api_client
                        )
                        if result:
                            video_path, report_path = result[0], result[1]
                    else:
                        self.error_occurred.emit("분석 함수(run_squat_analysis)를 찾을 수 없습니다.")
                        return

                except ImportError as e:
                    self.error_occurred.emit(f"스쿼트 모듈 로드 실패: {str(e)}")
                    return
                except Exception as e:
                    self.error_occurred.emit(f"스쿼트 분석 실행 오류: {str(e)}")
                    return

            elif self.exercise_type == "lunge":
                self.status_updated.emit("런지 분석 모듈 로드 중...")
                try:
                    # 동적 import로 메모리 충돌 방지 (스쿼트와 동일한 방식)
                    import importlib
                    import sys

                    # PyInstaller 환경에서 모듈 경로 처리
                    try:
                        if 'lunge_realtime' in sys.modules:
                            lunge_module = sys.modules['lunge_realtime']
                            importlib.reload(lunge_module)
                        else:
                            lunge_module = importlib.import_module('lunge_realtime')
                    except ImportError as import_err:
                        print(f"[ERROR] lunge_realtime 모듈 import 실패: {import_err}")
                        try:
                            import lunge_realtime as lunge_module
                        except Exception as e2:
                            raise ImportError(f"lunge_realtime을 찾을 수 없습니다: {e2}")

                    self.status_updated.emit("런지 분석 시작...")

                    # 함수가 존재하는지 확인 (스쿼트와 동일한 방식)
                    if hasattr(lunge_module, 'run_lunge_analysis'):
                        result = lunge_module.run_lunge_analysis(
                            self.duration_seconds, self.should_stop, self.frame_callback, is_gui_mode=True, api_client=self.api_client
                        )
                        if result:
                            video_path, report_path = result[0], result[1]
                    else:
                        self.error_occurred.emit("분석 함수(run_lunge_analysis)를 찾을 수 없습니다.")
                        return

                except ImportError as e:
                    self.error_occurred.emit(f"런지 모듈(lunge_realtime.py) 로드 실패: {str(e)}")
                    return
                except Exception as e:
                    self.error_occurred.emit(f"런지 분석 실행 오류: {str(e)}")
                    return

            elif self.exercise_type == "plank":
                self.status_updated.emit("플랭크 분석 모듈 로드 중...")
                try:
                    # 동적 import로 메모리 충돌 방지
                    import importlib
                    import sys

                    # PyInstaller 환경에서 모듈 경로 처리
                    try:
                        if 'plank' in sys.modules:
                            plank_module = sys.modules['plank']
                            importlib.reload(plank_module)
                        else:
                            plank_module = importlib.import_module('plank')
                    except ImportError as import_err:
                        print(f"[ERROR] plank 모듈 import 실패: {import_err}")
                        try:
                            import plank as plank_module
                        except Exception as e2:
                            raise ImportError(f"plank을 찾을 수 없습니다: {e2}")

                    self.status_updated.emit("플랭크 분석 시작...")

                    # plank.py에 있는 분석 함수 이름을 'run_plank_analysis'로 가정합니다.
                    # 만약 함수 이름이 다르다면 이 부분을 수정해야 합니다.
                    if hasattr(plank_module, 'run_plank_analysis'):
                        result = plank_module.run_plank_analysis(
                            self.duration_seconds, self.should_stop, self.frame_callback, is_gui_mode=True, api_client=self.api_client
                        )
                        if result:
                            video_path, report_path = result[0], result[1]
                    else:
                        self.error_occurred.emit("분석 함수(run_plank_analysis)를 찾을 수 없습니다.")
                        return

                except ImportError as e:
                    self.error_occurred.emit(f"플랭크 모듈(plank.py) 로드 실패: {str(e)}")
                    return
                except Exception as e:
                    self.error_occurred.emit(f"플랭크 분석 실행 오류: {str(e)}")
                    return
            else:
                self.error_occurred.emit("알 수 없는 운동 타입입니다.")
                return

            if not self.running:
                print("[DEBUG] 분석이 중지되었습니다.")
                return

            if video_path and report_path and result:
                # API 결과도 함께 전달
                json_path = result[2] if len(result) > 2 else None
                json_data = result[3] if len(result) > 3 else None
                api_result = result[4] if len(result) > 4 else None
                self.analysis_finished.emit(video_path, report_path, json_path, json_data, api_result)
            else:
                self.error_occurred.emit("분석이 알 수 없는 이유로 실패했습니다.")

        except Exception as e:
            if not self.running:
                return
            print(f"[ERROR] 분석 스레드 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"분석 중 오류 발생: {str(e)}")
        finally:
            # 메모리 정리
            import gc
            gc.collect()
            print("[DEBUG] 분석 스레드 종료 및 메모리 정리")

    def frame_callback(self, processed_frame):
        """처리된 프레임을 GUI로 전달하는 콜백 - 안전성 강화"""
        try:
            if not self.running:
                return

            self.mutex.lock()
            try:
                if processed_frame is not None and processed_frame.size > 0:
                    # 안전한 복사본 생성
                    frame_copy = processed_frame.copy()
                    # BGR을 RGB로 변환하여 전달
                    rgb_frame = cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB)
                    self.frame_processed.emit(rgb_frame)
            finally:
                self.mutex.unlock()
        except Exception as e:
            print(f"frame_callback 오류: {e}")

    def should_stop(self):
        """중지 여부 확인"""
        return not self.running

    def stop(self):
        """안전한 스레드 중지"""
        print("[DEBUG] 분석 스레드 중지 요청")
        self.mutex.lock()
        self.running = False
        self.mutex.unlock()

        # 즉시 중지 신호
        self.quit()
        
        # 짧은 대기 후 강제 종료
        if not self.wait(2000):  # 2초 대기
            print("[WARNING] 분석 스레드 강제 종료")
            self.terminate()
            self.wait(1000)


class CameraThread(QThread):
    """실시간 카메라 피드를 위한 스레드 (젯슨 ARM64 안정성 강화)"""
    # PySide6 Signal 사용 (pyqtSignal → Signal)
    frame_ready = Signal(np.ndarray)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        self.mutex = QMutex()  # 스레드 안전성

    def run(self):
        try:
            # 젯슨에서 안전한 카메라 초기화 (Linux 최적화)
            # 젯슨에서는 V4L2 백엔드 사용
            self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)  # 젯슨용 백엔드

            if not self.cap.isOpened():
                # 백업 방법으로 다시 시도
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    self.error_occurred.emit("카메라를 열 수 없습니다.")
                    return

            # 젯슨 최적화 카메라 설정 (딜레이 최소화)
            try:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 원래 해상도 유지
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  # 원래 해상도 유지
                self.cap.set(cv2.CAP_PROP_FPS, 15)  # 30 -> 15로 낮춰서 딜레이 감소
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 크기 최소화
                # 젯슨 특화 설정
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                # 추가 딜레이 최소화 설정
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # 자동 포커스 비활성화
                self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 자동 노출 최소화
            except Exception as e:
                print(f"카메라 설정 경고: {e}")

            frame_count = 0
            while self.running:
                try:
                    self.mutex.lock()
                    if not self.running:
                        self.mutex.unlock()
                        break

                    ret, frame = self.cap.read()
                    self.mutex.unlock()

                    if not ret or frame is None:
                        print("프레임 읽기 실패")
                        time.sleep(0.1)
                        continue

                    # 프레임 유효성 검사
                    if frame.size == 0 or len(frame.shape) != 3:
                        print("잘못된 프레임 형식")
                        continue

                    # 안전한 색상 변환
                    try:
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        if rgb_frame is not None and rgb_frame.size > 0:
                            self.frame_ready.emit(rgb_frame.copy())  # 안전한 복사본 전달
                    except Exception as e:
                        print(f"색상 변환 오류: {e}")
                        continue

                    frame_count += 1
                    if frame_count % 30 == 0:  # 30프레임마다 디버그
                        print(f"[DEBUG] 카메라 프레임 {frame_count} 처리됨")

                except Exception as e:
                    print(f"프레임 처리 오류: {e}")
                    if self.mutex.tryLock():
                        self.mutex.unlock()

                time.sleep(0.066)  # 약 15 FPS (딜레이 최소화)

        except Exception as e:
            self.error_occurred.emit(f"카메라 스레드 오류: {str(e)}")
        finally:
            self.cleanup()

    def cleanup(self):
        """안전한 리소스 정리"""
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
            print("[DEBUG] 카메라 리소스 정리 완료")
        except Exception as e:
            print(f"카메라 정리 오류: {e}")

    def stop(self):
        """안전한 스레드 정지"""
        print("[DEBUG] 카메라 스레드 정지 요청")
        self.mutex.lock()
        self.running = False
        self.mutex.unlock()

        self.cleanup()
        self.quit()
        
        # 짧은 대기 후 강제 종료
        if not self.wait(2000):  # 2초 대기
            print("[WARNING] 카메라 스레드 강제 종료")
            self.terminate()
            self.wait(1000)


class MainWindow(QWidget):
    """메인 윈도우 - PySide6 버전 (QWidget으로 변경하여 QStackedWidget에 추가 가능하도록)"""
    # 토큰 설정 화면으로 돌아가기 시그널
    go_to_token_screen = Signal()
    
    def __init__(self, access_token=None):
        super().__init__()
        # QMainWindow 대신 QWidget을 사용하므로 setWindowTitle 대신 변수로 저장
        self.window_title = "Re:PiT - 운동 자세 분석 시스템"
        
        # QWidget에는 setWindowIcon이 없으므로 제거 (부모 윈도우에서 설정됨)

        # 변수 초기화
        self.duration_seconds = 60
        self.selected_exercise = None
        self.analyzer_thread = None
        self.camera_thread = None
        self.is_analyzing = False
        self.tts_manager = None
        
        # API 관련 변수
        self.access_token = access_token
        self.api_client = None
        
        try:
            if self.access_token:
                self.api_client = RepitAPIClient(access_token=self.access_token)
        except Exception as e:
            print(f"[WARNING] API 클라이언트 생성 실패: {e}")

        # 경과 시간 타이머
        self.elapsed_time = 0
        self.analysis_timer = QTimer(self)
        self.analysis_timer.timeout.connect(self.update_timer_display)

        try:
            print("[DEBUG] init_ui 시작...")
            self.init_ui()
            print("[DEBUG] init_ui 완료")
        except Exception as e:
            print(f"[ERROR] init_ui 실패: {e}")
            import traceback
            traceback.print_exc()
            # UI는 최소한으로라도 표시되도록 함
            try:
                error_label = QLabel(f"UI 초기화 오류: {str(e)}\n\n앱을 재시작해주세요.")
                error_layout = QVBoxLayout(self)
                error_layout.addWidget(error_label)
            except:
                pass
            return
        
        try:
            print("[DEBUG] start_camera 시작...")
            self.start_camera()
            print("[DEBUG] start_camera 완료")
        except Exception as e:
            print(f"[WARNING] 카메라 시작 실패 (계속 진행): {e}")
            import traceback
            traceback.print_exc()
            # 카메라는 선택사항이므로 실패해도 계속 진행

    def init_ui(self):
        """UI 초기화"""
        # QWidget에서는 직접 레이아웃 설정 (setCentralWidget 없음)
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        # 왼쪽 패널
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # 오른쪽 패널
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)

    def create_left_panel(self):
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.Shape.Box)
        left_layout = QVBoxLayout(left_panel)

        # 운동 선택 그룹
        exercise_group = QGroupBox("운동 선택")
        exercise_layout = QVBoxLayout(exercise_group)

        self.squat_button = QPushButton("SQUAT")
        self.lunge_button = QPushButton("LUNGE")
        self.plank_button = QPushButton("PLANK")

        self.squat_button.setCheckable(True)
        self.lunge_button.setCheckable(True)
        self.plank_button.setCheckable(True)

        self.squat_button.clicked.connect(lambda: self.select_exercise("squat"))
        self.lunge_button.clicked.connect(lambda: self.select_exercise("lunge"))
        self.plank_button.clicked.connect(lambda: self.select_exercise("plank"))

        exercise_layout.addWidget(self.squat_button)
        exercise_layout.addWidget(self.lunge_button)
        exercise_layout.addWidget(self.plank_button)
        left_layout.addWidget(exercise_group)

        # 설정 그룹
        settings_group = QGroupBox("분석 설정")
        settings_layout = QVBoxLayout(settings_group)

        duration_label = QLabel("분석 시간 (초):")
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setRange(5, 600)
        self.duration_spinbox.setValue(60)
        self.duration_spinbox.valueChanged.connect(self.update_duration)

        settings_layout.addWidget(duration_label)
        settings_layout.addWidget(self.duration_spinbox)
        left_layout.addWidget(settings_group)

        # 제어 그룹
        control_group = QGroupBox("분석 제어")
        control_layout = QVBoxLayout(control_group)

        self.start_button = QPushButton("분석 시작")
        self.stop_button = QPushButton("분석 중지")
        self.stop_button.setEnabled(False)

        self.start_button.clicked.connect(self.start_analysis)
        self.stop_button.clicked.connect(self.stop_analysis)

        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        left_layout.addWidget(control_group)

        # 타이머 라벨
        self.timer_label = QLabel("경과 시간: 0초")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; margin-top: 10px; }")
        left_layout.addWidget(self.timer_label)

        # 상태 라벨
        self.status_label = QLabel("대기 중...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel { 
                background-color: #2d2d2d; 
                color: #ffffff; 
                padding: 10px; 
                border: 1px solid #555555; 
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        left_layout.addWidget(self.status_label)

        left_layout.addStretch()

        # 토큰 설정 버튼
        token_settings_group = QGroupBox("계정 설정")
        token_settings_layout = QVBoxLayout(token_settings_group)
        
        self.token_button = QPushButton("🔑 토큰 설정")
        self.token_button.setMinimumHeight(35)
        self.token_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border: 1px solid #adb5bd;
            }
        """)
        self.token_button.clicked.connect(self.go_to_token_settings)
        token_settings_layout.addWidget(self.token_button)
        
        # 토큰 상태 표시
        self.token_status_label = QLabel()
        self.update_token_status_display()
        self.token_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.token_status_label.setStyleSheet("QLabel { font-size: 11px; color: #6c757d; padding: 5px; }")
        token_settings_layout.addWidget(self.token_status_label)
        
        left_layout.addWidget(token_settings_group)

        self.update_button_styles()
        return left_panel

    def create_right_panel(self):
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.Shape.Box)
        right_layout = QVBoxLayout(right_panel)

        # 카메라 그룹
        camera_group = QGroupBox("실시간 카메라")
        camera_layout = QVBoxLayout(camera_group)

        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setStyleSheet("QLabel { background-color: #000000; border: 1px solid #ccc; }")
        self.camera_label.setText("카메라 초기화 중...")

        camera_layout.addWidget(self.camera_label)
        right_layout.addWidget(camera_group)

        # 결과 그룹
        result_group = QGroupBox("분석 결과")
        result_layout = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(150)

        result_layout.addWidget(self.result_text)
        right_layout.addWidget(result_group)

        return right_panel

    def start_camera(self):
        """카메라 시작"""
        if self.camera_thread and self.camera_thread.isRunning():
            print("[DEBUG] 기존 카메라 스레드가 실행 중입니다. 새로 시작하지 않습니다.")
            return

        try:
            self.camera_thread = CameraThread()
            self.camera_thread.frame_ready.connect(self.update_camera_frame)
            self.camera_thread.error_occurred.connect(self.on_camera_error)
            self.camera_thread.start()
        except Exception as e:
            self.on_camera_error(f"카메라 시작 실패: {str(e)}")

    def _stop_camera_thread(self, wait_ms=5000):
        """카메라 스레드를 안전하게 중지"""
        if not self.camera_thread:
            return

        try:
            print("[DEBUG] 카메라 스레드 종료 대기...")
            self.camera_thread.stop()
            if not self.camera_thread.wait(wait_ms):
                print("[WARNING] 카메라 스레드가 종료 대기 시간 내에 끝나지 않아 강제 종료합니다.")
                self.camera_thread.terminate()
                self.camera_thread.wait(1000)
        except Exception as e:
            print(f"[WARNING] 카메라 스레드 중지 중 오류: {e}")
        finally:
            try:
                self.camera_thread.deleteLater()
            except Exception:
                pass
            self.camera_thread = None

    def _stop_analyzer_thread(self, wait_ms=5000):
        """분석 스레드를 안전하게 중지"""
        if not self.analyzer_thread:
            return

        try:
            print("[DEBUG] 분석 스레드 종료 대기...")
            self.analyzer_thread.stop()
            if not self.analyzer_thread.wait(wait_ms):
                print("[WARNING] 분석 스레드가 종료 대기 시간 내에 끝나지 않아 강제 종료합니다.")
                self.analyzer_thread.terminate()
                self.analyzer_thread.wait(1000)
        except Exception as e:
            print(f"[WARNING] 분석 스레드 중지 중 오류: {e}")
        finally:
            try:
                self.analyzer_thread.deleteLater()
            except Exception:
                pass
            self.analyzer_thread = None

    def update_camera_frame(self, frame):
        """카메라 프레임 업데이트"""
        try:
            # 안전한 프레임 처리
            if frame is None or frame.size == 0:
                return

            # 카메라 프레임을 거울모드로 표시 (운동 분석 시작 전 구도 맞추기용)
            frame = cv2.flip(frame, 1)

            h, w, ch = frame.shape

            # 안전한 메모리 접근
            if h <= 0 or w <= 0 or ch <= 0:
                return

            bytes_per_line = ch * w

            # QImage 생성 시 안전장치 (PySide6 호환)
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

            if qt_image.isNull():
                return

            pixmap = QPixmap.fromImage(qt_image)

            if pixmap.isNull():
                return

            # 라벨 크기 확인
            label_size = self.camera_label.size()
            if label_size.width() <= 0 or label_size.height() <= 0:
                return

            scaled_pixmap = pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.camera_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"프레임 업데이트 오류: {e}")
            import traceback
            traceback.print_exc()

    def on_camera_error(self, error_msg):
        """카메라 에러 처리"""
        self.camera_label.setText(f"카메라 오류: {error_msg}")
        self.status_label.setText("카메라 연결 실패")

    def update_duration(self, value):
        """분석 시간 업데이트"""
        self.duration_seconds = value

    def select_exercise(self, exercise_type):
        """운동 선택"""
        self.selected_exercise = exercise_type

        # 버튼 상태 업데이트
        buttons = {
            "squat": self.squat_button,
            "lunge": self.lunge_button,
            "plank": self.plank_button
        }

        for type_name, button in buttons.items():
            button.setChecked(type_name == exercise_type)

        self.update_button_styles()

        # 상태 메시지 업데이트
        exercise_names = {"squat": "스쿼트", "lunge": "런지", "plank": "플랭크"}
        self.status_label.setText(f"{exercise_names.get(exercise_type, '')} 분석 준비됨")

        # 기본 시간 설정
        default_duration = 60
        self.duration_spinbox.setValue(default_duration)

    def update_button_styles(self):
        """버튼 스타일 업데이트"""
        buttons = [self.squat_button, self.lunge_button, self.plank_button]

        for button in buttons:
            if button.isChecked():
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #808080;
                        color: white;
                        border: 2px solid #666666;
                        border-radius: 8px;
                        padding: 15px;
                        font-weight: bold;
                        font-size: 14px;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        color: #333333;
                        border: 2px solid #cccccc;
                        border-radius: 8px;
                        padding: 15px;
                        font-weight: bold;
                        font-size: 14px;
                    }
                """)

    def start_analysis(self):
        """분석 시작 - 젯슨 ARM64 안정성 강화"""
        if not self.selected_exercise:
            QMessageBox.warning(self, "경고", "운동을 선택해주세요.")
            return

        try:
            # 분석 중 상태로 변경
            self.is_analyzing = True

            # 카메라 안전하게 중지
            print("[DEBUG] 카메라 스레드 중지 시작...")
            self._stop_camera_thread()

            self.camera_label.setText("분석 준비 중... 잠시 기다려주세요.")

            # 메모리 정리
            import gc
            gc.collect()

            # 약간의 지연으로 메모리 안정화
            QTimer.singleShot(1000, self._start_analysis_delayed)

        except Exception as e:
            print(f"분석 시작 준비 오류: {e}")
            self.on_analysis_error(f"분석 시작 준비 중 오류: {str(e)}")

    def _start_analysis_delayed(self):
        """지연된 분석 시작 - 메모리 안정화 후"""
        try:
            # 타이머 초기화 및 시작
            self.elapsed_time = 0
            self.timer_label.setText("경과 시간: 0초")
            self.analysis_timer.start(1000)

            # 분석 스레드 시작 (안전한 지연 시작)
            duration = self.duration_spinbox.value()
            self.analyzer_thread = ExerciseAnalyzerThread(self.selected_exercise, duration, api_client=self.api_client)

            self.analyzer_thread.status_updated.connect(self.update_status)
            self.analyzer_thread.analysis_finished.connect(self.on_analysis_finished)
            self.analyzer_thread.error_occurred.connect(self.on_analysis_error)
            self.analyzer_thread.frame_processed.connect(self.update_camera_frame)

            # TTS 매니저 생성 (메인 스레드에서)
            self.tts_manager = TTSManager(self.selected_exercise)
            # TTS는 자체적으로 처리되므로 시그널 연결 불필요
            
            self.analyzer_thread.start()

            # UI 상태 업데이트
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("분석이 시작되었습니다...")

        except Exception as e:
            print(f"지연된 분석 시작 오류: {e}")
            self.on_analysis_error(f"분석 시작 오류: {str(e)}")

    def stop_analysis(self, finished_naturally=False):
        """분석 중지"""
        # TTS 매니저 정리
        if hasattr(self, 'tts_manager') and self.tts_manager:
            self.tts_manager.stop_tts()
            self.tts_manager = None
        
        # 분석 스레드 중지
        self._stop_analyzer_thread()

        # 상태 초기화
        self.is_analyzing = False
        self.analysis_timer.stop()

        # 카메라 재시작
        self.start_camera()

        # UI 상태 복원
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        if not finished_naturally:
            self.status_label.setText("분석이 중지되었습니다.")

    def update_status(self, status_msg):
        """상태 업데이트"""
        self.status_label.setText(status_msg)

    def on_analysis_finished(self, video_path, report_path, json_path=None, json_data=None, api_result=None):
        """분석 완료 처리"""
        self.stop_analysis(finished_naturally=True)

        # 결과 요약
        summary = f"""분석 완료!

📹 비디오: {os.path.basename(video_path)}
📄 리포트: {os.path.basename(report_path)}
📁 위치: {os.path.dirname(video_path)}
"""
        server_status_lines = []
        
        # API 전송 결과 처리
        delete_candidates = []

        if api_result is not None:
            token_missing = not self.access_token
            if api_result.get("success", False):
                # API 전송 성공
                video_status = ""
                video_upload_info = api_result.get("video_upload")
                if video_upload_info:
                    if video_upload_info.get("success"):
                        video_status = "\n영상 업로드 및 확정이 완료되었습니다."
                        server_status_lines.append("• 영상 업로드: 성공")
                    else:
                        video_status = f"\n영상 업로드 실패: {video_upload_info.get('message', '사유 미상')}"
                        server_status_lines.append(f"• 영상 업로드: 실패 ({video_upload_info.get('message', '사유 미상')})")
                else:
                    server_status_lines.append("• 영상 업로드: 응답에 정보가 없어 미확인")
                
                QMessageBox.information(
                    self,
                    "전송 완료",
                    "운동 기록이 서버에 성공적으로 저장되었습니다.\n"
                    "📹 비디오와 📄 리포트는 로컬에도 저장되었습니다."
                    f"{video_status}"
                )
                if api_result.get("data", {}).get("result", {}).get("record_id"):
                    record_id = api_result["data"]["result"]["record_id"]
                    print(f"✅ 저장된 기록 ID: {record_id}")
                    server_status_lines.insert(0, f"• 운동 기록: 성공 (record_id={record_id})")
                else:
                    server_status_lines.insert(0, "• 운동 기록: 성공 (record_id 미응답)")

                # 로컬 파일 정리 조건: 영상 업로드까지 성공했을 때만
                if video_upload_info and video_upload_info.get("success"):
                    delete_candidates = [video_path, report_path, json_path]
            else:
                # API 전송 실패
                error_message = api_result.get("message") or "알 수 없는 오류"
                video_upload_info = api_result.get("video_upload")

                token_related_failure = token_missing or ("토큰" in error_message)
                generic_failure = error_message.strip() in ("", "알 수 없는 오류", "Unknown error")

                if token_related_failure or generic_failure and token_missing:
                    info_message = (
                        "토큰 정보를 확인할 수 없어 서버 전송을 생략했습니다.\n"
                        "📹 비디오와 📄 리포트는 로컬에만 저장됩니다."
                    )
                    QMessageBox.information(self, "전송 생략", info_message)
                    server_status_lines.append("• 운동 기록: 토큰 미설정으로 전송 생략")
                else:
                    QMessageBox.warning(
                        self,
                        "전송 실패",
                        f"운동 기록 서버 전송에 실패했습니다.\n\n"
                        f"오류: {error_message}\n\n"
                        f"📹 비디오와 📄 리포트는 로컬에 저장되었습니다."
                    )
                    server_status_lines.append(f"• 운동 기록: 실패 ({error_message})")

                if video_upload_info:
                    if video_upload_info.get("success"):
                        server_status_lines.append("• 영상 업로드: 성공")
                    else:
                        server_status_lines.append(f"• 영상 업로드: 실패 ({video_upload_info.get('message', '사유 미상')})")
        elif not self.access_token:
            message = (
                "토큰을 입력하지 않아 서버 전송을 생략했습니다.\n"
                "📹 비디오와 📄 리포트는 로컬에만 저장됩니다."
            )
            QMessageBox.information(self, "전송 생략", message)
            print("ℹ️  토큰이 없어 로컬에만 저장됩니다.")
            server_status_lines.append("• 운동 기록: 토큰 미설정으로 전송 생략")
            server_status_lines.append("• 영상 업로드: 토큰 미설정으로 생략")
        else:
            # 토큰은 있으나 api_result 자체가 None인 경우
            server_status_lines.append("• 운동 기록: 전송 정보를 확인할 수 없습니다.")
        
        # 리포트 내용 읽기
        report_content = ""
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
        except Exception as e:
            report_content = f"리포트 파일을 읽을 수 없습니다: {e}"
        
        # 로컬 파일 삭제 (필요 시)
        deleted_files = []
        if delete_candidates:
            for file_path in delete_candidates:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        deleted_files.append(file_path)
                        print(f"🧹 서버 전송 성공으로 로컬 파일 삭제: {file_path}")
                    except Exception as e:
                        print(f"⚠️ 로컬 파일 삭제 실패 ({file_path}): {e}")
            if deleted_files:
                server_status_lines.append("• 로컬 파일: 서버 전송 성공으로 자동 삭제")

        server_status_section = ""
        if server_status_lines:
            server_status_section = (
                "\n" + "=" * 50 + "\n서버 전송 상태\n" + "=" * 50 + "\n"
                + "\n".join(server_status_lines) + "\n"
            )
        
        full_result = (
            summary
            + server_status_section
            + "\n" + "="*50 + "\n상세 분석 결과\n" + "="*50 + "\n\n"
            + report_content
        )
        self.result_text.setText(full_result)

        # 상태 업데이트
        self.status_label.setText("분석 완료!")
    

    def on_analysis_error(self, error_msg):
        """분석 오류 처리"""
        self.stop_analysis(finished_naturally=True)

        self.result_text.setText(f"분석 오류: {error_msg}")
        self.status_label.setText("분석 실패")

        QMessageBox.critical(
            self,
            "오류",
            f"분석 중 오류가 발생했습니다:\n{error_msg}"
        )

    def update_timer_display(self):
        """타이머 표시 업데이트"""
        self.elapsed_time += 1
        self.timer_label.setText(f"경과 시간: {self.elapsed_time}초")
    
    def go_to_token_settings(self):
        """토큰 설정 화면으로 이동"""
        if self.is_analyzing:
            QMessageBox.warning(
                self,
                "분석 진행 중",
                "운동 분석이 진행 중입니다.\n분석을 먼저 중지해주세요."
            )
            return
        
        # 시그널 발생
        self.go_to_token_screen.emit()
    
    def update_token_status_display(self):
        """토큰 상태 표시 업데이트"""
        if self.access_token:
            # 토큰의 처음 4자와 마지막 4자만 표시
            if len(self.access_token) > 8:
                masked_token = f"{self.access_token[:4]}...{self.access_token[-4:]}"
            else:
                masked_token = "****"
            self.token_status_label.setText(f"✅ 토큰: {masked_token}")
        else:
            self.token_status_label.setText("⚠️ 토큰 미설정 (로컬 저장만)")
    
    def set_access_token(self, token):
        """액세스 토큰 설정"""
        self.access_token = token
        self.update_token_status_display()
        print(f"✅ 액세스 토큰 설정됨 (길이: {len(token) if token else 0})")

    def closeEvent(self, event):
        """애플리케이션 종료 시 정리 - 강력한 스레드 정리"""
        try:
            print("[DEBUG] 애플리케이션 종료 시작...")
            
            # 분석 중이면 먼저 중지
            if self.is_analyzing:
                print("[DEBUG] 분석 중지 중...")
                self.stop_analysis(finished_naturally=False)
            
            # TTS 매니저 정리
            if hasattr(self, 'tts_manager') and self.tts_manager:
                try:
                    print("[DEBUG] TTS 매니저 정리 중...")
                    self.tts_manager.stop_tts()
                    self.tts_manager = None
                except Exception as e:
                    print(f"[WARNING] TTS 정리 중 오류: {e}")
            
            # 카메라 스레드 강력 정리
            if hasattr(self, 'camera_thread') and self.camera_thread:
                try:
                    print("[DEBUG] 카메라 스레드 강력 정리 중...")
                self._stop_camera_thread(wait_ms=2000)
                    print("[DEBUG] 카메라 스레드 정리 완료")
                except Exception as e:
                    print(f"[WARNING] 카메라 스레드 정리 중 오류: {e}")
            
            # 분석 스레드 강력 정리
            if hasattr(self, 'analyzer_thread') and self.analyzer_thread:
                try:
                    print("[DEBUG] 분석 스레드 강력 정리 중...")
                self._stop_analyzer_thread(wait_ms=2000)
                    print("[DEBUG] 분석 스레드 정리 완료")
                except Exception as e:
                    print(f"[WARNING] 분석 스레드 정리 중 오류: {e}")

            # 타이머 정리
            if hasattr(self, 'analysis_timer') and self.analysis_timer:
                try:
                    if self.analysis_timer.isActive():
                        self.analysis_timer.stop()
                    self.analysis_timer.deleteLater()
                    print("[DEBUG] 타이머 정리 완료")
                except Exception as e:
                    print(f"[WARNING] 타이머 정리 중 오류: {e}")
            
            # Qt 이벤트 처리 (스레드 정리 완료 대기)
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            
            # 메모리 정리
            import gc
            gc.collect()
            
            print("[DEBUG] 애플리케이션 종료 완료")
            
        except Exception as e:
            print(f"[ERROR] 종료 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 어떤 경우든 이벤트 수락
            event.accept()


def main():
    """메인 함수 - 젯슨 ARM64 안정성 강화"""
    # 젯슨에서 안전한 멀티프로세싱 설정
    import multiprocessing
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass  # 이미 설정된 경우

    try:
        app = QApplication(sys.argv)

        # 젯슨 특수 설정
        app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True)
        app.setStyle('Fusion')  # 안정한 스타일

        # 메모리 관리 강화
        import gc
        gc.set_threshold(700, 10, 10)  # 더 자주 가비지 컬렉션

        print("[DEBUG] 토큰 입력 위젯 생성 중...")
        from token_input_widget import TokenInputWidget
        
        token_widget = TokenInputWidget()
        
        def on_token_submitted(token):
            print(f"[DEBUG] 토큰 입력 완료: {token[:10]}...")
            token_widget.close()
            
            print("[DEBUG] 메인 윈도우 생성 중...")
            window = MainWindow(access_token=token)
            window.show()
        
        def on_continue_without_token():
            print("[DEBUG] 토큰 없이 계속하기")
            token_widget.close()
            
            print("[DEBUG] 메인 윈도우 생성 중...")
            window = MainWindow(access_token=None)
            window.show()
        
        token_widget.token_submitted.connect(on_token_submitted)
        token_widget.continue_without_token.connect(on_continue_without_token)
        
        print("[DEBUG] 토큰 입력 화면 표시...")
        token_widget.show()

        # 안전한 종료 핸들러
        def safe_exit():
            print("[DEBUG] 안전한 종료 시작...")
            try:
                if hasattr(window, 'camera_thread') and window.camera_thread:
                    window.camera_thread.stop()
                if hasattr(window, 'analyzer_thread') and window.analyzer_thread:
                    window.analyzer_thread.stop()

                # 메모리 정리
                gc.collect()
                print("[DEBUG] 리소스 정리 완료")
            except Exception as e:
                print(f"종료 중 오류: {e}")

        import signal
        def signal_handler(sig, frame):
            print(f"[DEBUG] 신호 {sig} 수신됨")
            safe_exit()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        print("[DEBUG] 애플리케이션 실행...")
        # PySide6에서는 exec() 메서드 사용 (PyQt5의 exec_()에서 변경)
        result = app.exec()

        safe_exit()
        sys.exit(result)

    except Exception as e:
        print(f"메인 함수 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 