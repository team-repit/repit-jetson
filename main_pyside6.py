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
from PySide6.QtGui import QIcon

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
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 시작
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 