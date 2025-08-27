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
            "측면 불안정성": "몸통을 똑바로 유지하세요. 좌우로 기울어지지 마세요.",
            "무릎 모임": "앞 무릎이 발끝 방향을 향하도록 하세요. 안쪽으로 무너지지 마세요.",
            "과도한 무릎 전진": "앞 무릎이 발끝을 넘어가지 않도록 주의하세요.",
            "상체 숙여짐": "가슴을 펴고 상체를 일으키세요.",
            "부족한 깊이": "더 깊게 내려가세요. 근육을 충분히 활성화하세요.",
            "좁은 스탠스": "발을 어깨너비만큼 벌리세요. 안정적인 자세를 유지하세요.",
            "앞발목 가동성 부족": "앞발목을 더 굽혀보세요. 가동성을 높이세요."
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
        if hasattr(self, 'current_rep_errors') and len(self.current_rep_errors) >= 2:
            priority_errors = self.get_priority_order(self.current_rep_errors)
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
            "측면 불안정성",      # 🚨 안전성 최우선
            "무릎 모임",          # 🚨 안전성 최우선  
            "과도한 무릎 전진",   # 🚨 안전성 최우선
            "상체 숙여짐",        # ⚠️ 효과성
            "부족한 깊이",        # ⚠️ 효과성
            "좁은 스탠스",        # ⚠️ 효과성
            "앞발목 가동성 부족"  # 💡 최적화
        ]
        
        # 우선순위 순서로 정렬
        sorted_errors = []
        for priority_error in priority_order:
            if priority_error in errors:
                sorted_errors.append(priority_error)
        
        return sorted_errors
    
    def add_encouragement(self, rep_count: int):
        """격려 메시지 추가"""
        current_time = time.time()
        if current_time - self.last_general_feedback < 5.0:  # 5초 간격
            return
        
        encouragements = [
            "잘 하고 있습니다!",
            "자세를 유지하세요!",
            "한 번 더 힘내세요!",
            "훌륭합니다!"
        ]
        
        message = encouragements[rep_count % len(encouragements)]
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

class ComprehensiveLungeGrader:
    """
    'AI 런지 자세 교정을 위한 종합 평가 기준'을 기반으로 한 새로운 평가 클래스.
    계층적 피드백 구조(안전성 > 효과성 > 최적화)를 따릅니다.
    """
    def __init__(self):
        pass

    def evaluate_errors(self, angles: dict, landmarks: dict, front_leg: str) -> List[str]:
        """
        자세를 평가하고 발생한 모든 오류 목록을 계층적으로 반환합니다.
        """
        errors = []
        
        # 레벨 1: 안전성 (Safety) - 즉시 교정 대상
        # 1-1. 측면 불안정성 (기존 ±10도 -> ±15도)
        shoulder_angle_with_horizontal = calculate_angle(landmarks['right_shoulder'], landmarks['left_shoulder'], [landmarks['left_shoulder'][0] + 100, landmarks['left_shoulder'][1]])
        hip_angle_with_horizontal = calculate_angle(landmarks['right_hip'], landmarks['left_hip'], [landmarks['left_hip'][0] + 100, landmarks['left_hip'][1]])
        if not (165 <= shoulder_angle_with_horizontal <= 195) or not (165 <= hip_angle_with_horizontal <= 195):
            errors.append("측면 불안정성")

        # 1-2. 무릎 모임 (기존 10px -> 25px)
        if front_leg == 'left':
            if landmarks['left_knee'][0] < landmarks['left_hip'][0] - 25:
                 errors.append("무릎 모임")
        else:
            if landmarks['right_knee'][0] > landmarks['right_hip'][0] + 25:
                 errors.append("무릎 모임")

        # 1-3. 과도한 무릎 전진 (기존 20px -> 35px)
        if front_leg == 'left':
            if landmarks['left_knee'][0] > landmarks['left_ankle'][0] + 35:
                errors.append("과도한 무릎 전진")
        else: # front_leg == 'right'
            if landmarks['right_knee'][0] < landmarks['right_ankle'][0] - 35:
                errors.append("과도한 무릎 전진")

        # 레벨 2: 효과성 (Effectiveness) - 주요 교정 대상
        # 2-1. 상체 숙여짐 (기존 15도 -> 25도 허용, 즉 각도 < 75 -> < 65)
        if 'torso' in angles and angles['torso'] < 65: 
            errors.append("상체 숙여짐")

        # 2-2. 부족한 깊이 (기존 100도 -> 115도)
        if 'front_knee' in angles and angles['front_knee'] > 115:
            errors.append("부족한 깊이")
        if 'back_knee' in angles and angles['back_knee'] > 115:
            errors.append("부족한 깊이")

        # 2-3. 좁은 스탠스 (기존 어깨너비 20% -> 15%)
        ankle_dist = abs(landmarks['left_ankle'][0] - landmarks['right_ankle'][0])
        shoulder_dist = abs(landmarks['left_shoulder'][0] - landmarks['right_shoulder'][0])
        if shoulder_dist > 0 and ankle_dist < shoulder_dist * 0.15:
            errors.append("좁은 스탠스")

        # 레벨 3: 최적화 (Optimization) - 미세 조정
        # 3-1. 앞발목 가동성 부족 (기존 80도 -> 90도)
        if 'front_ankle' in angles and angles['front_ankle'] > 90:
            errors.append("앞발목 가동성 부족")

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
        safety_errors = ["측면 불안정성", "무릎 모임", "과도한 무릎 전진"]
        if error in safety_errors:
            return "urgent"
        return "normal"

# 오류 키와 상세 설명을 매핑하는 딕셔너리
ERROR_CRITERIA_MAP = {
    "측면 불안정성": "측면 불안정성: 몸통이 옆으로 기울어지거나 골반이 떨어지는 불안정한 자세.",
    "무릎 모임": "무릎 모임 (Knee Valgus): 앞쪽 다리의 무릎이 발보다 안쪽으로 무너지는 현상.",
    "과도한 무릎 전진": "과도한 무릎 전진: 앞 무릎이 발끝보다 훨씬 앞으로 나아가는 현상.",
    "상체 숙여짐": "상체 숙여짐: 코어 안정성 부족으로 상체가 앞으로 굽혀지는 자세.",
    "부족한 깊이": "부족한 깊이: 근육을 충분히 활성화하지 못하는 얕은 런지 자세.",
    "좁은 스탠스": "좁은 스탠스 (\"외줄타기\"): 양발의 좌우 간격이 거의 없어 지지 기반이 불안정한 자세.",
    "앞발목 가동성 부족": "앞발목 가동성 부족: 최저점에서 앞발목의 배측 굴곡이 충분하지 않은 경우."
}

def save_report(report_path: str, total_reps: int, results: List[Dict]):
    """분석 결과와 전체 평가 기준을 텍스트 파일로 저장합니다."""
    grades = [res['grade'] for res in results]
    grade_counts = GradeCounter(grades)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("실시간 런지 자세 분석 리포트 (TTS 피드백 포함)\n")
        f.write("="*50 + "\n")
        f.write(f"총 런지 횟수: {total_reps}회\n\n")
        
        f.write("등급별 요약:\n")
        for grade in ["A", "B", "C", "D", "F"]:
            count = grade_counts.get(grade, 0)
            f.write(f"- 등급 {grade}: {count}회\n")
        
        f.write("\n" + "="*50 + "\n")
        f.write("반복별 상세 결과:\n")
        for res in results:
            f.write(f"\n--- {res['rep']}회차: 등급 {res['grade']} ---\n")
            if res['errors']:
                f.write("  [수행하지 못한 기준]\n")
                for error_key in sorted(res['errors']):
                    error_description = ERROR_CRITERIA_MAP.get(error_key, "알 수 없는 오류")
                    f.write(f"  - {error_description}\n")
            else:
                f.write("  - 모든 기준을 만족했습니다.\n")

        # 전체 평가 기준 추가
        f.write("\n\n" + "="*50 + "\n")
        f.write("          자세 평가 기준 (참고)\n")
        f.write("="*50 + "\n\n")

        f.write("1. 런지 (Lunge) 종합 기준\n")
        f.write("-------------------------\n")
        f.write("레벨 1: 안전성 (Safety) - 즉시 교정 대상\n")
        f.write("- 측면 불안정성: 어깨/엉덩이 선이 수평에서 ±15도 이상 벗어남\n")
        f.write("- 무릎 모임 (Knee Valgus): 앞 무릎이 엉덩이-발목 선보다 안쪽으로 25px 이상 들어옴\n")
        f.write("- 과도한 무릎 전진: 앞 무릎이 발목보다 35px 이상 앞으로 나감\n\n")
        f.write("레벨 2: 효과성 (Effectiveness) - 주요 교정 대상\n")
        f.write("- 상체 숙여짐: 상체가 수직선 대비 25도 이상 기울어짐 (각도 65도 미만)\n")
        f.write("- 부족한 깊이: 앞/뒤 무릎 각도가 115도를 넘음\n")
        f.write("- 좁은 스탠스: 발목 간격이 어깨너비의 15% 미만\n\n")
        f.write("레벨 3: 최적화 (Optimization) - 미세 조정\n")
        f.write("- 앞발목 가동성 부족: 앞발목 각도가 90도를 넘음 (배측 굴곡 부족)\n\n")

    print(f"리포트가 '{report_path}'에 저장되었습니다.")

# def run_lunge_analysis(duration_seconds=120, stop_callback=None):
def run_lunge_analysis(duration_seconds=120, stop_callback=None, frame_callback=None):
    """실시간 카메라를 통한 런지 분석 함수 (TTS 피드백 포함)
    
    Args:
        duration_seconds (int): 분석할 시간 (초), 기본값 120초 (2분)
        stop_callback (callable): 분석 중지 여부를 확인하는 콜백 함수
    """
    
    # 중지 플래그 초기화
    run_lunge_analysis._stop_analysis = False
    
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
    output_video_path = os.path.join(output_dir, f"lunge_realtime_tts_analysis_{timestamp}.mp4")
    output_report_path = os.path.join(output_dir, f"lunge_realtime_tts_report_{timestamp}.txt")
    
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))
    
    try:
        # TTS 피드백 매니저 초기화
        print("TTS 매니저 초기화 중...")
        tts_manager = UniversalTTS()
        
        # 런지 등급 평가기 초기화
        print("런지 등급 평가기 초기화 중...")
        grader = ComprehensiveLungeGrader()
        
        # 변수 초기화
        counter = 0 
        stage = None
        all_rep_results = []
        current_rep_errors = set()
        last_rep_grade = "N/A"
        current_phase = "READY"
        
        print("초기화 완료!")
        
    except Exception as e:
        print(f"초기화 오류: {str(e)}")
        cap.release()
        out.release()
        return None, None
    
    # 타이머 설정
    start_time = time.time()
    recording_duration = duration_seconds
    
    print(f"런지 분석을 시작합니다. {duration_seconds}초간 카메라가 켜집니다.")
    print("TTS 피드백이 실시간으로 제공됩니다!")
    print("런지 동작을 시작하세요!")
    print("종료하려면 'q'를 누르세요.")
    
    # 시작 안내 메시지
    tts_manager.add_feedback("시작", "encouragement")
    
    while cap.isOpened():
        try:
            ret, frame = cap.read()
            if not ret: 
                print("프레임을 읽을 수 없습니다.")
                break
            
            # 카메라 프레임을 거울모드로 변환 (운동 분석 중에도 거울모드 유지)
            frame = cv2.flip(frame, 1)
            
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
            # 랜드마크가 없어도 기본 UI는 표시
            cv2.rectangle(image, (0, 0), (frame_width, 120), (245, 117, 16), -1)
            cv2.putText(image, f'TIME: {remaining_time:.1f}s', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(image, 'No Person Detected', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
            out.write(image)
            continue
            
        try:
            landmarks = results.pose_landmarks.landmark
            h, w, _ = image.shape
            
            lm_data = {
                'left_shoulder': [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y * h],
                'left_hip': [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y * h],
                'left_knee': [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y * h],
                'left_ankle': [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y * h],
                'left_foot_index': [landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].x * w, landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].y * h],
                'right_shoulder': [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y * h],
                'right_hip': [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y * h],
                'right_knee': [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y * h],
                'right_ankle': [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y * h],
                'right_foot_index': [landmarks[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value].x * w, landmarks[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value].y * h],
            }
            
            # 각도 계산
            angles = {}
            left_knee_angle = calculate_angle(lm_data['left_hip'], lm_data['left_knee'], lm_data['left_ankle'])
            right_knee_angle = calculate_angle(lm_data['right_hip'], lm_data['right_knee'], lm_data['right_ankle'])
            
            # 앞다리 판단 (더 작은 무릎 각도를 가진 다리가 앞다리로 가정)
            front_leg = 'left' if left_knee_angle < right_knee_angle else 'right'
            
            if front_leg == 'left':
                angles['front_knee'] = left_knee_angle
                angles['back_knee'] = right_knee_angle
                # 상체 각도는 수직선 대비
                angles['torso'] = calculate_angle(lm_data['left_hip'], lm_data['left_shoulder'], [lm_data['left_shoulder'][0], lm_data['left_shoulder'][1] - 100])
                angles['front_ankle'] = calculate_angle(lm_data['left_knee'], lm_data['left_ankle'], lm_data['left_foot_index'])
            else:
                angles['front_knee'] = right_knee_angle
                angles['back_knee'] = left_knee_angle
                # 상체 각도는 수직선 대비
                angles['torso'] = calculate_angle(lm_data['right_hip'], lm_data['right_shoulder'], [lm_data['right_shoulder'][0], lm_data['right_shoulder'][1] - 100])
                angles['front_ankle'] = calculate_angle(lm_data['right_knee'], lm_data['right_ankle'], lm_data['right_foot_index'])
            
            # 런지 반복 횟수(카운트) 로직
            # 런지 깊이가 충분할 때 (내려갔을 때)
            if (angles['front_knee'] < 100 or angles['back_knee'] < 100) and (stage == 'up' or stage is None):
                stage = "down"
                current_rep_errors.clear() # 새로운 랩 시작 시 이전 오류 초기화

            # 완전히 일어섰을 때
            if (angles['front_knee'] > 160 and angles['back_knee'] > 160) and stage == 'down':
                stage = "up"
                counter += 1
                # 1회 반복이 끝났으므로 최종 등급을 매기고 결과 저장
                final_grade = grader.get_grade_from_errors(list(current_rep_errors))
                all_rep_results.append({'rep': counter, 'grade': final_grade, 'errors': list(current_rep_errors)})
                last_rep_grade = final_grade
                
                # 런지 완료 시 격려 메시지
                if counter > 0:
                    tts_manager.add_encouragement(counter)
                
            # 현재 단계(Phase) 결정
            if stage is None: # 초기 상태
                current_phase = "READY"
            elif stage == "up":
                current_phase = "UP"
            elif stage == "down":
                current_phase = "DOWN"
            
            # 오류 누적: 내려간 상태('down')일 때만 오류를 기록
            if stage == "down":
                errors_in_frame = grader.evaluate_errors(angles, lm_data, front_leg)
                
                # 현재 등급 계산하여 TTS 매니저에 전달
                current_grade = grader.get_grade_from_errors(list(current_rep_errors))
                tts_manager.current_grade = current_grade
                tts_manager.current_rep_errors = current_rep_errors
                
                # 새로운 오류에 대해서만 TTS 피드백 제공
                for error in errors_in_frame:
                    if error not in current_rep_errors:
                        priority = grader.get_error_priority(error)
                        tts_manager.add_feedback(error, priority)
                
                current_rep_errors.update(errors_in_frame)

        except Exception as e:
            pass

        # 스켈레톤 그리기
        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2), 
                                mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2))
        
        # ------------------ 화면 표시 정보  ------------------
        # 상단 정보 박스
        cv2.rectangle(image, (0,0), (frame_width, 120), (245,117,16), -1)
        
        # 타이머 표시
        cv2.putText(image, f'TIME: {remaining_time:.1f}s', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
        
        # REPS
        cv2.putText(image, 'REPS', (int(frame_width * 0.3), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(image, str(counter), (int(frame_width * 0.3), 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3, cv2.LINE_AA)
        
        # PHASE
        cv2.putText(image, 'PHASE', (int(frame_width * 0.5), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(image, current_phase, (int(frame_width * 0.5), 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3, cv2.LINE_AA)

        # LAST REP GRADE
        cv2.putText(image, 'GRADE', (int(frame_width * 0.7), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(image, last_rep_grade, (int(frame_width * 0.7), 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3, cv2.LINE_AA)
        
        # TTS 상태 표시
        cv2.putText(image, 'TTS: ON', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2, cv2.LINE_AA)
        
        # 하단 안내 메시지
        cv2.rectangle(image, (0, frame_height-50), (frame_width, frame_height), (0,0,0), -1)
        cv2.putText(image, 'Press Q to quit early | TTS Feedback Active', (10, frame_height-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2, cv2.LINE_AA)
        # ----------------------------------------------------
        
        # 텍스트를 그린 후 전체 이미지를 좌우 반전 (거울모드)
        flipped_image = cv2.flip(image, 1)
        
        # GUI로 처리된 프레임 전달 (거울모드로 반전된 프레임)
        if frame_callback:
            frame_callback(flipped_image.copy())  # 반전된 프레임을 GUI로 전달
        
        # 동영상 저장 (원본 방향으로 저장)
        out.write(image)
        
        # macOS에서는 GUI 없이 콘솔 모드로 실행
        print(f"프레임 처리 중... REP: {counter}, PHASE: {current_phase}, GRADE: {last_rep_grade}")

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
                cv2.namedWindow('Real-time Lunge Analysis with TTS', cv2.WINDOW_NORMAL)
                cv2.resizeWindow('Real-time Lunge Analysis with TTS', 1280, 720)
                cv2.imshow('Real-time Lunge Analysis with TTS', image)
                
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
            print(f"런지 분석 진행 중... 시간: {remaining_time:.1f}초, 반복: {counter}")
            _last_status_time = int(time.time())
        
        # 분석 중지 체크 (전역 변수로 제어)
        if hasattr(run_lunge_analysis, '_stop_analysis') and run_lunge_analysis._stop_analysis:
            print("분석이 중지되었습니다.")
            break

        # 분석 중지 체크 (콜백 함수로 제어)
        if stop_callback and stop_callback():
            print("분석이 중지되었습니다.")
            break

    # 마지막 런지가 완료되지 않았다면 처리
    if stage == 'down' and current_rep_errors:
        final_grade = grader.get_grade_from_errors(list(current_rep_errors))
        all_rep_results.append({'rep': counter, 'grade': final_grade, 'errors': list(current_rep_errors)})

    # TTS 매니저 정리
    tts_manager.stop()
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()

    # 결과 저장
    save_report(output_report_path, counter, all_rep_results)
    print(f"분석 영상이 '{output_video_path}'에 저장되었습니다.")
    print(f"분석 리포트가 '{output_report_path}'에 저장되었습니다.")
    print(f"총 {counter}회의 런지를 분석했습니다.")
    print("TTS 피드백이 실시간으로 제공되었습니다.")
    
    # 결과 파일 경로 반환
    return output_video_path, output_report_path

def main():
    """기존 main 함수 (호환성 유지)"""
    video_path, report_path = run_lunge_analysis(120)  # 기본 2분
    if video_path and report_path:
        print(f"분석 완료: {video_path}, {report_path}")
    else:
        print("분석 실패")

if __name__ == "__main__":
    main()