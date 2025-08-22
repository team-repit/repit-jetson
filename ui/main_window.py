#!/usr/bin/env python3
"""
운동 자세 분석 메인 윈도우 UI
PyQt5를 사용하여 젯슨에서 실행 가능한 GUI 애플리케이션
"""

import sys
import os
import time
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QGroupBox, 
                             QSpinBox, QTextEdit, QMessageBox, QFrame)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont
import cv2
import numpy as np

# 운동 분석 모듈들 import
import squat_real_tts
import lunge_realtime
import plank

class ExerciseAnalyzerThread(QThread):
    """운동 분석을 위한 스레드"""
    update_frame = pyqtSignal(np.ndarray)  # 카메라 프레임 업데이트 신호
    analysis_finished = pyqtSignal(str, str)  # 분석 완료 신호 (비디오 경로, 리포트 경로)
    error_occurred = pyqtSignal(str)  # 오류 발생 신호
    status_updated = pyqtSignal(str)  # 상태 업데이트 신호
    
    def __init__(self, exercise_type, duration_seconds):
        super().__init__()
        self.exercise_type = exercise_type
        self.duration_seconds = duration_seconds
        self.running = True
        self.cap = None
        
    def run(self):
        """운동 분석 실행"""
        try:
            if self.exercise_type == "squat":
                self.status_updated.emit("스쿼트 분석 시작 중...")
                video_path, report_path = squat_real_tts.run_squat_analysis(self.duration_seconds, self.should_stop)
            elif self.exercise_type == "lunge":
                self.status_updated.emit("런지 분석 시작 중...")
                video_path, report_path = lunge_realtime.run_lunge_analysis(self.duration_seconds, self.should_stop)
            elif self.exercise_type == "plank":
                self.status_updated.emit("플랭크 분석 시작 중...")
                video_path, report_path = plank.run_plank_analysis(self.duration_seconds, self.should_stop)
            else:
                self.error_occurred.emit("알 수 없는 운동 타입입니다.")
                return
                
            # 중지 요청이 있었는지 확인
            if not self.running:
                self.status_updated.emit("분석이 사용자에 의해 중지되었습니다.")
                return
                
            if video_path and report_path:
                self.analysis_finished.emit(video_path, report_path)
            else:
                self.error_occurred.emit("분석이 실패했습니다.")
                
        except Exception as e:
            if not self.running:
                self.status_updated.emit("분석이 중지되었습니다.")
            else:
                self.error_occurred.emit(f"분석 중 오류 발생: {str(e)}")
    
    def should_stop(self):
        """분석 중지 여부 확인"""
        return not self.running
    
    def stop(self):
        """분석 중지"""
        print(f"스레드 중지 요청: {self.exercise_type}")
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.quit()
        self.wait()

class CameraThread(QThread):
    """실시간 카메라 피드를 위한 스레드"""
    frame_ready = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None
        
    def run(self):
        """카메라 피드 캡처"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.error_occurred.emit("카메라를 열 수 없습니다.")
                return
                
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            while self.running:
                ret, frame = self.cap.read()
                if ret:
                    # 프레임을 RGB로 변환하여 PyQt5에서 표시
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.frame_ready.emit(rgb_frame)
                else:
                    break
                    
                time.sleep(0.033)  # ~30 FPS
                
        except Exception as e:
            self.error_occurred.emit(f"카메라 오류: {str(e)}")
        finally:
            if self.cap:
                self.cap.release()
    
    def stop(self):
        """카메라 중지"""
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.quit()
        self.wait()

class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("운동 자세 분석 시스템")
        self.setGeometry(100, 100, 1200, 800)
        
        # 변수 초기화
        self.duration_seconds = 60  # 기본값을 60초로 변경
        self.selected_exercise = None
        self.analyzer_thread = None
        self.camera_thread = None
        self.is_analyzing = False
        
        # UI 초기화
        self.init_ui()
        
        # 카메라 스레드 시작
        self.start_camera()
    
    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        
        # 왼쪽 패널 (운동 선택 및 설정)
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 오른쪽 패널 (카메라 화면 및 분석 상태)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)
    
    def create_left_panel(self):
        """왼쪽 패널 생성 (운동 선택 및 설정)"""
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.Box)
        left_layout = QVBoxLayout(left_panel)
        
        # 운동 선택 그룹
        exercise_group = QGroupBox("운동 선택")
        exercise_layout = QVBoxLayout(exercise_group)
        
        self.squat_button = QPushButton("SQUAT")
        self.lunge_button = QPushButton("LUNGE")
        self.plank_button = QPushButton("PLANK")
        
        # 버튼 그룹 설정 (하나만 선택 가능)
        self.squat_button.setCheckable(True)
        self.lunge_button.setCheckable(True)
        self.plank_button.setCheckable(True)
        
        # 버튼 클릭 이벤트 연결
        self.squat_button.clicked.connect(lambda: self.select_exercise("squat"))
        self.lunge_button.clicked.connect(lambda: self.select_exercise("lunge"))
        self.plank_button.clicked.connect(lambda: self.select_exercise("plank"))
        
        exercise_layout.addWidget(self.squat_button)
        exercise_layout.addWidget(self.lunge_button)
        exercise_layout.addWidget(self.plank_button)
        
        left_layout.addWidget(exercise_group)
        
        # 분석 설정 그룹
        settings_group = QGroupBox("분석 설정")
        settings_layout = QVBoxLayout(settings_group)
        
        duration_label = QLabel("분석 시간 (초):")
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setRange(30, 600)
        self.duration_spinbox.setValue(60)  # 기본값을 60초로 변경
        self.duration_spinbox.valueChanged.connect(self.update_duration)
        
        settings_layout.addWidget(duration_label)
        settings_layout.addWidget(self.duration_spinbox)
        
        left_layout.addWidget(settings_group)
        
        # 분석 제어 그룹
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
        
        # 상태 표시
        self.status_label = QLabel("대기 중...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; }")
        left_layout.addWidget(self.status_label)
        
        left_layout.addStretch()
        
        # 초기 버튼 스타일 적용
        self.update_button_styles()
        
        return left_panel
    
    def create_right_panel(self):
        """오른쪽 패널 생성 (카메라 화면 및 분석 상태)"""
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.Box)
        right_layout = QVBoxLayout(right_panel)
        
        # 카메라 화면 표시
        camera_group = QGroupBox("실시간 카메라")
        camera_layout = QVBoxLayout(camera_group)
        
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("QLabel { background-color: #000000; border: 1px solid #ccc; }")
        self.camera_label.setText("카메라 초기화 중...")
        
        camera_layout.addWidget(self.camera_label)
        right_layout.addWidget(camera_group)
        
        # 분석 결과 표시
        result_group = QGroupBox("분석 결과")
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(150)
        
        result_layout.addWidget(self.result_text)
        right_layout.addWidget(result_group)
        
        return right_panel
    
    def start_camera(self):
        """카메라 스레드 시작"""
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self.update_camera_frame)
        self.camera_thread.error_occurred.connect(self.on_camera_error)
        self.camera_thread.start()
    
    def update_camera_frame(self, frame):
        """카메라 프레임 업데이트"""
        try:
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # 라벨 크기에 맞게 스케일링
            scaled_pixmap = pixmap.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.camera_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"프레임 업데이트 오류: {e}")
    
    def on_camera_error(self, error_msg):
        """카메라 오류 처리"""
        self.camera_label.setText(f"카메라 오류: {error_msg}")
        self.status_label.setText("카메라 연결 실패")
    
    def update_duration(self, value):
        """분석 시간 업데이트"""
        self.duration_seconds = value
    
    def select_exercise(self, exercise_type):
        """운동 타입 선택"""
        self.selected_exercise = exercise_type
        
        # 모든 버튼 체크 해제
        self.squat_button.setChecked(False)
        self.lunge_button.setChecked(False)
        self.plank_button.setChecked(False)
        
        # 선택된 버튼만 체크
        if exercise_type == "squat":
            self.squat_button.setChecked(True)
        elif exercise_type == "lunge":
            self.lunge_button.setChecked(True)
        elif exercise_type == "plank":
            self.plank_button.setChecked(True)
        
        # 버튼 스타일 업데이트
        self.update_button_styles()
        
        # 상태 업데이트
        exercise_names = {
            "squat": "스쿼트",
            "lunge": "런지",
            "plank": "플랭크"
        }
        exercise_name = exercise_names.get(self.selected_exercise, "알 수 없음")
        self.status_label.setText(f"{exercise_name} 분석 준비됨")
        
        # 타이머 기본값 조정
        if self.selected_exercise == "plank":
            self.duration_spinbox.setValue(60)  # 플랭크는 60초 기본
        else:
            self.duration_spinbox.setValue(60)  # 스쿼트, 런지도 60초 기본
    
    def update_button_styles(self):
        """버튼 스타일을 현재 상태에 맞게 업데이트"""
        # 스쿼트 버튼 스타일
        if self.squat_button.isChecked():
            self.squat_button.setStyleSheet("""
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: 2px solid #666666;
                    border-radius: 8px;
                    padding: 15px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #707070;
                    border-color: #555555;
                }
            """)
        else:
            self.squat_button.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #333333;
                    border: 2px solid #cccccc;
                    border-radius: 8px;
                    padding: 15px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border-color: #bbbbbb;
                }
            """)
        
        # 런지 버튼 스타일
        if self.lunge_button.isChecked():
            self.lunge_button.setStyleSheet("""
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: 2px solid #666666;
                    border-radius: 8px;
                    padding: 15px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #707070;
                    border-color: #555555;
                }
            """)
        else:
            self.lunge_button.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #333333;
                    border: 2px solid #cccccc;
                    border-radius: 8px;
                    padding: 15px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border-color: #bbbbbb;
                }
            """)
        
        # 플랭크 버튼 스타일
        if self.plank_button.isChecked():
            self.plank_button.setStyleSheet("""
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: 2px solid #666666;
                    border-radius: 8px;
                    padding: 15px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #707070;
                    border-color: #555555;
                }
            """)
        else:
            self.plank_button.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #333333;
                    border: 2px solid #cccccc;
                    border-radius: 8px;
                    padding: 15px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border-color: #bbbbbb;
                }
            """)
    
    def start_analysis(self):
        """분석 시작"""
        if not self.selected_exercise:
            QMessageBox.warning(self, "경고", "운동을 선택해주세요.")
            return
        
        duration = self.duration_spinbox.value()
        
        # 분석 스레드 시작
        self.analyzer_thread = ExerciseAnalyzerThread(self.selected_exercise, duration)
        self.analyzer_thread.status_updated.connect(self.update_status)
        self.analyzer_thread.analysis_finished.connect(self.on_analysis_finished)
        self.analyzer_thread.error_occurred.connect(self.on_analysis_error)
        
        self.analyzer_thread.start()
        
        # UI 상태 업데이트
        self.is_analyzing = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("분석 시작 중...")
    
    def stop_analysis(self):
        """분석 중지"""
        if self.analyzer_thread and self.analyzer_thread.isRunning():
            print("분석 중지 요청 중...")
            
            # 스레드에 중지 신호 전송
            self.analyzer_thread.running = False
            
            # 강제 종료를 위한 타이머 설정
            if not self.analyzer_thread.wait(3000):  # 3초 대기
                print("강제 종료 중...")
                self.analyzer_thread.terminate()  # 강제 종료
                self.analyzer_thread.wait(1000)   # 1초 더 대기
            
            # 스레드 정리
            if self.analyzer_thread.isRunning():
                self.analyzer_thread.quit()
                self.analyzer_thread.wait()
        
        # UI 상태 업데이트
        self.is_analyzing = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("분석이 중지되었습니다.")
        
        print("분석 중지 완료")
    
    def update_status(self, status_msg):
        """상태 메시지 업데이트"""
        self.status_label.setText(status_msg)
    
    def on_analysis_finished(self, video_path, report_path):
        """분석 완료 처리"""
        self.is_analyzing = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # 결과 요약 표시
        summary = f"""분석 완료!

📹 비디오 파일: {os.path.basename(video_path)}
📄 리포트 파일: {os.path.basename(report_path)}
📁 저장 위치: {os.path.dirname(video_path)}

"""
        
        # 리포트 내용 읽기
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            # 결과 텍스트에 요약과 상세 내용 모두 표시
            full_result = summary + "\n" + "="*50 + "\n상세 분석 결과\n" + "="*50 + "\n\n" + report_content
            self.result_text.setText(full_result)
            
        except Exception as e:
            error_msg = f"리포트 파일을 읽을 수 없습니다: {str(e)}"
            self.result_text.setText(summary + "\n" + error_msg)
        
        self.status_label.setText("분석 완료!")
        
        # 성공 메시지 표시
        QMessageBox.information(self, "분석 완료", 
                              f"분석이 완료되었습니다!\n\n"
                              f"비디오: {os.path.basename(video_path)}\n"
                              f"리포트: {os.path.basename(report_path)}")
    
    def on_analysis_error(self, error_msg):
        """분석 오류 처리"""
        self.is_analyzing = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        self.result_text.setText(f"분석 오류: {error_msg}")
        self.status_label.setText("분석 실패")
        
        QMessageBox.critical(self, "오류", f"분석 중 오류가 발생했습니다:\n{error_msg}")
    
    def closeEvent(self, event):
        """애플리케이션 종료 시 정리"""
        if self.camera_thread:
            self.camera_thread.stop()
        if self.analyzer_thread:
            self.analyzer_thread.stop()
        event.accept()

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 애플리케이션 스타일 설정
    app.setStyle('Fusion')
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 시작
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 