#!/usr/bin/env python3
"""
스쿼트 분석 GUI 애플리케이션 메인 실행 파일
젯슨에서 실행 가능한 tkinter 기반 애플리케이션
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox

# macOS에서 tkinter 경고 억제
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# UI 모듈 import
from ui_tkinter.main_window import MainWindow

def main():
    """메인 함수"""
    # tkinter 애플리케이션 생성
    root = tk.Tk()
    
    # 애플리케이션 정보 설정
    root.title("스쿼트 분석 시스템")
    root.geometry("1200x800")
    root.minsize(800, 600)
    
    # macOS에서 윈도우를 앞으로 가져오기
    root.lift()
    root.attributes('-topmost', True)
    root.attributes('-topmost', False)
    
    # 고해상도 디스플레이 지원
    try:
        root.tk.call('tk', 'scaling', 1.5)
    except:
        pass
    
    # 메인 윈도우 생성
    app = MainWindow(root)
    
    # 윈도우를 화면 중앙에 배치
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # 윈도우를 앞으로 가져오기 (macOS에서 중요)
    root.deiconify()
    root.focus_force()
    
    # 이벤트 루프 시작
    root.mainloop()

if __name__ == "__main__":
    main() 