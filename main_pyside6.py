#!/usr/bin/env python3
"""
스쿼트 분석 GUI 애플리케이션 메인 실행 파일 - PySide6 버전
젯슨 ARM64에서 실행 가능한 PySide6 기반 애플리케이션
"""

import sys
import os

# PyInstaller 환경에서 경로 처리
def resource_path(relative_path):
    """PyInstaller 환경에서 리소스 경로 가져오기"""
    try:
        # PyInstaller로 빌드된 경우 _MEIPASS 임시 폴더
        base_path = sys._MEIPASS
    except Exception:
        # 일반 Python 실행 환경
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# UI 모듈 import (PySide6 버전)
from ui_pyside6.main_window import MainWindow
from ui_pyside6.token_input_widget import TokenInputWidget

# PySide6 애플리케이션 생성 - 전역 import
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon


class AppController(QMainWindow):
    """애플리케이션 컨트롤러 - 토큰 입력 화면과 메인 화면 전환"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Re:PiT - 운동 자세 분석 시스템")
        self.setGeometry(100, 100, 1200, 800)
        
        # 아이콘 설정
        icon_path = resource_path("ui_pyside6/logo.png")
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

        # 앱 종료 시 메인 윈도우 자원을 안전하게 정리
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.on_app_about_to_quit)
        
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
    
    def _teardown_main_window(self, remove_from_stack=True):
        """현재 메인 윈도우가 있으면 안전하게 종료 및 제거"""
        if not self.main_window:
            return

        try:
            print("[DEBUG] 기존 MainWindow force_cleanup 실행")
            self.main_window.force_cleanup()
        except Exception as e:
            print(f"[WARNING] 기존 MainWindow force_cleanup 실패: {e}")

        try:
            self.main_window.close()
        except Exception as e:
            print(f"[WARNING] 기존 MainWindow close 실패: {e}")

        if remove_from_stack:
            try:
                self.stacked_widget.removeWidget(self.main_window)
            except Exception as e:
                print(f"[WARNING] MainWindow 스택 제거 실패: {e}")

        try:
            self.main_window.deleteLater()
        except Exception as e:
            print(f"[WARNING] MainWindow deleteLater 실패: {e}")

        self.main_window = None

    def show_main_window(self):
        """메인 윈도우 표시"""
        try:
            # 기존 메인 윈도우가 있다면 제거
            if self.main_window:
                self._teardown_main_window()
            
            print("[DEBUG] MainWindow 생성 시작...")
            
            # 새 메인 윈도우 생성 (예외 처리 강화)
            try:
                self.main_window = MainWindow(access_token=self.current_token)
                print("[DEBUG] MainWindow 객체 생성 완료")
            except Exception as e:
                print(f"[ERROR] MainWindow 생성 실패: {e}")
                import traceback
                traceback.print_exc()
                # 에러 메시지 표시
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self,
                    "오류",
                    f"메인 화면을 불러올 수 없습니다.\n\n오류: {str(e)}\n\n앱을 재시작해주세요."
                )
                return
            
            # 시그널 연결
            try:
                self.main_window.go_to_token_screen.connect(self.show_token_screen)
                print("[DEBUG] 시그널 연결 완료")
            except Exception as e:
                print(f"[WARNING] 시그널 연결 실패: {e}")
            
            # 스택 위젯에 추가하고 표시
            try:
                self.stacked_widget.addWidget(self.main_window)
                print("[DEBUG] 스택 위젯에 추가 완료")
                self.stacked_widget.setCurrentWidget(self.main_window)
                print("[DEBUG] 화면 전환 완료")
            except Exception as e:
                print(f"[ERROR] 스택 위젯 작업 실패: {e}")
                import traceback
                traceback.print_exc()
                return
            
            print(f"✅ 메인 윈도우 표시 (토큰: {'있음' if self.current_token else '없음'})")
            
        except Exception as e:
            print(f"[ERROR] show_main_window 전체 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def show_token_screen(self):
        """토큰 입력 화면 표시"""
        print("🔄 토큰 설정 화면으로 이동")
        # 메인 윈도우가 존재하면 안전하게 정리
        self._teardown_main_window()
        self.stacked_widget.setCurrentWidget(self.token_widget)

    def on_app_about_to_quit(self):
        """애플리케이션 종료 직전에 호출되어 자원을 정리"""
        try:
            if self.main_window:
                print("[DEBUG] aboutToQuit: MainWindow 강제 정리")
                self._teardown_main_window(remove_from_stack=False)
        except Exception as e:
            print(f"[WARNING] aboutToQuit 정리 실패: {e}")
    
    def closeEvent(self, event):
        """애플리케이션 종료 - 강력한 스레드 정리"""
        try:
            print("[DEBUG] AppController 종료 시작...")
            
            # 메인 윈도우가 있다면 정리
            if self.main_window:
                print("[DEBUG] 메인 윈도우 정리 중...")
                self._teardown_main_window(remove_from_stack=False)
            
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
    try:
        # macOS에서 Finder에서 실행될 때 작업 디렉토리 문제 해결
        # PyInstaller 환경에서는 앱 번들 내부로 설정
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 경우
                app_dir = os.path.dirname(sys.executable)
                # .app/Contents/MacOS -> .app/Contents/Resources
                if app_dir.endswith('/MacOS'):
                    app_dir = app_dir.replace('/MacOS', '/Resources')
                os.chdir(app_dir)
                print(f"[DEBUG] 작업 디렉토리 설정: {os.getcwd()}")
        except Exception as e:
            print(f"[WARNING] 작업 디렉토리 설정 실패: {e}")
        
        # 전역 예외 핸들러 설정은 QApplication 생성 후에 설정
        # (QApplication 생성 전에는 설정하지 않음)
        
        # 애플리케이션 생성
        app = QApplication(sys.argv)
        
        # 전역 예외 핸들러 설정 (QApplication 생성 후)
        def exception_handler(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            error_msg = f"처리되지 않은 예외:\n{exc_type.__name__}: {exc_value}"
            print(f"[FATAL ERROR] {error_msg}")
            import traceback
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            
            # 사용자에게 오류 표시
            try:
                current_app = QApplication.instance()
                if current_app:
                    QMessageBox.critical(None, "오류", error_msg)
            except Exception as e:
                print(f"[WARNING] 오류 메시지 표시 실패: {e}")
        
        sys.excepthook = exception_handler
        
        # 애플리케이션 정보 설정
        app.setApplicationName("Re:PiT")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("Repit AI")
        
        # 아이콘 설정
        icon_path = resource_path("ui_pyside6/logo.png")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            print(f"✅ 앱 아이콘 설정됨: {icon_path}")
        else:
            print(f"⚠️  아이콘 파일을 찾을 수 없습니다: {icon_path}")
        
        # 고해상도 디스플레이 지원 (PySide6 최적화)
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        # PySide6에서는 AA_EnableHighDpiScaling이 기본적으로 활성화됨
        
        print("[DEBUG] AppController 생성 시작...")
        # 앱 컨트롤러 생성 및 표시
        controller = AppController()
        print("[DEBUG] AppController 생성 완료")
        controller.show()
        print("[DEBUG] AppController 표시 완료")

        import signal

        def handle_signal(signum, frame):
            print(f"[DEBUG] 신호({signum}) 수신 - 안전 종료 시도")
            controller.close()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        
        # 이벤트 루프 시작
        print("[DEBUG] 이벤트 루프 시작...")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"[FATAL ERROR] main 함수 오류: {e}")
        import traceback
        traceback.print_exc()
        
        # 사용자에게 오류 메시지 표시
        try:
            error_app = QApplication.instance()
            if not error_app:
                # QApplication이 없으면 생성 (한 번만)
                error_app = QApplication(sys.argv)
            QMessageBox.critical(None, "치명적 오류", 
                                f"앱을 시작할 수 없습니다.\n\n오류: {str(e)}")
        except Exception as e2:
            print(f"[WARNING] 오류 메시지 표시 실패: {e2}")
        sys.exit(1)

if __name__ == "__main__":
    main() 