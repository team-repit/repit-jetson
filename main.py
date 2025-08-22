#!/usr/bin/env python3
"""
스쿼트 분석 GUI 애플리케이션 메인 실행 파일
젯슨에서 실행 가능한 PyQt5 기반 애플리케이션
"""

import sys
import os

# UI 모듈 import
from ui.main_window import MainWindow

# PyQt5 애플리케이션 생성
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

def main():
    """메인 함수"""
    # 애플리케이션 생성
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("스쿼트 분석 시스템")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Repit AI")
    
    # 고해상도 디스플레이 지원
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    # 이벤트 루프 시작
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 