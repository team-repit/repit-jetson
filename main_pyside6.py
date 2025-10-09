#!/usr/bin/env python3
"""
스쿼트 분석 GUI 애플리케이션 메인 실행 파일 - PySide6 버전
젯슨 ARM64에서 실행 가능한 PySide6 기반 애플리케이션
"""

import sys
import os

# UI 모듈 import (PySide6 버전)
from ui_pyside6.main_window import MainWindow
from ui_pyside6.token_input_widget import TokenInputWidget

# PySide6 애플리케이션 생성
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon


class AppController(QMainWindow):
    """애플리케이션 컨트롤러 - 토큰 입력 화면과 메인 화면 전환"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Re:PiT - 운동 자세 분석 시스템")
        self.setGeometry(100, 100, 1200, 800)
        
        # 아이콘 설정
        icon_path = os.path.join(os.path.dirname(__file__), "ui_pyside6", "logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 스택 위젯 생성 (화면 전환용)
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 토큰 입력 화면
        self.token_widget = TokenInputWidget()
        self.token_widget.token_submitted.connect(self.on_token_submitted)
        self.token_widget.continue_without_token.connect(self.on_continue_without_token)
        
        # 메인 윈도우는 토큰 설정 후 생성
        self.main_window = None
        self.current_token = None
        
        # 토큰 입력 화면을 첫 화면으로 설정
        self.stacked_widget.addWidget(self.token_widget)
        
    def on_token_submitted(self, token):
        """토큰 입력 완료"""
        print(f"✅ 토큰 입력 완료 (길이: {len(token)})")
        self.current_token = token
        self.show_main_window()
    
    def on_continue_without_token(self):
        """토큰 없이 계속"""
        print("ℹ️  토큰 없이 계속하기")
        self.current_token = None
        self.show_main_window()
    
    def show_main_window(self):
        """메인 윈도우 표시"""
        # 기존 메인 윈도우가 있다면 제거
        if self.main_window:
            self.stacked_widget.removeWidget(self.main_window)
            self.main_window.deleteLater()
        
        # 새 메인 윈도우 생성
        self.main_window = MainWindow(access_token=self.current_token)
        self.main_window.go_to_token_screen.connect(self.show_token_screen)
        
        # 스택 위젯에 추가하고 표시
        self.stacked_widget.addWidget(self.main_window)
        self.stacked_widget.setCurrentWidget(self.main_window)
        
        print(f"✅ 메인 윈도우 표시 (토큰: {'있음' if self.current_token else '없음'})")
    
    def show_token_screen(self):
        """토큰 입력 화면 표시"""
        print("🔄 토큰 설정 화면으로 이동")
        self.stacked_widget.setCurrentWidget(self.token_widget)
    
    def closeEvent(self, event):
        """애플리케이션 종료 - 강력한 스레드 정리"""
        try:
            print("[DEBUG] AppController 종료 시작...")
            
            # 메인 윈도우가 있다면 정리
            if self.main_window:
                try:
                    print("[DEBUG] 메인 윈도우 정리 중...")
                    # MainWindow의 closeEvent를 명시적으로 호출
                    self.main_window.close()
                    self.main_window = None
                except Exception as e:
                    print(f"[WARNING] 메인 윈도우 정리 중 오류: {e}")
            
            # Qt 이벤트 처리 (스레드 정리 완료 대기)
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            
            # 메모리 정리
            import gc
            gc.collect()
            
            print("[DEBUG] AppController 종료 완료")
            
        except Exception as e:
            print(f"[ERROR] AppController 종료 중 오류: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 어떤 경우든 이벤트 수락
            event.accept()


def main():
    """메인 함수"""
    # 애플리케이션 생성
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("Re:PiT")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Repit AI")
    
    # 아이콘 설정
    icon_path = os.path.join(os.path.dirname(__file__), "ui_pyside6", "logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        print(f"✅ 앱 아이콘 설정됨: {icon_path}")
    else:
        print(f"⚠️  아이콘 파일을 찾을 수 없습니다: {icon_path}")
    
    # 고해상도 디스플레이 지원 (PySide6 최적화)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    # PySide6에서는 AA_EnableHighDpiScaling이 기본적으로 활성화됨
    
    # 앱 컨트롤러 생성 및 표시
    controller = AppController()
    controller.show()
    
    # 이벤트 루프 시작
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 