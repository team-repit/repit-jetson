import cv2
import mediapipe as mp
import numpy as np
import os
import time
import threading
import queue
import subprocess
from typing import List, Dict, Tuple, Optional
from collections import Counter as GradeCounter
import json

# MediaPipe Pose 모델 초기화
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

class UniversalTTS:
    """모든 플랫폼에서 작동하는 TTS 시스템 (하이브리드 접근법)"""
    
    def __init__(self):
        self.feedback_queue = queue.Queue()
        self.last_feedback_time = {}  # 각 오류별 마지막 피드백 시간
        self.feedback_cooldown = 3.0  # 같은 오류에 대한 피드백 쿨다운 (초)
        self.min_feedback_interval = 2.0  # 최소 피드백 간격 (초)
        self.last_general_feedback = 0  # 마지막 일반 피드백 시간
        self.running = True
        self.feedback_thread = threading.Thread(target=self._feedback_worker, daemon=True)
        
        # 플랫폼별 TTS 설정
        self.platform = self._detect_platform()
        self.setup_tts()
        
        # 젯슨에서 TTS 도구 설치 안내
        if self.platform == "Jetson":
            self._check_jetson_tts_tools()
        
        self.feedback_thread.start()
        
        # 피드백 메시지 매핑
        self.feedback_messages = {
            "엉덩이 처짐": "엉덩이를 들어올리세요. 허리가 꺾이지 않도록 주의하세요.",
            "엉덩이 솟음": "엉덩이를 너무 높이 들지 마세요. 몸을 일직선으로 유지하세요.",
            "고개 정렬 불량": "고개를 똑바로 유지하세요. 목이 꺾이지 않도록 하세요.",
            "팔꿈치 정렬 불량": "팔꿈치를 어깨 바로 아래에 위치시키세요.",
            "무릎 굽힘": "다리를 펴고 긴장을 유지하세요."
        }
    
    def _detect_platform(self):
        """플랫폼 감지"""
        import platform
        system = platform.system()
        
        # 젯슨 감지 (ARM64 + Linux)
        if system == "Linux":
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpu_info = f.read()
                    if 'aarch64' in cpu_info or 'ARM' in cpu_info:
                        return "Jetson"
            except:
                pass
        return system
    
    def setup_tts(self):
        """플랫폼별 TTS 설정"""
        if self.platform == "Jetson":
            # 젯슨 전용 TTS 설정 (gTTS 우선, Festival 백업, espeak 최종)
            self.tts_method = "gtts"
            self.backup_tts = "festival"
            print("TTS: 젯슨 Google TTS 우선 사용 (한국어 품질 최고)")
            print("백업 TTS: Festival TTS")
            print("최종 백업: espeak TTS")
        elif self.platform == "Darwin":  # macOS
            self.tts_method = "gtts"
            self.backup_tts = "native_say"
            print("TTS: Google TTS 우선 사용")
            print("백업 TTS: macOS say 명령어")
        elif self.platform == "Windows":
            self.tts_method = "gtts"
            self.backup_tts = "pyttsx3"
            print("TTS: Google TTS 우선 사용")
            print("백업 TTS: Windows pyttsx3")
        elif self.platform == "Linux":
            self.tts_method = "gtts"
            self.backup_tts = "festival"
            print("TTS: Google TTS 우선 사용")
            print("백업 TTS: Festival TTS")
        else:
            self.tts_method = "gtts"
            self.backup_tts = "pyttsx3"
            print("TTS: Google TTS 우선 사용")
            print("백업 TTS: pyttsx3")
    
    def _feedback_worker(self):
        """백그라운드에서 TTS 피드백을 처리하는 워커 스레드"""
        while self.running:
            try:
                feedback_data = self.feedback_queue.get(timeout=1.0)
                if feedback_data:
                    message, priority = feedback_data
                    self._speak_feedback(message, priority)
                self.feedback_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS 피드백 오류: {e}")
    
    def _speak_feedback(self, message: str, priority: str):
        """플랫폼별 TTS 사용"""
        try:
            if self.platform == "Jetson":
                # 젯슨 gTTS 우선 시도
                self._speak_gtts(message, priority)
            elif self.tts_method == "gtts":
                # Google TTS 우선 시도
                self._speak_gtts(message, priority)
            else:
                # 기본 TTS 시도
                self._speak_backup(message)
        except Exception as e:
            print(f"주 TTS 실패: {e}")
            # 플랫폼별 백업 TTS 시도
            self._speak_backup(message)
    
    def _speak_gtts(self, message: str, priority: str):
        """Google TTS 메인 (우선 사용)"""
        try:
            from gtts import gTTS
            tts = gTTS(text=message, lang='ko')
            temp_file = "temp_speech.mp3"
            tts.save(temp_file)
            
            # 플랫폼별 오디오 재생
            if self.platform == "Darwin":  # macOS
                subprocess.run(['afplay', temp_file], check=True)
            elif self.platform == "Windows":
                os.startfile(temp_file)  # Windows 기본 플레이어
            elif self.platform in ["Linux", "Jetson"]:
                # Linux/젯슨에서 MP3 재생을 위한 여러 방법 시도
                self._play_mp3_linux(temp_file)
            
            # 임시 파일 삭제
            os.remove(temp_file)
            print("Google TTS 사용됨")
            
        except ImportError:
            print("gTTS가 설치되지 않았습니다. 백업 TTS를 사용합니다.")
            raise
        except Exception as e:
            print(f"Google TTS 실패: {e}")
            raise
    
    def _play_mp3_linux(self, mp3_file: str):
        """Linux/젯슨에서 MP3 파일 재생"""
        # 여러 MP3 플레이어 중 하나를 찾아서 사용
        players = [
            ('mpg123', ['mpg123', mp3_file]),
            ('ffplay', ['ffplay', '-nodisp', '-autoexit', mp3_file]),
            ('mpv', ['mpv', '--no-video', mp3_file]),
            ('cvlc', ['cvlc', '--play-and-exit', mp3_file])
        ]
        
        for player_name, cmd in players:
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"MP3 재생: {player_name} 사용")
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        # MP3 플레이어가 없으면 WAV로 변환 후 재생
        try:
            import pydub
            audio = pydub.AudioSegment.from_mp3(mp3_file)
            wav_file = mp3_file.replace('.mp3', '.wav')
            audio.export(wav_file, format="wav")
            subprocess.run(['aplay', wav_file], check=True)
            os.remove(wav_file)
            print("MP3를 WAV로 변환하여 재생")
        except ImportError:
            print("pydub가 설치되지 않아 MP3를 WAV로 변환할 수 없습니다")
            raise Exception("Linux에서 MP3 재생을 위한 도구가 없습니다")
    
    def _speak_backup(self, message: str):
        """플랫폼별 백업 TTS"""
        try:
            if self.platform == "Darwin":  # macOS
                subprocess.run(['say', '-r', '150', message], check=True)
            elif self.platform == "Windows":
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.say(message)
                engine.runAndWait()
            elif self.platform in ["Linux", "Jetson"]:
                subprocess.run(['espeak', '-s', '120', message], check=True)
            print(f"백업 TTS 사용됨")
            
        except Exception as e:
            print(f"백업 TTS도 실패: {e}")
            print("음성 피드백을 제공할 수 없습니다.")
    
    def add_feedback(self, error_type: str, priority: str = "normal"):
        """지능적 피드백 추가 (잔소리꾼 방지)"""
        current_time = time.time()
        
        # 같은 오류에 대한 쿨다운 체크
        if error_type in self.last_feedback_time:
            if current_time - self.last_feedback_time[error_type] < self.feedback_cooldown:
                return False
        
        # 최소 피드백 간격 체크
        if current_time - self.last_general_feedback < self.min_feedback_interval:
            return False
        
        # 오류가 2개 이상일 때는 우선순위 1위만 피드백 (잔소리꾼 방지)
        if hasattr(self, 'current_hold_errors') and len(self.current_hold_errors) >= 2:
            priority_errors = self.get_priority_order(self.current_hold_errors)
            if error_type != priority_errors[0]:  # 우선순위 1위만
                return False
        
        # 피드백 메시지 가져오기
        message = self.feedback_messages.get(error_type, f"{error_type}을 수정하세요.")
        
        # 피드백 큐에 추가
        self.feedback_queue.put((message, priority))
        
        # 시간 업데이트
        self.last_feedback_time[error_type] = current_time
        self.last_general_feedback = current_time
        
        return True
    
    def get_priority_order(self, errors: List[str]) -> List[str]:
        """오류를 우선순위 순서로 정렬 (안전성 > 효과성 > 최적화)"""
        priority_order = [
            "엉덩이 처짐",        # 🚨 안전성 최우선
            "엉덩이 솟음",        # 🚨 안전성 최우선  
            "고개 정렬 불량",     # ⚠️ 효과성
            "팔꿈치 정렬 불량",   # ⚠️ 효과성
            "무릎 굽힘"          # 💡 최적화
        ]
        
        # 우선순위 순서로 정렬
        sorted_errors = []
        for priority_error in priority_order:
            if priority_error in errors:
                sorted_errors.append(priority_error)
        
        return sorted_errors
    
    def add_encouragement(self, hold_time: float):
        """격려 메시지 추가"""
        current_time = time.time()
        if current_time - self.last_general_feedback < 10.0:  # 10초 간격
            return
        
        encouragements = [
            "잘 하고 있습니다!",
            "자세를 유지하세요!",
            "한 번 더 힘내세요!",
            "훌륭합니다!"
        ]
        
        message = encouragements[int(hold_time) % len(encouragements)]
        self.feedback_queue.put((message, "encouragement"))
        self.last_general_feedback = current_time
    
    def stop(self):
        """TTS 매니저 정리"""
        self.running = False
        self.feedback_thread.join(timeout=1.0)

    def _check_jetson_tts_tools(self):
        """젯슨에서 필요한 TTS 도구들이 설치되어 있는지 확인하고 안내"""
        print("\n" + "="*60)
        print("젯슨 TTS 도구 설치 확인 중...")
        print("="*60)
        
        tools_status = {}
        
        # Google TTS 확인 (한국어 품질 최고)
        try:
            import gtts
            tools_status['Google TTS (gTTS)'] = "✅ 설치됨 (한국어 품질 최고)"
        except ImportError:
            tools_status['Google TTS (gTTS)'] = "❌ 설치 필요 (1순위)"
        
        # espeak TTS 확인 (최종 백업)
        try:
            subprocess.run(['espeak', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            tools_status['espeak TTS'] = "✅ 설치됨 (최종 백업)"
        except:
            tools_status['espeak TTS'] = "❌ 설치 필요"
        
        # MP3 재생 도구 확인
        mp3_players = ['mpg123', 'ffplay', 'mpv', 'cvlc']
        mp3_status = "❌ 설치 필요"
        for player in mp3_players:
            try:
                subprocess.run([player, '--help'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                mp3_status = f"✅ {player} 사용 가능"
                break
            except:
                continue
        tools_status['MP3 Player'] = mp3_status
        
        # 상태 출력
        for tool, status in tools_status.items():
            print(f"{tool}: {status}")
        
        # 설치 안내
        if any("❌" in status for status in tools_status.values()):
            print("\n📋 젯슨에서 TTS 도구 설치 방법:")
            print("\n🥇 Google TTS (1순위, 한국어 품질 최고):")
            print("pip install gtts pydub")
            
            print("\n🥈 기본 TTS 도구들 (2순위):")
            print("sudo apt-get update")
            print("sudo apt-get install espeak")                      # espeak TTS
            print("sudo apt-get install mpg123")                      # MP3 재생
            
            print("\n📦 Python 패키지:")
            print("pip install gtts pydub numpy")
        
        print("="*60 + "\n")

def calculate_angle(a: list, b: list, c: list) -> float:
    """세 점 사이의 각도를 계산하는 함수 (결과값: 0-180)"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

class ComprehensivePlankGrader:
    """
    'AI 플랭크 자세 교정을 위한 종합 평가 기준'을 기반으로 한 새로운 평가 클래스.
    계층적 피드백 구조(안전성 > 효과성 > 최적화)를 따릅니다.
    """
    def __init__(self):
        pass

    def evaluate_errors(self, angles: dict, landmarks: dict) -> List[str]:
        """
        자세를 평가하고 발생한 모든 오류 목록을 계층적으로 반환합니다.
        """
        errors = []
        
        # 레벨 1: 안전성 (Safety) - 즉시 교정 대상
        if 'body' in angles and angles['body'] > 200: # 190 -> 200
            errors.append("엉덩이 처짐")

        # 레벨 2: 효과성 (Effectiveness) - 주요 교정 대상
        if 'body' in angles and angles['body'] < 150: # 165 -> 150
            errors.append("엉덩이 솟음")
        if 'neck' in angles and not (150 <= angles['neck'] <= 210): # 165-195 -> 150-210
            errors.append("고개 정렬 불량")

        # 레벨 3: 최적화 (Optimization) - 미세 조정
        is_elbow_misaligned = 'arm' in angles and not (60 <= angles['arm'] <= 120) # 75-105 -> 60-120
        # 팔꿈치가 어깨보다 너무 앞이나 뒤에 있는지 확인
        shoulder_x = (landmarks['left_shoulder'][0] + landmarks['right_shoulder'][0]) / 2
        elbow_x = (landmarks['left_elbow'][0] + landmarks['right_elbow'][0]) / 2
        shoulder_hip_dist = abs(landmarks['left_shoulder'][0] - landmarks['left_hip'][0]) # 기준 거리
        is_elbow_pos_off = abs(shoulder_x - elbow_x) > shoulder_hip_dist * 0.40 # 0.20 -> 0.40

        if is_elbow_misaligned or is_elbow_pos_off:
            errors.append("팔꿈치 정렬 불량")
            
        if 'leg' in angles and angles['leg'] < 150: # 165 -> 150
            errors.append("무릎 굽힘")

        return errors

    def get_grade_from_errors(self, errors: List[str]) -> str:
        """오류 개수에 따라 등급을 반환합니다."""
        num_errors = len(set(errors))
        if num_errors == 0: return "A"
        elif num_errors == 1: return "B"
        elif num_errors == 2: return "C"
        elif num_errors == 3: return "D"
        else: return "F"

    def get_error_priority(self, error: str) -> str:
        """오류의 우선순위를 반환합니다."""
        safety_errors = ["엉덩이 처짐", "엉덩이 솟음"]
        if error in safety_errors:
            return "urgent"
        return "normal"

# 오류 키와 상세 설명을 매핑하는 딕셔너리
ERROR_CRITERIA_MAP = {
    "엉덩이 처짐": "엉덩이 처짐 (Hip Sag / 허리 꺾임): 코어와 둔근의 힘이 풀려 허리가 U자로 꺾이는 현상.",
    "엉덩이 솟음": "엉덩이 솟음 (Hip Pike): 코어의 부담을 줄이기 위해 엉덩이를 과도하게 높이 드는 자세.",
    "고개 정렬 불량": "고개 떨굼 / 젖힘 (Head/Neck Misalignment): 목이 척추의 중립선에서 벗어나는 자세.",
    "팔꿈치 정렬 불량": "팔꿈치/손목 정렬 불량 (Elbow/Wrist Misalignment): 팔꿈치가 어깨 바로 아래에 위치하지 않는 자세.",
    "무릎 굽힘": "무릎 굽힘 (Knee Bend): 다리의 긴장이 풀려 무릎이 굽혀지는 현상."
}

def save_report(report_path: str, hold_results: List[Dict]):
    """분석 결과와 전체 평가 기준을 텍스트 파일로 저장합니다."""
    total_hold_time = sum(res['duration'] for res in hold_results)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("실시간 플랭크 자세 분석 리포트 (TTS 피드백 포함)\n")
        f.write("="*50 + "\n")
        f.write(f"총 플랭크 유지 시간: {total_hold_time:.2f}초\n\n")
        
        f.write("구간별 상세 결과:\n")
        if not hold_results:
            f.write("- 플랭크 자세가 감지되지 않았습니다.\n")
        
        for i, res in enumerate(hold_results):
            grade = res['grade']
            duration = res['duration']
            errors = res['errors']
            f.write(f"\n--- {i+1}번째 구간 (유지 시간: {duration:.2f}초): 등급 {grade} ---\n")
            if errors:
                f.write("  [주요 발생 오류]\n")
                # 가장 많이 발생한 오류 순으로 정렬
                sorted_errors = sorted(errors.items(), key=lambda item: item[1], reverse=True)
                for error_key, count in sorted_errors:
                    error_description = ERROR_CRITERIA_MAP.get(error_key, "알 수 없는 오류")
                    f.write(f"  - {error_description} ({count}회 감지)\n")
            else:
                f.write("  - 모든 기준을 만족했습니다.\n")

        # 전체 평가 기준 추가
        f.write("\n\n" + "="*50 + "\n")
        f.write("          자세 평가 기준 (참고)\n")
        f.write("="*50 + "\n\n")

        f.write("1. 플랭크 (Plank) 종합 기준\n")
        f.write("-------------------------\n")
        f.write("레벨 1: 안전성 (Safety) - 즉시 교정 대상\n")
        f.write("- 엉덩이 처짐 (Hip Sag / 허리 꺾임): 어깨-엉덩이-발목 각도 > 200도\n\n")
        f.write("레벨 2: 효과성 (Effectiveness) - 주요 교정 대상\n")
        f.write("- 엉덩이 솟음 (Hip Pike): 어깨-엉덩이-발목 각도 < 150도\n")
        f.write("- 고개 떨굼 / 젖힘 (Head/Neck Misalignment): 귀-어깨-엉덩이 각도가 150도~210도 범위를 벗어남\n\n")
        f.write("레벨 3: 최적화 (Optimization) - 미세 조정\n")
        f.write("- 팔꿈치/손목 정렬 불량 (Elbow/Wrist Misalignment): 어깨-팔꿈치-손목 각도가 60도~120도 범위를 벗어나거나, 팔꿈치가 어깨 수직선상에서 벗어남\n")
        f.write("- 무릎 굽힘 (Knee Bend): 고관절-무릎-발목 각도 < 150도\n\n")

    print(f"리포트가 '{report_path}'에 저장되었습니다.")

def run_plank_analysis(duration_seconds=120, stop_callback=None):
    """실시간 카메라를 통한 플랭크 분석 함수 (TTS 피드백 포함)
    
    Args:
        duration_seconds (int): 분석할 시간 (초), 기본값 120초 (2분)
        stop_callback (callable): 분석 중지 여부를 확인하는 콜백 함수
    """
    
    # 중지 플래그 초기화
    run_plank_analysis._stop_analysis = False

    try:
        # 카메라 초기화
        print("카메라 초기화 중...")
        cap = cv2.VideoCapture(0)  # 기본 카메라 (보통 내장 웹캠)
        
        if not cap.isOpened():
            print("카메라를 열 수 없습니다.")
            return None, None
        
        # 카메라 테스트
        print("카메라 테스트 중...")
        ret, test_frame = cap.read()
        if not ret:
            print("카메라에서 프레임을 읽을 수 없습니다.")
            cap.release()
            return None, None
        
        print(f"카메라 성공: {test_frame.shape}")
        
    except Exception as e:
        print(f"카메라 초기화 오류: {str(e)}")
        return None, None
    
    # 카메라 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 영상 저장을 위한 설정
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 30.0
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    # output 디렉토리 생성 및 확인 (현재 스크립트 위치 기준)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"output 디렉토리를 생성했습니다: {output_dir}")
    
    # 타임스탬프를 포함한 파일명 생성 (output 디렉토리 내)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_video_path = os.path.join(output_dir, f"plank_realtime_tts_analysis_{timestamp}.mp4")
    output_report_path = os.path.join(output_dir, f"plank_realtime_tts_report_{timestamp}.txt")
    
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))
    
    try:
        # TTS 피드백 매니저 초기화
        print("TTS 매니저 초기화 중...")
        tts_manager = UniversalTTS()
        
        # 플랭크 등급 평가기 초기화
        print("플랭크 등급 평가기 초기화 중...")
        grader = ComprehensivePlankGrader()
        
        # 변수 초기화
        all_hold_results = []
        current_hold_errors = GradeCounter()
        is_holding = False
        hold_start_time = 0
        current_grade = "N/A"
        
        print("초기화 완료!")
        
    except Exception as e:
        print(f"초기화 오류: {str(e)}")
        cap.release()
        out.release()
        return None, None
    
    # 타이머 설정
    start_time = time.time()
    recording_duration = duration_seconds
    
    print(f"플랭크 분석을 시작합니다. {duration_seconds}초간 카메라가 켜집니다.")
    print("TTS 피드백이 실시간으로 제공됩니다!")
    print("플랭크 자세를 취하세요!")
    print("종료하려면 'q'를 누르세요.")
    
    # 시작 안내 메시지
    tts_manager.add_feedback("시작", "encouragement")
    
    while cap.isOpened():
        try:
            ret, frame = cap.read()
            if not ret: 
                print("프레임을 읽을 수 없습니다.")
                break
            
            # 현재 시간 계산
            current_time = time.time()
            elapsed_time = current_time - start_time
            remaining_time = max(0, recording_duration - elapsed_time)
            
            # 시간 경과 시 종료
            if elapsed_time >= recording_duration:
                print(f"설정된 시간 {duration_seconds}초가 경과했습니다.")
                break
            
            try:
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = pose.process(image)
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"이미지 처리 오류: {str(e)}")
                continue
                
        except Exception as e:
            print(f"메인 루프 오류: {str(e)}")
            break
        
        # 포즈 랜드마크가 감지되지 않은 경우 건너뛰기
        if not results.pose_landmarks:
            print("포즈 랜드마크가 감지되지 않았습니다. 카메라 앞에 사람이 있는지 확인하세요.")
            continue
            
        try:
            landmarks = results.pose_landmarks.landmark
            h, w, _ = image.shape
            
            lm_data = {
                'left_shoulder': [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y * h],
                'left_hip': [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y * h],
                'left_knee': [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y * h],
                'left_ankle': [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y * h],
                'left_ear': [landmarks[mp_pose.PoseLandmark.LEFT_EAR.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_EAR.value].y * h],
                'left_elbow': [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y * h],
                'left_wrist': [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y * h],
                'right_shoulder': [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y * h],
                'right_hip': [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y * h],
                'right_knee': [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y * h],
                'right_ankle': [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y * h],
                'right_ear': [landmarks[mp_pose.PoseLandmark.RIGHT_EAR.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_EAR.value].y * h],
                'right_elbow': [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y * h],
                'right_wrist': [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y * h],
            }

            # 플랭크 자세 기본 조건 확인
            shoulder_y = (lm_data['left_shoulder'][1] + lm_data['right_shoulder'][1]) / 2
            hip_y = (lm_data['left_hip'][1] + lm_data['right_hip'][1]) / 2
            if shoulder_y < hip_y + 50: # 어깨가 엉덩이보다 너무 낮지 않은지 (엎드린 자세 확인)
                is_plank_pose = True
            else:
                is_plank_pose = False

            if is_plank_pose:
                # 각도 계산
                angles = {}
                use_left_side = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].visibility > landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].visibility
                if use_left_side:
                    angles['body'] = calculate_angle(lm_data['left_shoulder'], lm_data['left_hip'], lm_data['left_ankle'])
                    angles['neck'] = calculate_angle(lm_data['left_ear'], lm_data['left_shoulder'], lm_data['left_hip'])
                    angles['arm'] = calculate_angle(lm_data['left_shoulder'], lm_data['left_elbow'], lm_data['left_wrist'])
                    angles['leg'] = calculate_angle(lm_data['left_hip'], lm_data['left_knee'], lm_data['left_ankle'])
                else:
                    angles['body'] = calculate_angle(lm_data['right_shoulder'], lm_data['right_hip'], lm_data['right_ankle'])
                    angles['neck'] = calculate_angle(lm_data['right_ear'], lm_data['right_shoulder'], lm_data['right_hip'])
                    angles['arm'] = calculate_angle(lm_data['right_shoulder'], lm_data['right_elbow'], lm_data['right_wrist'])
                    angles['leg'] = calculate_angle(lm_data['right_hip'], lm_data['right_knee'], lm_data['right_ankle'])
                
                # 플랭크 유지 상태 관리
                if not is_holding:
                    is_holding = True
                    hold_start_time = time.time()
                    current_hold_errors.clear()

                # 오류 평가
                errors_in_frame = grader.evaluate_errors(angles, lm_data)
                
                # 현재 등급 계산하여 TTS 매니저에 전달
                current_grade = grader.get_grade_from_errors(list(current_hold_errors.keys()))
                tts_manager.current_grade = current_grade
                tts_manager.current_hold_errors = current_hold_errors
                
                # 새로운 오류에 대해서만 TTS 피드백 제공
                for error in errors_in_frame:
                    if error not in current_hold_errors:
                        priority = grader.get_error_priority(error)
                        tts_manager.add_feedback(error, priority)
                
                current_hold_errors.update(errors_in_frame)
                current_grade = grader.get_grade_from_errors(list(current_hold_errors.keys()))

            elif is_holding: # 플랭크 자세가 깨졌을 때
                is_holding = False
                hold_duration = time.time() - hold_start_time
                if hold_duration > 1: # 1초 이상 유지했을 때만 기록
                    final_grade = grader.get_grade_from_errors(list(current_hold_errors.keys()))
                    all_hold_results.append({
                        'duration': hold_duration,
                        'grade': final_grade,
                        'errors': current_hold_errors
                    })

        except Exception as e:
            pass
        
        # ------------------ 화면 표시 정보 수정 ------------------
        # 상단 정보 박스
        cv2.rectangle(image, (0,0), (frame_width, 120), (245,117,16), -1)
        
        # 타이머 표시
        cv2.putText(image, f'TIME: {remaining_time:.1f}s', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
        
        # STATUS
        status_text = "HOLDING" if is_holding else "READY"
        status_color = (0, 255, 0) if is_holding else (0, 0, 255)
        cv2.putText(image, 'STATUS', (int(frame_width * 0.3), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(image, status_text, (int(frame_width * 0.3), 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5, status_color, 3, cv2.LINE_AA)
        
        # HOLD TIME
        hold_time = (time.time() - hold_start_time) if is_holding else 0
        cv2.putText(image, 'HOLD TIME', (int(frame_width * 0.5), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(image, f"{hold_time:.1f}s", (int(frame_width * 0.5), 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3, cv2.LINE_AA)

        # GRADE
        cv2.putText(image, 'GRADE', (int(frame_width * 0.7), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(image, current_grade, (int(frame_width * 0.7), 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3, cv2.LINE_AA)
        
        # TTS 상태 표시
        cv2.putText(image, 'TTS: ON', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2, cv2.LINE_AA)
        
        # 하단 안내 메시지
        cv2.rectangle(image, (0, frame_height-50), (frame_width, frame_height), (0,0,0), -1)
        cv2.putText(image, 'Press Q to quit early | TTS Feedback Active', (10, frame_height-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2, cv2.LINE_AA)
        # ----------------------------------------------------
        
        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2), 
                                mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2))               
        
        out.write(image)
        
        # macOS에서는 GUI 없이 콘솔 모드로 실행
        print(f"프레임 처리 중... STATUS: {'HOLDING' if is_holding else 'READY'}, TIME: {hold_time:.1f}s, GRADE: {current_grade}")

        # OpenCV 창 표시 (젯슨에서만 활성화, macOS에서는 비활성화)
        # try:
        #     cv2.namedWindow('Real-time Plank Analysis with TTS', cv2.WINDOW_NORMAL)
        #     cv2.resizeWindow('Real-time Plank Analysis with TTS', 1280, 720)
        # except Exception as e:
        #     print(f"창 생성 실패, 기본 창 사용: {e}")
        
        # try:
        #     cv2.imshow('Real-time Plank Analysis with TTS', image)
        # except Exception as e:
        #     print(f"이미지 표시 실패: {e}")

        # 플랫폼별 OpenCV 창 표시
        import platform
        system = platform.system()
        
        # 젯슨 감지 (ARM64 + Linux)
        is_jetson = False
        if system == "Linux":
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpu_info = f.read()
                    if 'aarch64' in cpu_info or 'ARM' in cpu_info:
                        is_jetson = True
            except:
                pass
        
        # 젯슨에서만 스켈레톤 표시
        if is_jetson:
            try:
                cv2.namedWindow('Real-time Plank Analysis with TTS', cv2.WINDOW_NORMAL)
                cv2.resizeWindow('Real-time Plank Analysis with TTS', 1280, 720)
                cv2.imshow('Real-time Plank Analysis with TTS', image)
                
                # 젯슨에서는 키 입력도 처리
                key = cv2.waitKey(10) & 0xFF
                if key == ord('q'): 
                    print("사용자가 'q'를 눌러 분석을 중단했습니다.")
                    break
                elif key == ord('s'):  # 's' 키로 스크린샷 저장
                    screenshot_path = os.path.join(output_dir, f"screenshot_{timestamp}_{int(time.time())}.jpg")
                    cv2.imwrite(screenshot_path, image)
                    print(f"스크린샷 저장: {screenshot_path}")
                    
            except Exception as e:
                print(f"젯슨 OpenCV 창 오류: {e}")
        else:
            # macOS 등에서는 GUI 없이 실행
            time.sleep(0.01)  # 10ms 대기
        
        # 시간 기반 종료 조건 (예: 5초마다 상태 출력)
        if int(time.time()) % 5 == 0 and int(time.time()) != getattr(locals(), '_last_status_time', 0):
            print(f"플랭크 분석 진행 중... 시간: {remaining_time:.1f}초")
            _last_status_time = int(time.time())
        
        # 분석 중지 체크 (전역 변수로 제어)
        if hasattr(run_plank_analysis, '_stop_analysis') and run_plank_analysis._stop_analysis:
            print("분석이 중지되었습니다.")
            break

        # 분석 중지 체크 (콜백 함수로 제어)
        if stop_callback and stop_callback():
            print("분석이 중지되었습니다.")
            break

    # 마지막 홀드 세션 저장
    if is_holding:
        hold_duration = time.time() - hold_start_time
        if hold_duration > 1:
            final_grade = grader.get_grade_from_errors(list(current_hold_errors.keys()))
            all_hold_results.append({
                'duration': hold_duration,
                'grade': final_grade,
                'errors': current_hold_errors
            })

    # TTS 매니저 정리
    tts_manager.stop()
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()

    # 결과 저장
    save_report(output_report_path, all_hold_results)
    print(f"분석 영상이 '{output_video_path}'에 저장되었습니다.")
    print(f"분석 리포트가 '{output_report_path}'에 저장되었습니다.")
    print("TTS 피드백이 실시간으로 제공되었습니다.")
    
    # 결과 파일 경로 반환
    return output_video_path, output_report_path

def main():
    """기존 main 함수 (호환성 유지)"""
    video_path, report_path = run_plank_analysis(120)  # 기본 2분
    if video_path and report_path:
        print(f"분석 완료: {video_path}, {report_path}")
    else:
        print("분석 실패")

if __name__ == "__main__":
    main()
