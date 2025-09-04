#!/usr/bin/env python3
"""
스쿼트 분석 GUI 애플리케이션 메인 실행 파일 - PySide6 버전
젯슨 ARM64에서 실행 가능한 PySide6 기반 애플리케이션
"""

import sys
import os

# UI 모듈 import (PySide6 버전)
from ui_pyside6.main_window import MainWindow

# PySide6 애플리케이션 생성
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

def main():
    """메인 함수"""
    # 애플리케이션 생성
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("스쿼트 분석 시스템 - PySide6")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Repit AI")
    
    # 고해상도 디스플레이 지원 (PySide6 최적화)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    # PySide6에서는 AA_EnableHighDpiScaling이 기본적으로 활성화됨
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 시작
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 