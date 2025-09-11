#!/usr/bin/env python3
"""
운동 자세 분석 메인 윈도우 UI
tkinter를 사용하여 젯슨에서 실행 가능한 GUI 애플리케이션
"""

import sys
import os
import time
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# macOS Segmentation fault 방지를 위한 환경변수 설정
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
os.environ['OPENCV_VIDEOIO_DEBUG'] = '1'

# OpenCV 백엔드 설정 (macOS 안정성 향상)
try:
    cv2.setUseOptimized(True)
    cv2.setNumThreads(4)
except:
    pass

class ExerciseAnalyzerThread(threading.Thread):
    """운동 분석을 위한 스레드 - tkinter 안정성 강화"""
    
    def __init__(self, exercise_type, duration_seconds, callback_dict):
        super().__init__()
        self.exercise_type = exercise_type
        self.duration_seconds = duration_seconds
        self.running = True
        self.callback_dict = callback_dict
        self.mutex = threading.Lock()

    def run(self):
        """안전한 분석 실행"""
        try:
            # 메모리 정리
            import gc
            gc.collect()

            print(f"[DEBUG] 분석 스레드 시작: {self.exercise_type}")
            video_path, report_path = None, None

            # 안전한 모듈 import 및 실행
            if self.exercise_type == "squat":
                self.callback_dict['status_updated']("스쿼트 분석 모듈 로드 중...")

                try:
                    # 동적 import로 메모리 충돌 방지
                    import importlib
                    import sys

                    # 모듈이 이미 로드되어 있다면 재로드
                    if 'squat_real_tts' in sys.modules:
                        squat_module = sys.modules['squat_real_tts']
                        importlib.reload(squat_module)
                    else:
                        squat_module = importlib.import_module('squat_real_tts')

                    self.callback_dict['status_updated']("스쿼트 분석 시작...")

                    # 함수가 존재하는지 확인
                    if hasattr(squat_module, 'run_squat_analysis'):
                        video_path, report_path = squat_module.run_squat_analysis(
                            self.duration_seconds, self.should_stop, self.frame_callback
                        )
                    else:
                        self.callback_dict['error_occurred']("분석 함수(run_squat_analysis)를 찾을 수 없습니다.")
                        return

                except ImportError as e:
                    self.callback_dict['error_occurred'](f"스쿼트 모듈 로드 실패: {str(e)}")
                    return
                except Exception as e:
                    self.callback_dict['error_occurred'](f"스쿼트 분석 실행 오류: {str(e)}")
                    return

            elif self.exercise_type == "lunge":
                self.callback_dict['status_updated']("런지 분석 모듈 로드 중...")
                try:
                    # 동적 import로 메모리 충돌 방지 (스쿼트와 동일한 방식)
                    import importlib
                    import sys

                    if 'lunge_realtime' in sys.modules:
                        lunge_module = sys.modules['lunge_realtime']
                        importlib.reload(lunge_module)
                    else:
                        lunge_module = importlib.import_module('lunge_realtime')

                    self.callback_dict['status_updated']("런지 분석 시작...")

                    # 함수가 존재하는지 확인 (스쿼트와 동일한 방식)
                    if hasattr(lunge_module, 'run_lunge_analysis'):
                        video_path, report_path = lunge_module.run_lunge_analysis(
                            self.duration_seconds, self.should_stop, self.frame_callback
                        )
                    else:
                        self.callback_dict['error_occurred']("분석 함수(run_lunge_analysis)를 찾을 수 없습니다.")
                        return

                except ImportError as e:
                    self.callback_dict['error_occurred'](f"런지 모듈(lunge_realtime.py) 로드 실패: {str(e)}")
                    return
                except Exception as e:
                    self.callback_dict['error_occurred'](f"런지 분석 실행 오류: {str(e)}")
                    return

            elif self.exercise_type == "plank":
                self.callback_dict['status_updated']("플랭크 분석 모듈 로드 중...")
                try:
                    # 동적 import로 메모리 충돌 방지
                    import importlib
                    import sys

                    if 'plank' in sys.modules:
                        plank_module = sys.modules['plank']
                        importlib.reload(plank_module)
                    else:
                        plank_module = importlib.import_module('plank')

                    self.callback_dict['status_updated']("플랭크 분석 시작...")

                    # plank.py에 있는 분석 함수 이름을 'run_plank_analysis'로 가정합니다.
                    # 만약 함수 이름이 다르다면 이 부분을 수정해야 합니다.
                    if hasattr(plank_module, 'run_plank_analysis'):
                        video_path, report_path = plank_module.run_plank_analysis(
                            self.duration_seconds, self.should_stop, self.frame_callback
                        )
                    else:
                        self.callback_dict['error_occurred']("분석 함수(run_plank_analysis)를 찾을 수 없습니다.")
                        return

                except ImportError as e:
                    self.callback_dict['error_occurred'](f"플랭크 모듈(plank.py) 로드 실패: {str(e)}")
                    return
                except Exception as e:
                    self.callback_dict['error_occurred'](f"플랭크 분석 실행 오류: {str(e)}")
                    return
            else:
                self.callback_dict['error_occurred']("알 수 없는 운동 타입입니다.")
                return

            if not self.running:
                print("[DEBUG] 분석이 중지되었습니다.")
                return

            if video_path and report_path:
                self.callback_dict['analysis_finished'](video_path, report_path)
            else:
                self.callback_dict['error_occurred']("분석이 알 수 없는 이유로 실패했습니다.")

        except Exception as e:
            if not self.running:
                return
            print(f"[ERROR] 분석 스레드 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            self.callback_dict['error_occurred'](f"분석 중 오류 발생: {str(e)}")
        finally:
            # 메모리 정리
            import gc
            gc.collect()
            print("[DEBUG] 분석 스레드 종료 및 메모리 정리")

    def frame_callback(self, processed_frame):
        """처리된 프레임을 GUI로 전달하는 콜백 - 안전성 강화"""
        try:
            if not self.running:
                return

            with self.mutex:
                if processed_frame is not None and processed_frame.size > 0:
                    # 안전한 복사본 생성
                    frame_copy = processed_frame.copy()
                    # BGR을 RGB로 변환하여 전달
                    rgb_frame = cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB)
                    self.callback_dict['frame_processed'](rgb_frame)
        except Exception as e:
            print(f"frame_callback 오류: {e}")

    def should_stop(self):
        """중지 여부 확인"""
        return not self.running

    def stop(self):
        """안전한 스레드 중지"""
        print("[DEBUG] 분석 스레드 중지 요청")
        with self.mutex:
            self.running = False

class CameraThread(threading.Thread):
    """실시간 카메라 피드를 위한 스레드 (tkinter 안정성 강화)"""
    
    def __init__(self, callback_dict):
        super().__init__()
        self.running = True
        self.cap = None
        self.mutex = threading.Lock()
        self.callback_dict = callback_dict

    def run(self):
        try:
            # macOS에서 안전한 카메라 초기화
            self.cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)  # macOS 전용 백엔드

            if not self.cap.isOpened():
                # 백업 방법으로 다시 시도
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    self.callback_dict['error_occurred']("카메라를 열 수 없습니다.")
                    return

            # 안전한 카메라 설정
            try:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 크기 최소화
            except Exception as e:
                print(f"카메라 설정 경고: {e}")

            frame_count = 0
            while self.running:
                try:
                    with self.mutex:
                        if not self.running:
                            break

                        ret, frame = self.cap.read()

                    if not ret or frame is None:
                        print("프레임 읽기 실패")
                        time.sleep(0.1)
                        continue

                    # 프레임 유효성 검사
                    if frame.size == 0 or len(frame.shape) != 3:
                        print("잘못된 프레임 형식")
                        continue

                    # 안전한 색상 변환
                    try:
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        if rgb_frame is not None and rgb_frame.size > 0:
                            self.callback_dict['frame_ready'](rgb_frame.copy())  # 안전한 복사본 전달
                    except Exception as e:
                        print(f"색상 변환 오류: {e}")
                        continue

                    frame_count += 1
                    if frame_count % 30 == 0:  # 30프레임마다 디버그
                        print(f"[DEBUG] 카메라 프레임 {frame_count} 처리됨")

                except Exception as e:
                    print(f"프레임 처리 오류: {e}")

                time.sleep(0.033)  # 약 30 FPS

        except Exception as e:
            self.callback_dict['error_occurred'](f"카메라 스레드 오류: {str(e)}")
        finally:
            self.cleanup()

    def cleanup(self):
        """안전한 리소스 정리"""
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
            print("[DEBUG] 카메라 리소스 정리 완료")
        except Exception as e:
            print(f"카메라 정리 오류: {e}")

    def stop(self):
        """안전한 스레드 정지"""
        print("[DEBUG] 카메라 스레드 정지 요청")
        with self.mutex:
            self.running = False

        self.cleanup()

class MainWindow:
    """메인 윈도우"""
    
    def __init__(self, root):
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 변수 초기화
        self.duration_seconds = tk.IntVar(value=60)
        self.selected_exercise = None
        self.analyzer_thread = None
        self.camera_thread = None
        self.is_analyzing = False
        self.elapsed_time = 0
        self.analysis_timer_running = False
        
        # 콜백 딕셔너리
        self.callback_dict = {
            'status_updated': self.update_status,
            'analysis_finished': self.on_analysis_finished,
            'error_occurred': self.on_analysis_error,
            'frame_processed': self.update_camera_frame,
            'frame_ready': self.update_camera_frame,
            'error_occurred': self.on_camera_error
        }
        
        self.init_ui()
        self.start_camera()

    def init_ui(self):
        """UI 초기화"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 왼쪽 패널
        left_panel = self.create_left_panel()
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 오른쪽 패널
        right_panel = self.create_right_panel()
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def create_left_panel(self):
        """왼쪽 패널 생성"""
        left_panel = ttk.Frame(self.root)
        
        # 운동 선택 그룹
        exercise_group = ttk.LabelFrame(left_panel, text="운동 선택", padding=10)
        exercise_group.pack(fill=tk.X, pady=(0, 10))
        
        self.exercise_var = tk.StringVar()
        
        self.squat_button = ttk.Radiobutton(
            exercise_group, 
            text="SQUAT", 
            variable=self.exercise_var, 
            value="squat",
            command=self.select_exercise
        )
        self.lunge_button = ttk.Radiobutton(
            exercise_group, 
            text="LUNGE", 
            variable=self.exercise_var, 
            value="lunge",
            command=self.select_exercise
        )
        self.plank_button = ttk.Radiobutton(
            exercise_group, 
            text="PLANK", 
            variable=self.exercise_var, 
            value="plank",
            command=self.select_exercise
        )
        
        self.squat_button.pack(anchor=tk.W, pady=2)
        self.lunge_button.pack(anchor=tk.W, pady=2)
        self.plank_button.pack(anchor=tk.W, pady=2)
        
        # 설정 그룹
        settings_group = ttk.LabelFrame(left_panel, text="분석 설정", padding=10)
        settings_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(settings_group, text="분석 시간 (초):").pack(anchor=tk.W)
        
        duration_spinbox = ttk.Spinbox(
            settings_group,
            from_=5,
            to=600,
            textvariable=self.duration_seconds,
            width=10
        )
        duration_spinbox.pack(anchor=tk.W, pady=(5, 0))
        
        # 제어 그룹
        control_group = ttk.LabelFrame(left_panel, text="분석 제어", padding=10)
        control_group.pack(fill=tk.X, pady=(0, 10))
        
        self.start_button = ttk.Button(
            control_group,
            text="분석 시작",
            command=self.start_analysis
        )
        self.stop_button = ttk.Button(
            control_group,
            text="분석 중지",
            command=self.stop_analysis,
            state=tk.DISABLED
        )
        
        self.start_button.pack(fill=tk.X, pady=(0, 5))
        self.stop_button.pack(fill=tk.X)
        
        # 타이머 라벨
        self.timer_label = ttk.Label(
            left_panel, 
            text="경과 시간: 0초",
            font=('Arial', 12, 'bold')
        )
        self.timer_label.pack(pady=10)
        
        # 상태 라벨
        self.status_label = ttk.Label(
            left_panel,
            text="대기 중...",
            relief=tk.SUNKEN,
            padding=10
        )
        self.status_label.pack(fill=tk.X, pady=(0, 10))
        
        return left_panel

    def create_right_panel(self):
        """오른쪽 패널 생성"""
        right_panel = ttk.Frame(self.root)
        
        # 카메라 그룹
        camera_group = ttk.LabelFrame(right_panel, text="실시간 카메라", padding=10)
        camera_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.camera_label = ttk.Label(camera_group, text="카메라 초기화 중...")
        self.camera_label.pack(expand=True)
        
        # 결과 그룹
        result_group = ttk.LabelFrame(right_panel, text="분석 결과", padding=10)
        result_group.pack(fill=tk.BOTH, expand=True)
        
        # 스크롤 가능한 텍스트 영역
        text_frame = ttk.Frame(result_group)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = tk.Text(text_frame, height=8, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return right_panel

    def start_camera(self):
        """카메라 시작"""
        try:
            self.camera_thread = CameraThread(self.callback_dict)
            self.camera_thread.start()
        except Exception as e:
            self.on_camera_error(f"카메라 시작 실패: {str(e)}")

    def update_camera_frame(self, frame):
        """카메라 프레임 업데이트"""
        try:
            if frame is None or frame.size == 0:
                return

            # 카메라 프레임을 거울모드로 표시 (운동 분석 시작 전 구도 맞추기용)
            frame = cv2.flip(frame, 1)
            
            # PIL Image로 변환
            pil_image = Image.fromarray(frame)
            
            # tkinter에서 사용할 수 있도록 변환
            photo = ImageTk.PhotoImage(pil_image)
            
            # 라벨에 이미지 설정
            self.camera_label.configure(image=photo, text="")
            self.camera_label.image = photo  # 참조 유지
            
        except Exception as e:
            print(f"프레임 업데이트 오류: {e}")

    def on_camera_error(self, error_msg):
        """카메라 에러 처리"""
        self.camera_label.configure(text=f"카메라 오류: {error_msg}")
        self.status_label.configure(text="카메라 연결 실패")

    def select_exercise(self):
        """운동 선택"""
        self.selected_exercise = self.exercise_var.get()
        
        # 상태 메시지 업데이트
        exercise_names = {"squat": "스쿼트", "lunge": "런지", "plank": "플랭크"}
        exercise_name = exercise_names.get(self.selected_exercise, "")
        if exercise_name:
            self.status_label.configure(text=f"{exercise_name} 분석 준비됨")

    def start_analysis(self):
        """분석 시작"""
        if not self.selected_exercise:
            messagebox.showwarning("경고", "운동을 선택해주세요.")
            return

        try:
            # 분석 중 상태로 변경
            self.is_analyzing = True

            # 카메라 안전하게 중지
            print("[DEBUG] 카메라 스레드 중지 시작...")
            if self.camera_thread and self.camera_thread.is_alive():
                self.camera_thread.stop()
                self.camera_thread.join(timeout=5.0)

            self.camera_label.configure(text="분석 준비 중... 잠시 기다려주세요.")

            # 메모리 정리
            import gc
            gc.collect()

            # 약간의 지연으로 메모리 안정화
            self.root.after(1000, self._start_analysis_delayed)

        except Exception as e:
            print(f"분석 시작 준비 오류: {e}")
            self.on_analysis_error(f"분석 시작 준비 중 오류: {str(e)}")

    def _start_analysis_delayed(self):
        """지연된 분석 시작 - 메모리 안정화 후"""
        try:
            # 타이머 초기화 및 시작
            self.elapsed_time = 0
            self.timer_label.configure(text="경과 시간: 0초")
            self.start_analysis_timer()

            # 분석 스레드 시작
            duration = self.duration_seconds.get()
            self.analyzer_thread = ExerciseAnalyzerThread(
                self.selected_exercise, 
                duration, 
                self.callback_dict
            )
            self.analyzer_thread.start()

            # UI 상태 업데이트
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
            self.status_label.configure(text="분석이 시작되었습니다...")

        except Exception as e:
            print(f"지연된 분석 시작 오류: {e}")
            self.on_analysis_error(f"분석 시작 오류: {str(e)}")

    def start_analysis_timer(self):
        """분석 타이머 시작"""
        if self.is_analyzing:
            self.elapsed_time += 1
            self.timer_label.configure(text=f"경과 시간: {self.elapsed_time}초")
            self.root.after(1000, self.start_analysis_timer)

    def stop_analysis(self, finished_naturally=False):
        """분석 중지"""
        # 분석 스레드 중지
        if self.analyzer_thread and self.analyzer_thread.is_alive():
            self.analyzer_thread.stop()
            self.analyzer_thread.join(timeout=5.0)

        # 상태 초기화
        self.is_analyzing = False

        # 카메라 재시작
        self.start_camera()

        # UI 상태 복원
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

        if not finished_naturally:
            self.status_label.configure(text="분석이 중지되었습니다.")

    def update_status(self, status_msg):
        """상태 업데이트"""
        self.status_label.configure(text=status_msg)

    def on_analysis_finished(self, video_path, report_path):
        """분석 완료 처리"""
        self.stop_analysis(finished_naturally=True)

        # 결과 요약
        summary = f"""분석 완료!

📹 비디오: {os.path.basename(video_path)}
📄 리포트: {os.path.basename(report_path)}
📁 위치: {os.path.dirname(video_path)}
"""

        # 리포트 내용 읽기
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()

            full_result = summary + "\n" + "="*50 + "\n상세 분석 결과\n" + "="*50 + "\n\n" + report_content
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, full_result)
        except Exception as e:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, summary + f"\n리포트 파일을 읽을 수 없습니다: {e}")

        # 상태 및 알림
        self.status_label.configure(text="분석 완료!")
        messagebox.showinfo(
            "분석 완료",
            f"분석이 완료되었습니다!\n\n비디오: {os.path.basename(video_path)}\n리포트: {os.path.basename(report_path)}"
        )

    def on_analysis_error(self, error_msg):
        """분석 오류 처리"""
        self.stop_analysis(finished_naturally=True)

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"분석 오류: {error_msg}")
        self.status_label.configure(text="분석 실패")

        messagebox.showerror(
            "오류",
            f"분석 중 오류가 발생했습니다:\n{error_msg}"
        )

    def on_closing(self):
        """애플리케이션 종료 시 정리"""
        # 모든 스레드 정리
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.stop()
            self.camera_thread.join(timeout=3.0)

        if self.analyzer_thread and self.analyzer_thread.is_alive():
            self.analyzer_thread.stop()
            self.analyzer_thread.join(timeout=5.0)

        # 애플리케이션 종료
        self.root.destroy() 