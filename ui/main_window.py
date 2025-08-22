#!/usr/bin/env python3
"""
스쿼트 분석 메인 윈도우 UI
PyQt5를 사용하여 젯슨에서 실행 가능한 GUI 애플리케이션
"""

import sys
import os
import subprocess
import threading
import time
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSpinBox, QPushButton, 
                             QTextEdit, QProgressBar, QGroupBox, QMessageBox,
                             QFileDialog, QSplitter, QSlider, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QUrl
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

class SquatAnalyzerThread(QThread):
    """스쿼트 분석을 백그라운드에서 실행하는 스레드"""
    
    # 시그널 정의
    analysis_started = pyqtSignal()
    analysis_finished = pyqtSignal(str, str)  # 비디오 경로, 리포트 경로
    analysis_error = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, duration_seconds):
        super().__init__()
        self.duration_seconds = duration_seconds
        self.is_running = False
        
    def run(self):
        """스쿼트 분석 실행"""
        try:
            self.is_running = True
            self.analysis_started.emit()
            
            # squat_real_tts.py 모듈 직접 import하여 실행
            import squat_real_tts
            
            # 분석 실행 (새 창에서 카메라 실행)
            video_path, report_path = squat_real_tts.run_squat_analysis(self.duration_seconds)
            
            if video_path and report_path:
                # 파일이 실제로 존재하는지 확인
                if os.path.exists(video_path) and os.path.exists(report_path):
                    self.analysis_finished.emit(video_path, report_path)
                else:
                    # output 디렉토리에서 최신 파일 찾기 (현재 애플리케이션 위치 기준)
                    app_dir = os.path.dirname(os.path.abspath(__file__))
                    output_dir = os.path.join(app_dir, "..", "output")
                    if os.path.exists(output_dir):
                        video_files = [f for f in os.listdir(output_dir) if f.endswith('.mp4') and 'squat_realtime_tts' in f]
                        report_files = [f for f in os.listdir(output_dir) if f.endswith('.txt') and 'squat_realtime_tts' in f]
                        
                        if video_files and report_files:
                            # 가장 최근 파일 선택
                            latest_video = os.path.join(output_dir, sorted(video_files)[-1])
                            latest_report = os.path.join(output_dir, sorted(report_files)[-1])
                            self.analysis_finished.emit(latest_video, latest_report)
                        else:
                            self.analysis_error.emit("output 디렉토리에서 결과 파일을 찾을 수 없습니다.")
                    else:
                        self.analysis_error.emit("output 디렉토리가 생성되지 않았습니다.")
            else:
                self.analysis_error.emit("분석이 실패했습니다.")
                
        except ImportError as e:
            self.analysis_error.emit(f"모듈 import 오류: {str(e)}\n\nsquat_real_tts.py 파일이 application 디렉토리에 있는지 확인하세요.")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.analysis_error.emit(f"분석 중 오류 발생:\n\n{str(e)}\n\n상세 오류:\n{error_details}")
        finally:
            self.is_running = False
    
    def stop(self):
        """분석 중지"""
        self.is_running = False

class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.analyzer_thread = None
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("스쿼트 분석 시스템 - Jetson TTS")
        self.setGeometry(100, 100, 1000, 700)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 제목
        title_label = QLabel("🏋️ 스쿼트 분석 시스템")
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 설정 그룹
        settings_group = QGroupBox("⚙️ 분석 설정")
        settings_layout = QHBoxLayout()
        
        # 타이머 설정
        timer_label = QLabel("분석 시간 (초):")
        self.timer_spinbox = QSpinBox()
        self.timer_spinbox.setRange(10, 120)  # 10초 ~ 2분
        self.timer_spinbox.setValue(60)  # 기본값 1분
        self.timer_spinbox.setSuffix("초")
        
        # 시작 버튼
        self.start_button = QPushButton("🚀 분석 시작")
        self.start_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.start_button.clicked.connect(self.start_analysis)
        
        # 중지 버튼
        self.stop_button = QPushButton("⏹️ 분석 중지")
        self.stop_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.stop_button.clicked.connect(self.stop_analysis)
        self.stop_button.setEnabled(False)
        
        settings_layout.addWidget(timer_label)
        settings_layout.addWidget(self.timer_spinbox)
        settings_layout.addStretch()
        settings_layout.addWidget(self.start_button)
        settings_layout.addWidget(self.stop_button)
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 결과 표시 영역
        results_splitter = QSplitter(Qt.Horizontal)
        
        # 비디오 결과
        video_group = QGroupBox("🎥 분석 비디오")
        video_layout = QVBoxLayout()
        
        # 비디오 플레이어 위젯
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 300)
        self.video_widget.setStyleSheet("border: 2px solid #ccc; background-color: #000;")
        
        # 비디오 플레이어 컨트롤
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        
        # 비디오 컨트롤 버튼들
        video_controls = QHBoxLayout()
        
        self.play_button = QPushButton("▶️ 재생")
        self.play_button.clicked.connect(self.play_video)
        self.pause_button = QPushButton("⏸️ 일시정지")
        self.pause_button.clicked.connect(self.pause_video)
        self.stop_button = QPushButton("⏹️ 정지")
        self.stop_button.clicked.connect(self.stop_video)
        
        # 볼륨 슬라이더
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.media_player.setVolume)
        
        video_controls.addWidget(self.play_button)
        video_controls.addWidget(self.pause_button)
        video_controls.addWidget(self.stop_button)
        video_controls.addStretch()
        video_controls.addWidget(QLabel("🔊"))
        video_controls.addWidget(self.volume_slider)
        
        video_layout.addWidget(self.video_widget)
        video_layout.addLayout(video_controls)
        
        # 초기 상태: 비디오 없음
        self.video_label = QLabel("비디오가 여기에 표시됩니다")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 2px dashed #ccc; background-color: #f9f9f9;")
        self.video_widget.hide()
        self.video_label.show()
        
        video_layout.addWidget(self.video_label)
        video_group.setLayout(video_layout)
        results_splitter.addWidget(video_group)
        
        # 비디오 정보 라벨 저장
        self.video_info_label = None
        
        # 분석 리포트
        report_group = QGroupBox("📊 분석 리포트")
        report_layout = QVBoxLayout()
        
        # 리포트 헤더 (파일명, 크기 등)
        report_header = QHBoxLayout()
        self.report_info_label = QLabel("리포트 정보")
        self.report_info_label.setStyleSheet("color: #666; font-size: 12px;")
        report_header.addWidget(self.report_info_label)
        report_header.addStretch()
        
        # 리포트 텍스트 (스크롤바 포함)
        self.report_text = QTextEdit()
        self.report_text.setPlaceholderText("분석 리포트가 여기에 표시됩니다...")
        self.report_text.setLineWrapMode(QTextEdit.WidgetWidth)  # 자동 줄바꿈
        self.report_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 세로 스크롤바
        self.report_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 가로 스크롤바
        
        report_layout.addLayout(report_header)
        report_layout.addWidget(self.report_text)
        report_group.setLayout(report_layout)
        results_splitter.addWidget(report_group)
        
        main_layout.addWidget(results_splitter)
        
        # 상태 표시
        self.status_label = QLabel("준비됨")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        # 초기 상태 설정
        self.update_ui_state("ready")
        
    def start_analysis(self):
        """분석 시작"""
        duration = self.timer_spinbox.value()
        
        # 분석 스레드 시작
        self.analyzer_thread = SquatAnalyzerThread(duration)
        self.analyzer_thread.analysis_started.connect(self.on_analysis_started)
        self.analyzer_thread.analysis_finished.connect(self.on_analysis_finished)
        self.analyzer_thread.analysis_error.connect(self.on_analysis_error)
        self.analyzer_thread.progress_updated.connect(self.progress_bar.setValue)
        
        self.analyzer_thread.start()
        
    def stop_analysis(self):
        """분석 중지"""
        if self.analyzer_thread:
            self.analyzer_thread.stop()
            self.analyzer_thread.wait()
            self.update_ui_state("ready")
            self.status_label.setText("분석이 중지되었습니다")
    
    def on_analysis_started(self):
        """분석 시작 시 호출"""
        self.update_ui_state("analyzing")
        self.status_label.setText("분석 중... 카메라가 켜집니다")
        
    def on_analysis_finished(self, video_path, report_path):
        """분석 완료 시 호출"""
        self.update_ui_state("ready")
        self.status_label.setText("분석 완료!")
        
        # 결과 표시
        self.display_results(video_path, report_path)
        
        QMessageBox.information(self, "분석 완료", 
                              f"스쿼트 분석이 완료되었습니다!\n\n"
                              f"비디오: {os.path.basename(video_path)}\n"
                              f"리포트: {os.path.basename(report_path)}")
    
    def on_analysis_error(self, error_msg):
        """분석 오류 시 호출"""
        self.update_ui_state("ready")
        self.status_label.setText("오류 발생")
        
        QMessageBox.critical(self, "분석 오류", f"분석 중 오류가 발생했습니다:\n{error_msg}")
    
    def display_results(self, video_path, report_path):
        """결과 표시"""
        # 리포트 텍스트 표시
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            self.report_text.setText(report_content)
            
            # 리포트 정보 업데이트
            report_name = os.path.basename(report_path)
            report_size = os.path.getsize(report_path) / 1024  # KB
            self.report_info_label.setText(f"📄 {report_name} ({report_size:.1f} KB)")
            
        except Exception as e:
            self.report_text.setText(f"리포트 파일을 읽을 수 없습니다: {str(e)}")
            self.report_info_label.setText("❌ 리포트 로드 실패")
        
        # 비디오 플레이어 설정
        self.setup_video_player(video_path)
    
    def setup_video_player(self, video_path):
        """비디오 플레이어 설정"""
        try:
            # 비디오 파일 로드
            url = QUrl.fromLocalFile(os.path.abspath(video_path))
            self.media_player.setMedia(QMediaContent(url))
            
            # 비디오 위젯 표시, 라벨 숨김
            self.video_widget.show()
            self.video_label.hide()
            
            # 비디오 정보 표시 (플레이어 아래)
            video_name = os.path.basename(video_path)
            video_size = os.path.getsize(video_path) / (1024*1024)
            
            # 비디오 정보를 별도 라벨로 표시
            if self.video_info_label is None:
                self.video_info_label = QLabel(f"📹 {video_name} ({video_size:.1f} MB)")
                self.video_info_label.setAlignment(Qt.AlignCenter)
                self.video_info_label.setStyleSheet("color: #666; font-size: 12px;")
                # 비디오 그룹에 정보 라벨 추가
                video_group = self.video_widget.parent().parent()
                video_group.layout().addWidget(self.video_info_label)
            else:
                self.video_info_label.setText(f"📹 {video_name} ({video_size:.1f} MB)")
            
        except Exception as e:
            print(f"비디오 플레이어 설정 오류: {str(e)}")
            # 오류 시 라벨로 폴백
            self.video_widget.hide()
            self.video_label.show()
            self.video_label.setText(f"📹 비디오 로드 실패\n{str(e)}")
    
    def play_video(self):
        """비디오 재생"""
        self.media_player.play()
    
    def pause_video(self):
        """비디오 일시정지"""
        self.media_player.pause()
    
    def stop_video(self):
        """비디오 정지"""
        self.media_player.stop()
    
    def update_ui_state(self, state):
        """UI 상태 업데이트"""
        if state == "ready":
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.timer_spinbox.setEnabled(True)
            self.progress_bar.setVisible(False)
        elif state == "analyzing":
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.timer_spinbox.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
    
    def closeEvent(self, event):
        """애플리케이션 종료 시"""
        if self.analyzer_thread and self.analyzer_thread.isRunning():
            self.analyzer_thread.stop()
            self.analyzer_thread.wait()
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