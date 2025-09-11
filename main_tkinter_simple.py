#!/usr/bin/env python3
"""
스쿼트 분석 시스템 - tkinter 간단 버전
macOS에서 확실하게 작동하는 버전
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class SimpleMainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("스쿼트 분석 시스템 (tkinter)")
        self.root.geometry("800x600")
        
        # 메인 프레임
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 제목
        title_label = ttk.Label(main_frame, text="🏋️ 스쿼트 분석 시스템", font=('Arial', 20, 'bold'))
        title_label.pack(pady=20)
        
        # 운동 선택
        exercise_frame = ttk.LabelFrame(main_frame, text="운동 선택", padding=10)
        exercise_frame.pack(fill=tk.X, pady=10)
        
        self.exercise_var = tk.StringVar(value="squat")
        
        ttk.Radiobutton(exercise_frame, text="SQUAT", variable=self.exercise_var, value="squat").pack(anchor=tk.W)
        ttk.Radiobutton(exercise_frame, text="LUNGE", variable=self.exercise_var, value="lunge").pack(anchor=tk.W)
        ttk.Radiobutton(exercise_frame, text="PLANK", variable=self.exercise_var, value="plank").pack(anchor=tk.W)
        
        # 분석 시간
        time_frame = ttk.LabelFrame(main_frame, text="분석 시간", padding=10)
        time_frame.pack(fill=tk.X, pady=10)
        
        self.time_var = tk.IntVar(value=30)
        time_spinbox = ttk.Spinbox(time_frame, from_=5, to=120, textvariable=self.time_var, width=10)
        time_spinbox.pack(anchor=tk.W)
        
        # 버튼들
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        self.start_button = ttk.Button(button_frame, text="분석 시작", command=self.start_analysis)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="분석 중지", command=self.stop_analysis, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 상태 표시
        self.status_label = ttk.Label(main_frame, text="대기 중...", relief=tk.SUNKEN, padding=10)
        self.status_label.pack(fill=tk.X, pady=10)
        
        # 결과 표시
        result_frame = ttk.LabelFrame(main_frame, text="분석 결과", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.result_text = tk.Text(result_frame, height=8, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 분석 상태
        self.is_analyzing = False
        self.analysis_thread = None
        
        # 윈도우를 확실하게 표시
        self.root.after(100, self.ensure_window_visible)
    
    def ensure_window_visible(self):
        """윈도우가 확실히 보이도록 설정"""
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.attributes('-topmost', False)
        self.root.focus_force()
        self.root.deiconify()
        
        # 화면 중앙에 배치
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
    
    def start_analysis(self):
        """분석 시작"""
        exercise = self.exercise_var.get()
        duration = self.time_var.get()
        
        if not exercise:
            messagebox.showwarning("경고", "운동을 선택해주세요.")
            return
        
        self.is_analyzing = True
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.status_label.configure(text=f"{exercise.upper()} 분석 시작...")
        
        # 분석 스레드 시작
        self.analysis_thread = threading.Thread(target=self.run_analysis, args=(exercise, duration))
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
    
    def run_analysis(self, exercise, duration):
        """분석 실행 (별도 스레드)"""
        try:
            # 시뮬레이션된 분석 (실제로는 squat_real_tts.py 등을 호출)
            for i in range(duration):
                if not self.is_analyzing:
                    break
                
                # 상태 업데이트 (GUI 스레드에서 실행)
                self.root.after(0, lambda: self.status_label.configure(text=f"{exercise.upper()} 분석 중... {i+1}/{duration}초"))
                time.sleep(1)
            
            if self.is_analyzing:
                # 분석 완료
                self.root.after(0, self.analysis_completed, exercise)
            
        except Exception as e:
            self.root.after(0, lambda: self.show_error(f"분석 오류: {str(e)}"))
    
    def analysis_completed(self, exercise):
        """분석 완료"""
        self.is_analyzing = False
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.status_label.configure(text="분석 완료!")
        
        # 결과 표시
        result = f"""✅ {exercise.upper()} 분석 완료!

📊 분석 결과:
- 운동 타입: {exercise.upper()}
- 분석 시간: {self.time_var.get()}초
- 상태: 정상 완료

🎯 다음 단계:
1. 실제 squat_real_tts.py 모듈과 연동
2. 카메라 피드 추가
3. 상세 분석 결과 표시
"""
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
        
        messagebox.showinfo("완료", f"{exercise.upper()} 분석이 완료되었습니다!")
    
    def stop_analysis(self):
        """분석 중지"""
        self.is_analyzing = False
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.status_label.configure(text="분석 중지됨")
    
    def show_error(self, error_msg):
        """오류 표시"""
        self.is_analyzing = False
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.status_label.configure(text="오류 발생")
        messagebox.showerror("오류", error_msg)

def main():
    """메인 함수"""
    # macOS에서 tkinter 경고 억제
    import os
    os.environ['TK_SILENCE_DEPRECATION'] = '1'
    
    # 루트 윈도우 생성
    root = tk.Tk()
    
    # 메인 윈도우 생성
    app = SimpleMainWindow(root)
    
    print("tkinter 애플리케이션이 시작되었습니다!")
    print("윈도우가 보이지 않는다면 다른 창 뒤에 숨어있을 수 있습니다.")
    
    # 이벤트 루프 시작
    root.mainloop()

if __name__ == "__main__":
    main() 