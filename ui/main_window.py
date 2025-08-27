#!/usr/bin/env python3
"""
운동 자세 분석 메인 윈도우 UI
PyQt5를 사용하여 젯슨에서 실행 가능한 GUI 애플리케이션
"""

import sys
import os
import time
import threading

# macOS Segmentation fault 방지를 위한 환경변수 설정
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
os.environ['OPENCV_VIDEOIO_DEBUG'] = '1'
os.environ['QT_MAC_WANTS_LAYER'] = '1'

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGroupBox,
                             QSpinBox, QTextEdit, QMessageBox, QFrame)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QMutex
from PyQt5.QtGui import QPixmap, QImage, QFont
import cv2
import numpy as np

# OpenCV 백엔드 설정 (macOS 안정성 향상)
try:
    cv2.setUseOptimized(True)
    cv2.setNumThreads(4)
except:
    pass

class ExerciseAnalyzerThread(QThread):
    """운동 분석을 위한 스레드 - macOS 안정성 강화"""
    analysis_finished = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)
    status_updated = pyqtSignal(str)
    frame_processed = pyqtSignal(np.ndarray)  # 처리된 프레임을 GUI로 전달

    def __init__(self, exercise_type, duration_seconds):
        super().__init__()
        self.exercise_type = exercise_type
        self.duration_seconds = duration_seconds
        self.running = True
        self.mutex = QMutex()

    def run(self):
        """안전한 분석 실행"""
        try:
            # 메모리 정리
            import gc
            gc.collect()

            print(f"[DEBUG] 분석 스레드 시작: {self.exercise_type}")
            video_path, report_path = None, None

            # 안전한 모듈 import 및 실행
            if self.exercise_type == "squat":
                self.status_updated.emit("스쿼트 분석 모듈 로드 중...")

                try:
                    # 동적 import로 메모리 충돌 방지
                    import importlib
                    import sys

                    # 모듈이 이미 로드되어 있다면 재로드
                    if 'squat_real_tts' in sys.modules:
                        squat_module = sys.modules['squat_real_tts']
                        importlib.reload(squat_module)
                    else:
                        squat_module = importlib.import_module('squat_real_tts')

                    self.status_updated.emit("스쿼트 분석 시작...")

                    # 함수가 존재하는지 확인
                    if hasattr(squat_module, 'run_squat_analysis'):
                        video_path, report_path = squat_module.run_squat_analysis(
                            self.duration_seconds, self.should_stop, self.frame_callback
                        )
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

                    if 'lunge_realtime' in sys.modules:
                        lunge_module = sys.modules['lunge_realtime']
                        importlib.reload(lunge_module)
                    else:
                        lunge_module = importlib.import_module('lunge_realtime')

                    self.status_updated.emit("런지 분석 시작...")

                    # 함수가 존재하는지 확인 (스쿼트와 동일한 방식)
                    if hasattr(lunge_module, 'run_lunge_analysis'):
                        video_path, report_path = lunge_module.run_lunge_analysis(
                            self.duration_seconds, self.should_stop, self.frame_callback
                        )
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

                    if 'plank' in sys.modules:
                        plank_module = sys.modules['plank']
                        importlib.reload(plank_module)
                    else:
                        plank_module = importlib.import_module('plank')

                    self.status_updated.emit("플랭크 분석 시작...")

                    # plank.py에 있는 분석 함수 이름을 'run_plank_analysis'로 가정합니다.
                    # 만약 함수 이름이 다르다면 이 부분을 수정해야 합니다.
                    if hasattr(plank_module, 'run_plank_analysis'):
                        video_path, report_path = plank_module.run_plank_analysis(
                            self.duration_seconds, self.should_stop, self.frame_callback
                        )
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

            if video_path and report_path:
                self.analysis_finished.emit(video_path, report_path)
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

        self.quit()
        self.wait(5000)  # 최대 5초 대기

# 이하 CameraThread, MainWindow 등 나머지 코드는 이전과 동일합니다.
# ... (생략) ...
# 전체 코드가 필요하시면 말씀해주세요. 여기서는 변경된 부분만 명확히 보여드립니다.
class CameraThread(QThread):
    """실시간 카메라 피드를 위한 스레드 (macOS 안정성 강화)"""
    frame_ready = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        self.mutex = QMutex()  # 스레드 안전성

    def run(self):
        try:
            # macOS에서 안전한 카메라 초기화
            self.cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)  # macOS 전용 백엔드

            if not self.cap.isOpened():
                # 백업 방법으로 다시 시도
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    self.error_occurred.emit("카메라를 열 수 없습니다.")
                    return

            # 안전한 카메라 설정
            try:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 크기 최소화
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

                time.sleep(0.033)  # 약 30 FPS

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
        self.wait(3000)  # 최대 3초 대기

class MainWindow(QMainWindow):
    """메인 윈도우"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("운동 자세 분석 시스템")
        self.setGeometry(100, 100, 1200, 800)

        # 변수 초기화
        self.duration_seconds = 60
        self.selected_exercise = None
        self.analyzer_thread = None
        self.camera_thread = None
        self.is_analyzing = False

        # 경과 시간 타이머
        self.elapsed_time = 0
        self.analysis_timer = QTimer(self)
        self.analysis_timer.timeout.connect(self.update_timer_display)

        self.init_ui()
        self.start_camera()

    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 왼쪽 패널
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # 오른쪽 패널
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)

    def create_left_panel(self):
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.Box)
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
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; margin-top: 10px; }")
        left_layout.addWidget(self.timer_label)

        # 상태 라벨
        self.status_label = QLabel("대기 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; }")
        left_layout.addWidget(self.status_label)

        left_layout.addStretch()

        self.update_button_styles()
        return left_panel

    def create_right_panel(self):
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.Box)
        right_layout = QVBoxLayout(right_panel)

        # 카메라 그룹
        camera_group = QGroupBox("실시간 카메라")
        camera_layout = QVBoxLayout(camera_group)

        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
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
        try:
            self.camera_thread = CameraThread()
            self.camera_thread.frame_ready.connect(self.update_camera_frame)
            self.camera_thread.error_occurred.connect(self.on_camera_error)
            self.camera_thread.start()
        except Exception as e:
            self.on_camera_error(f"카메라 시작 실패: {str(e)}")

    def update_camera_frame(self, frame):
        """카메라 프레임 업데이트"""
        # print(f"[DEBUG] update_camera_frame 호출됨: {frame.shape}")  # 디버깅
        try:
            # 안전한 프레임 처리
            if frame is None or frame.size == 0:
                # print("[DEBUG] 빈 프레임 수신")
                return

            # 카메라 프레임을 거울모드로 표시 (운동 분석 시작 전 구도 맞추기용)
            frame = cv2.flip(frame, 1)

            h, w, ch = frame.shape

            # 안전한 메모리 접근
            if h <= 0 or w <= 0 or ch <= 0:
                # print(f"[DEBUG] 잘못된 프레임 크기: {h}x{w}x{ch}")
                return

            bytes_per_line = ch * w

            # QImage 생성 시 안전장치
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)

            if qt_image.isNull():
                # print("[DEBUG] QImage 생성 실패")
                return

            pixmap = QPixmap.fromImage(qt_image)

            if pixmap.isNull():
                # print("[DEBUG] QPixmap 생성 실패")
                return

            # 라벨 크기 확인
            label_size = self.camera_label.size()
            if label_size.width() <= 0 or label_size.height() <= 0:
                # print(f"[DEBUG] 잘못된 라벨 크기: {label_size}")
                return

            scaled_pixmap = pixmap.scaled(
                label_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.camera_label.setPixmap(scaled_pixmap)
            # print("[DEBUG] 프레임 표시 성공!")  # 디버깅
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
        """분석 시작 - macOS 안정성 강화"""
        if not self.selected_exercise:
            QMessageBox.warning(self, "경고", "운동을 선택해주세요.")
            return

        try:
            # 분석 중 상태로 변경
            self.is_analyzing = True

            # 카메라 안전하게 중지
            print("[DEBUG] 카메라 스레드 중지 시작...")
            if self.camera_thread and self.camera_thread.isRunning():
                self.camera_thread.stop()
                # 카메라 완전히 중지될 때까지 대기
                if not self.camera_thread.wait(5000):  # 5초 대기
                    print("[WARNING] 카메라 스레드가 정상적으로 종료되지 않음")
                    self.camera_thread.terminate()
                    self.camera_thread.wait(2000)

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
            self.analyzer_thread = ExerciseAnalyzerThread(self.selected_exercise, duration)

            self.analyzer_thread.status_updated.connect(self.update_status)
            self.analyzer_thread.analysis_finished.connect(self.on_analysis_finished)
            self.analyzer_thread.error_occurred.connect(self.on_analysis_error)
            self.analyzer_thread.frame_processed.connect(self.update_camera_frame)

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
        # 분석 스레드 중지
        if self.analyzer_thread and self.analyzer_thread.isRunning():
            self.analyzer_thread.stop()

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

    def on_analysis_finished(self, video_path, report_path):
        """분석 완료 처리"""
        self.stop_analysis(finished_naturally=True)

        # 결과 요약
        summary = f"""분석 완료!

📹 비디오: {os.path.basename(video_path)}
📄 리포트: {os.path.basename(report_path)}
📁 위치: {os.path.dirname(video_path)}
"""

        # 리포트 내용 읽기
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()

            full_result = summary + "\n" + "="*50 + "\n상세 분석 결과\n" + "="*50 + "\n\n" + report_content
            self.result_text.setText(full_result)
        except Exception as e:
            self.result_text.setText(summary + f"\n리포트 파일을 읽을 수 없습니다: {e}")

        # 상태 및 알림
        self.status_label.setText("분석 완료!")
        QMessageBox.information(
            self,
            "분석 완료",
            f"분석이 완료되었습니다!\n\n비디오: {os.path.basename(video_path)}\n리포트: {os.path.basename(report_path)}"
        )

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

    def closeEvent(self, event):
        """애플리케이션 종료 시 정리"""
        # 모든 스레드 정리
        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.stop()

        if self.analyzer_thread and self.analyzer_thread.isRunning():
            self.analyzer_thread.stop()

        # 타이머 정리
        if self.analysis_timer.isActive():
            self.analysis_timer.stop()

        event.accept()

def main():
    """메인 함수 - macOS 안정성 강화"""
    # macOS에서 안전한 멀티프로세싱 설정
    import multiprocessing
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass # 이미 설정된 경우

    try:
        app = QApplication(sys.argv)

        # macOS 특수 설정
        app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)
        app.setStyle('Fusion')  # 안정한 스타일

        # 메모리 관리 강화
        import gc
        gc.set_threshold(700, 10, 10)  # 더 자주 가비지 컬렉션

        print("[DEBUG] 메인 윈도우 생성 중...")
        window = MainWindow()

        print("[DEBUG] 윈도우 표시...")
        window.show()

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
        result = app.exec_()

        safe_exit()
        sys.exit(result)

    except Exception as e:
        print(f"메인 함수 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()