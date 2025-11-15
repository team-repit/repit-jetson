#!/usr/bin/env python3
"""
토큰 입력 화면 위젯 - PySide6 버전
로그인을 대체하는 API 토큰 입력 UI
"""

import os
import sys
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QLineEdit, QMessageBox, QFrame)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QPixmap

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


class TokenInputWidget(QWidget):
    """토큰 입력 화면 위젯"""
    # 토큰 입력 완료 시그널 (토큰 문자열 전달)
    token_submitted = Signal(str)
    # 토큰 없이 계속하기 시그널
    continue_without_token = Signal()
    
    def __init__(self):
        super().__init__()
        self.token_file = os.path.join(os.path.dirname(__file__), "..", ".token_cache")
        self.init_ui()
        self.load_cached_token()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 로고 영역
        logo_path = resource_path("ui_pyside6/logo.png")
        if os.path.exists(logo_path):
            logo_label = QLabel()
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)
        
        # 제목
        title_label = QLabel("Re:PiT")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 부제목
        subtitle_label = QLabel("운동 자세 분석 시스템")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #666666; margin-bottom: 30px;")
        layout.addWidget(subtitle_label)
        
        # 토큰 입력 프레임
        token_frame = QFrame()
        token_frame.setFrameStyle(QFrame.Shape.Box)
        token_frame.setMaximumWidth(500)
        token_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                padding: 30px;
            }
        """)
        token_layout = QVBoxLayout(token_frame)
        
        # 안내 문구
        info_label = QLabel("API 토큰을 입력해주세요")
        info_font = QFont()
        info_font.setPointSize(16)
        info_font.setBold(True)
        info_label.setFont(info_font)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: #333333; margin-bottom: 10px;")
        token_layout.addWidget(info_label)
        
        # 설명 문구
        desc_label = QLabel("웹 페이지에서 발급받은 토큰을 입력하세요.\n운동 기록이 서버에 저장됩니다.")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 20px;")
        desc_label.setWordWrap(True)
        token_layout.addWidget(desc_label)
        
        # 토큰 입력 필드
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("토큰을 입력하거나 붙여넣기 하세요")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)  # **** 표시
        self.token_input.setMinimumHeight(45)
        self.token_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #ced4da;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                background-color: white;
                font-family: monospace;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #808080;
                background-color: #ffffff;
            }
            QLineEdit[echoMode="2"] {
                font-family: monospace;
                color: #333333;
            }
        """)
        self.token_input.returnPressed.connect(self.submit_token)
        
        # 입력 이벤트 연결 (디버깅용)
        self.token_input.textChanged.connect(self.on_text_changed)
        
        token_layout.addWidget(self.token_input)
        
        # 토큰 표시/숨기기 체크박스
        show_token_layout = QHBoxLayout()
        show_token_layout.addStretch()
        self.show_token_btn = QPushButton("토큰 보기")
        self.show_token_btn.setCheckable(True)
        self.show_token_btn.setMaximumWidth(100)
        self.show_token_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: none;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #333333;
                text-decoration: underline;
            }
        """)
        self.show_token_btn.toggled.connect(self.toggle_token_visibility)
        show_token_layout.addWidget(self.show_token_btn)
        token_layout.addLayout(show_token_layout)
        
        # 버튼 레이아웃
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        
        # 확인 버튼
        submit_button = QPushButton("토큰 입력 완료")
        submit_button.setMinimumHeight(45)
        submit_button.setStyleSheet("""
            QPushButton {
                background-color: #808080;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 12px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
        """)
        submit_button.clicked.connect(self.submit_token)
        button_layout.addWidget(submit_button)
        
        # 토큰 없이 계속하기 버튼
        continue_button = QPushButton("토큰 입력 없이 계속하기")
        continue_button.setMinimumHeight(40)
        continue_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: 1px solid #ced4da;
                border-radius: 5px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border: 1px solid #adb5bd;
            }
        """)
        continue_button.clicked.connect(self.continue_without_token_clicked)
        button_layout.addWidget(continue_button)
        
        token_layout.addLayout(button_layout)
        
        # 메인 레이아웃에 토큰 프레임 추가
        layout.addWidget(token_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 하단 안내
        footer_label = QLabel("💡 토큰이 없으신가요? 웹 페이지에서 로그인 후 발급받으세요.")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("color: #999999; margin-top: 20px; font-size: 12px;")
        layout.addWidget(footer_label)
        
        layout.addStretch()
    
    def on_text_changed(self, text):
        """텍스트 변경 이벤트 (디버깅용)"""
        print(f"🔤 입력된 텍스트 길이: {len(text)}")
        if text:
            print(f"   첫 글자: '{text[0]}'")
    
    def toggle_token_visibility(self, checked):
        """토큰 표시/숨기기"""
        if checked:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_token_btn.setText("토큰 숨기기")
            print("🔍 토큰 표시 모드")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_token_btn.setText("토큰 보기")
            print("🔒 토큰 숨기기 모드")
    
    def submit_token(self):
        """토큰 입력 완료"""
        token = self.token_input.text().strip()
        
        if not token:
            QMessageBox.warning(
                self,
                "입력 오류",
                "토큰을 입력해주세요.\n토큰 없이 계속하려면 '토큰 입력 없이 계속하기'를 눌러주세요."
            )
            return
        
        # 토큰 유효성 검사 (기본적인 길이 체크)
        if len(token) < 10:
            QMessageBox.warning(
                self,
                "유효하지 않은 토큰",
                "입력하신 토큰이 너무 짧습니다.\n올바른 토큰을 입력해주세요."
            )
            return
        
        # 토큰 저장
        self.save_token(token)
        
        # 시그널 발생
        self.token_submitted.emit(token)
    
    def continue_without_token_clicked(self):
        """토큰 없이 계속하기"""
        # 커스텀 메시지 박스 생성 (Yes를 왼쪽, No를 오른쪽에 배치)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("토큰 없이 계속")
        msg_box.setText("토큰 입력 없이 계속하시겠습니까?\n\n운동 기록이 서버에 저장되지 않으며,\n로컬에만 저장됩니다.")
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        # 버튼 생성 (Yes를 왼쪽, No를 오른쪽에 배치)
        yes_button = msg_box.addButton("예", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("아니오", QMessageBox.ButtonRole.NoRole)
        
        # 기본 버튼을 Yes로 설정 (파란색 버튼이 됨)
        msg_box.setDefaultButton(yes_button)
        
        # 메시지 박스 표시
        msg_box.exec()
        
        if msg_box.clickedButton() == yes_button:
            # 캐시된 토큰 삭제
            self.clear_token()
            self.continue_without_token.emit()
    
    def save_token(self, token):
        """토큰을 로컬 파일에 저장"""
        try:
            data = {"token": token}
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            # 파일 권한 제한 (읽기/쓰기만 본인만 가능)
            os.chmod(self.token_file, 0o600)
            print(f"✅ 토큰 저장됨: {self.token_file}")
        except Exception as e:
            print(f"❌ 토큰 저장 실패: {e}")
    
    def load_cached_token(self):
        """저장된 토큰 불러오기"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    token = data.get("token", "")
                    if token:
                        self.token_input.setText(token)
                        print(f"✅ 캐시된 토큰 불러옴")
        except Exception as e:
            print(f"⚠️  토큰 불러오기 실패: {e}")
    
    def clear_token(self):
        """저장된 토큰 삭제"""
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                print(f"✅ 토큰 캐시 삭제됨")
            self.token_input.clear()
        except Exception as e:
            print(f"❌ 토큰 삭제 실패: {e}")
    
    def get_token(self):
        """현재 입력된 토큰 반환"""
        return self.token_input.text().strip()

