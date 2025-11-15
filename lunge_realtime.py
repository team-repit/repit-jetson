import cv2
import mediapipe as mp
import numpy as np
import os
import sys
import time
import threading
import queue
import subprocess
from typing import List, Dict, Tuple, Optional
from collections import Counter as GradeCounter

from analysis_postprocess import send_record_and_upload
import json

# PyInstaller 환경에서 MediaPipe 모델 경로 설정
def get_mediapipe_path():
    """PyInstaller 환경에서 MediaPipe 경로 가져오기"""
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            mediapipe_path = os.path.join(base_path, 'mediapipe')
            model_path = os.path.join(mediapipe_path, 'modules', 'pose_landmark', 'pose_landmark_cpu.binarypb')
            if os.path.exists(model_path):
                os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'
                return mediapipe_path
    except Exception as e:
        print(f"[WARNING] MediaPipe 경로 설정 실패: {e}")
    
    try:
        import mediapipe as mp
        return os.path.dirname(mp.__file__)
    except:
        return None

def get_output_dir():
    """사용자 쓰기 가능한 output 디렉토리 가져오기"""
    try:
        if getattr(sys, 'frozen', False):
            # PyInstaller 환경: 사용자 Documents 폴더 사용 (쓰기 가능)
            home_dir = os.path.expanduser("~")
            output_dir = os.path.join(home_dir, "Documents", "RePiT", "output")
        else:
            # 개발 환경: 스크립트 위치 기준
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(script_dir, "output")
        
        # 디렉토리 생성 (이미 존재해도 에러 없음)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    except Exception as e:
        print(f"[WARNING] output 디렉토리 생성 실패: {e}")
        # 폴백: 홈 디렉토리
        fallback_dir = os.path.join(os.path.expanduser("~"), "RePiT_output")
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

# MediaPipe 경로 설정
mediapipe_path = get_mediapipe_path()
if mediapipe_path:
    os.environ['GLOG_logtostderr'] = '1'

# Qt 스레딩 지원 추가
try:
    from PySide6.QtCore import QThread, Signal, QObject
    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt5.QtCore import QThread, pyqtSignal as Signal, QObject
        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False

# 🎯 2024년 런지 점수 기준 적당히 완화 업데이트
# 기존: 너무 엄격한 기준으로 D, F 등급이 많이 나옴
# 완화: 적당히 완화하여 현실적이면서도 의미있는 평가 시스템
# 
# 주요 변경사항:
# 1. 점수 기준: 0개=A, 1-2개=B, 3-4개=C, 5-6개=D, 7개+=F
# 2. 측면 불안정성: ±15도 -> ±20도로 완화
# 3. 무릎 모임: 25px -> 30px로 완화
# 4. 과도한 무릎 전진: 35px -> 40px로 완화
# 5. 상체 숙여짐: 65도 -> 60도로 완화
# 6. 부족한 깊이: 115도 -> 120도로 완화
# 7. 좁은 스탠스: 15% -> 20%로 완화
# 8. 앞발목 가동성: 90도 -> 95도로 완화

# MediaPipe Pose 모델 초기화 (PyInstaller 환경 대응)
try:
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    mp_drawing = mp.solutions.drawing_utils
except Exception as e:
    print(f"[ERROR] MediaPipe 초기화 실패: {e}")
    import traceback
    traceback.print_exc()
    mp_pose = None
    pose = None
    mp_drawing = None

class UniversalTTS(QObject if QT_AVAILABLE else object):
    """모든 플랫폼에서 작동하는 TTS 시스템 (Qt 호환)"""
    
    if QT_AVAILABLE:
        feedback_ready = Signal(str, str)  # 메시지, 우선순위
        status_updated = Signal(str)
    
    def __init__(self):
        if QT_AVAILABLE:
            super().__init__()
        self.feedback_queue = queue.Queue()
        self.last_feedback_time = {}  # 각 오류별 마지막 피드백 시간
        self.feedback_cooldown = 3.0  # 같은 오류에 대한 피드백 쿨다운 (초)
        self.min_feedback_interval = 2.0  # 최소 피드백 간격 (초)
        self.last_general_feedback = 0  # 마지막 일반 피드백 시간
        self.running = True
        
        # 플랫폼별 TTS 설정
        self.platform = self._detect_platform()
        self.setup_tts()
        
        # 젯슨에서 TTS 도구 설치 안내
        if self.platform == "Jetson":
            self._check_jetson_tts_tools()
        
        # Qt 환경에서는 피드백 워커를 별도 스레드에서 시작 (시그널 사용 안 함)
        if QT_AVAILABLE:
            import threading
            self.feedback_thread = threading.Thread(target=self._feedback_worker, daemon=True)
            self.feedback_thread.start()
        else:
            # Qt가 없는 환경에서는 일반 스레드 사용
            self.feedback_thread = threading.Thread(target=self._feedback_worker, daemon=True)
            self.feedback_thread.start()
        
        # 피드백 메시지 매핑 (친근하고 구체적인 안내)
        self.feedback_messages = {
            "좌우 흔들림": "몸이 좌우로 흔들리고 있어요. 중심을 잡고 똑바로 서세요.",
            "무릎 모임": "앞 무릎이 안쪽으로 무너지고 있어요. 무릎을 발끝 방향으로 맞춰주세요.",
            "과도한 무릎 전진": "무릎이 너무 앞으로 나갔어요. 무릎을 조금 뒤로 빼세요.",
            "상체 숙여짐": "상체가 너무 앞으로 숙여져 있어요. 가슴을 펴고 일어나세요.",
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
                    # 직접 TTS 실행 (시그널 사용 안 함)
                    self._speak_feedback(message, priority)
                self.feedback_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS 피드백 오류: {e}")
    
    def process_feedback(self, message, priority):
        """Qt 시그널에서 호출되는 메서드 - 메인 스레드에서 실행됨"""
        self._speak_feedback(message, priority)
    
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
        """Linux/젯슨에서 MP3 파일 재생 - 젯슨 최적화"""
        # 젯슨에서 안정적인 오디오 재생을 위한 순서
        players = [
            # 젯슨에서 가장 안정적인 방법들
            ('aplay (WAV 변환)', self._convert_and_play_wav),
            ('mpg123', ['mpg123', '-q', mp3_file]),  # -q 옵션으로 조용한 실행
            ('ffplay', ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', mp3_file]),
            ('mpv', ['mpv', '--no-video', '--no-terminal', mp3_file]),
            ('cvlc', ['cvlc', '--intf', 'dummy', '--play-and-exit', mp3_file])
        ]
        
        for player_name, cmd in players:
            try:
                if callable(cmd):
                    # WAV 변환 함수인 경우
                    cmd(mp3_file)
                else:
                    # 일반 명령어인 경우
                    result = subprocess.run(cmd, check=True, 
                                          stdout=subprocess.DEVNULL, 
                                          stderr=subprocess.DEVNULL,
                                          timeout=10)  # 10초 타임아웃
                print(f"MP3 재생 성공: {player_name} 사용")
                return
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                print(f"{player_name} 실패: {e}")
                continue
        
        print("모든 MP3 재생 방법이 실패했습니다. 백업 TTS를 사용합니다.")
        raise Exception("Linux에서 MP3 재생을 위한 도구가 없습니다")
    
    def _convert_and_play_wav(self, mp3_file: str):
        """MP3를 WAV로 변환 후 aplay로 재생 - 젯슨에서 가장 안정적"""
        try:
            import pydub
            audio = pydub.AudioSegment.from_mp3(mp3_file)
            wav_file = mp3_file.replace('.mp3', '.wav')
            audio.export(wav_file, format="wav")
            
            # aplay로 재생 (젯슨에서 가장 안정적)
            subprocess.run(['aplay', wav_file], check=True, timeout=10)
            os.remove(wav_file)
            print("MP3를 WAV로 변환하여 aplay로 재생")
        except ImportError:
            print("pydub가 설치되지 않아 MP3를 WAV로 변환할 수 없습니다")
            raise
        except Exception as e:
            print(f"WAV 변환 및 재생 실패: {e}")
            raise
    
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
        
        # 피드백 메시지 가져오기 (친근한 메시지 우선 사용)
        message = self.feedback_messages.get(error_type, "")
        
        # 이상한 메시지 방지 (error_type이 한글이 아닌 경우)
        if not message:
            # 기본적인 친근한 메시지로 대체
            message = "운동 자세를 잡아주세요."
        
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
        if self.feedback_thread and not QT_AVAILABLE:
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
            print("sudo apt-get install ffmpeg")                      # ffplay 지원
            print("sudo apt-get install alsa-utils")                  # aplay 지원
            
            print("\n📦 Python 패키지:")
            print("pip install gtts pydub numpy")
            
            print("\n🔧 젯슨 오디오 설정 확인:")
            print("aplay -l  # 오디오 장치 확인")
            print("speaker-test -t wav  # 스피커 테스트")
        
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
        
        # 레벨 1: 안전성 (Safety) - 즉시 교정 대상 (적당히 완화된 기준)
        # 1-1. 측면 불안정성 (기존 ±15도 -> ±20도로 완화)
        shoulder_angle_with_horizontal = calculate_angle(landmarks['right_shoulder'], landmarks['left_shoulder'], [landmarks['left_shoulder'][0] + 100, landmarks['left_shoulder'][1]])
        hip_angle_with_horizontal = calculate_angle(landmarks['right_hip'], landmarks['left_hip'], [landmarks['left_hip'][0] + 100, landmarks['left_hip'][1]])
        if not (160 <= shoulder_angle_with_horizontal <= 200) or not (160 <= hip_angle_with_horizontal <= 200):
            errors.append("좌우 흔들림")

        # 1-2. 무릎 모임 (기존 25px -> 30px로 완화)
        if front_leg == 'left':
            if landmarks['left_knee'][0] < landmarks['left_hip'][0] - 30:
                 errors.append("무릎 모임")
        else:
            if landmarks['right_knee'][0] > landmarks['right_hip'][0] + 30:
                 errors.append("무릎 모임")

        # 1-3. 과도한 무릎 전진 (기존 35px -> 40px로 완화)
        if front_leg == 'left':
            if landmarks['left_knee'][0] > landmarks['left_ankle'][0] + 40:
                errors.append("과도한 무릎 전진")
        else: # front_leg == 'right'
            if landmarks['right_knee'][0] < landmarks['right_ankle'][0] - 40:
                errors.append("과도한 무릎 전진")

        # 레벨 2: 효과성 (Effectiveness) - 주요 교정 대상 (적당히 완화된 기준)
        # 2-1. 상체 숙여짐 (기존 65도 -> 60도로 완화)
        if 'torso' in angles and angles['torso'] < 60: 
            errors.append("상체 숙여짐")

        # 2-2. 부족한 깊이 (기존 115도 -> 120도로 완화)
        if 'front_knee' in angles and angles['front_knee'] > 120:
            errors.append("부족한 깊이")
        if 'back_knee' in angles and angles['back_knee'] > 120:
            errors.append("부족한 깊이")

        # 2-3. 좁은 스탠스 (기존 15% -> 20%로 완화)
        ankle_dist = abs(landmarks['left_ankle'][0] - landmarks['right_ankle'][0])
        shoulder_dist = abs(landmarks['left_shoulder'][0] - landmarks['right_shoulder'][0])
        if shoulder_dist > 0 and ankle_dist < shoulder_dist * 0.2:
            errors.append("좁은 스탠스")

        # 레벨 3: 최적화 (Optimization) - 미세 조정 (적당히 완화된 기준)
        # 3-1. 앞발목 가동성 부족 (기존 90도 -> 95도로 완화)
        if 'front_ankle' in angles and angles['front_ankle'] > 95:
            errors.append("앞발목 가동성 부족")

        return errors

    def get_grade_from_errors(self, errors: List[str]) -> str:
        """오류 개수에 따라 등급을 반환합니다. (적당히 완화된 기준)"""
        num_errors = len(set(errors))
        
        # 점수 기준 적당히 완화 (너무 후하지도, 너무 엄격하지도 않은 균형)
        # 기존: 0개=A, 1개=B, 2개=C, 3개=D, 4개+=F
        # 조정: 0개=A, 1-2개=B, 3-4개=C, 5-6개=D, 7개+=F
        if num_errors == 0: return "A"      # 완벽
        elif num_errors <= 2: return "B"    # 1-2개 오류: B급 (기존 B, C급)
        elif num_errors <= 4: return "C"    # 3-4개 오류: C급 (기존 D급)
        elif num_errors <= 6: return "D"    # 5-6개 오류: D급 (기존 F급)
        else: return "F"                    # 7개 이상: F급 (심각한 경우)

    def get_body_part_scores(self, errors: List[str]) -> List[Dict[str, str]]:
        """부위별 점수를 반환합니다."""
        body_part_scores = []
        
        # 런지 관련 부위별 오류 매핑
        body_part_error_mapping = {
            "무릎": ["무릎 모임", "과도한 무릎 전진", "부족한 깊이"],
            "상체": ["상체 숙여짐"],
            "골반": ["좌우 흔들림", "좁은 스탠스"],
            "발목": ["앞발목 가동성 부족"]
        }
        
        # 각 부위별로 점수 계산
        for body_part, related_errors in body_part_error_mapping.items():
            # 해당 부위와 관련된 오류 개수 계산
            part_errors = [error for error in errors if error in related_errors]
            num_part_errors = len(part_errors)
            
            # 부위별 점수 계산 (전체 점수와 동일한 기준 적용)
            if num_part_errors == 0:
                detail_score = "A"
            elif num_part_errors <= 2:
                detail_score = "B"
            elif num_part_errors <= 4:
                detail_score = "C"
            elif num_part_errors <= 6:
                detail_score = "D"
            else:
                detail_score = "F"
            
            body_part_scores.append({
                "body_part": body_part,
                "detail_score": detail_score
            })
        
        return body_part_scores

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
    error_counts = GradeCounter()
    for res in results:
        error_counts.update(res['errors'])
    top_errors = error_counts.most_common(3)
    dominant_grade = grade_counts.most_common(1)[0][0] if grade_counts else "F"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("[실시간 런지 자세 분석 리포트 | TTS 피드백 포함]\n")
        f.write(f"총 런지 횟수: {total_reps}회\n\n")
        
        f.write("[등급별 요약]\n")
        for grade in ["A", "B", "C", "D", "F"]:
            count = grade_counts.get(grade, 0)
            f.write(f"- 등급 {grade}: {count}회\n")

        f.write("\n[핵심 요약]\n")
        if total_reps > 0:
            f.write(f"- 가장 자주 기록된 등급: {dominant_grade}\n")
        else:
            f.write("- 측정된 런지가 없어 기본 가이드를 제공합니다.\n")
        if top_errors:
            f.write("- 자주 나온 교정 포인트:\n")
            for name, count in top_errors:
                desc = ERROR_CRITERIA_MAP.get(name, name)
                f.write(f"  · {desc} ({count}회)\n")
        else:
            f.write("- 눈에 띄는 오류가 기록되지 않았습니다.\n")
        
        f.write("\n[반복별 상세 결과]\n")
        for res in results:
            f.write(f"\n({res['rep']}회차) 등급 {res['grade']}\n")
            if res['errors']:
                for error_key in sorted(res['errors']):
                    error_description = ERROR_CRITERIA_MAP.get(error_key, "알 수 없는 오류")
                    f.write(f"  - {error_description}\n")
            else:
                f.write("  - 모든 기준을 만족했습니다.\n")

        f.write("\n[자세 평가 기준 요약]\n")
        f.write("레벨 1 - 안전성\n")
        f.write("  · 측면 불안정성: 어깨/엉덩이 선이 수평에서 ±20도 이상 벗어남\n")
        f.write("  · 무릎 모임: 앞 무릎이 엉덩이-발목 선보다 30px 이상 안쪽\n")
        f.write("  · 과도한 무릎 전진: 앞 무릎이 발목보다 40px 이상 전진\n")
        f.write("레벨 2 - 효과성\n")
        f.write("  · 상체 숙여짐: 상체 각도 60도 미만\n")
        f.write("  · 부족한 깊이: 앞/뒤 무릎 각도 120도 초과\n")
        f.write("  · 좁은 스탠스: 발목 간격이 어깨너비의 20% 미만\n")
        f.write("레벨 3 - 최적화\n")
        f.write("  · 앞발목 가동성 부족: 앞발목 각도 95도 초과\n")

    print(f"리포트가 '{report_path}'에 저장되었습니다.")

def save_json_report(json_path: str, total_reps: int, results: List[Dict], total_duration: int):
    """분석 결과를 JSON 파일로 저장합니다."""
    # 전체 점수 계산 (가장 많이 나온 등급을 전체 점수로 사용)
    if results:
        grades = [res['grade'] for res in results]
        grade_counts = GradeCounter(grades)
        most_common_grade = grade_counts.most_common(1)[0][0]
    else:
        most_common_grade = "F"
    
    # 부위별 점수 계산 (모든 반복의 평균)
    grader = ComprehensiveLungeGrader()
    all_body_part_scores = []
    
    for res in results:
        body_part_scores = grader.get_body_part_scores(res['errors'])
        all_body_part_scores.extend(body_part_scores)
    
    # 부위별 평균 점수 계산
    body_part_grade_counts = {}
    for score in all_body_part_scores:
        body_part = score['body_part']
        detail_score = score['detail_score']
        if body_part not in body_part_grade_counts:
            body_part_grade_counts[body_part] = []
        body_part_grade_counts[body_part].append(detail_score)
    
    final_body_part_scores = []
    for body_part, scores in body_part_grade_counts.items():
        # 점수를 숫자로 변환하여 평균 계산
        score_values = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'F': 1}
        numeric_scores = [score_values.get(score, 1) for score in scores]
        avg_score = sum(numeric_scores) / len(numeric_scores)
        
        # 평균을 다시 등급으로 변환
        if avg_score >= 4.5:
            final_grade = "A"
        elif avg_score >= 3.5:
            final_grade = "B"
        elif avg_score >= 2.5:
            final_grade = "C"
        elif avg_score >= 1.5:
            final_grade = "D"
        else:
            final_grade = "F"
        
        final_body_part_scores.append({
            "body_part": body_part,
            "detail_score": final_grade
        })

    required_body_parts = ["무릎", "상체", "골반", "발목"]
    reordered_scores = []
    existing = {score["body_part"]: score for score in final_body_part_scores}
    for part in required_body_parts:
        reordered_scores.append(existing.get(part, {"body_part": part, "detail_score": "F"}))
    final_body_part_scores = reordered_scores
    
    # 리포트 텍스트 생성 - 리포트 파일의 전체 내용을 읽어서 포함
    analysis_text = ""
    try:
        # 리포트 파일 경로 생성 (json_path와 같은 디렉토리의 .txt 파일)
        report_dir = os.path.dirname(json_path)
        # JSON 파일명에서 analysis를 report로 변경하고 확장자를 txt로 변경
        report_filename = os.path.basename(json_path).replace('analysis', 'report').replace('.json', '.txt')
        report_path = os.path.join(report_dir, report_filename)
        
        print(f"[DEBUG] 리포트 파일 경로: {report_path}")
        print(f"[DEBUG] 리포트 파일 존재 여부: {os.path.exists(report_path)}")
        
        # 리포트 파일이 존재하면 전체 내용을 읽어옴
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                analysis_text = f.read()
            print(f"[DEBUG] 리포트 파일 내용 길이: {len(analysis_text)} 문자")
            print(f"[DEBUG] 리포트 파일 내용 미리보기: {analysis_text[:200]}...")
            print(f"리포트 파일 내용을 analysis_text에 포함: {report_path}")
        else:
            print(f"리포트 파일을 찾을 수 없음: {report_path}")
            # 리포트 파일이 없으면 기본 정보 생성
            analysis_text = f"실시간 런지 자세 분석 리포트 (TTS 피드백 포함)\n"
            analysis_text += f"총 런지 횟수: {total_reps}회\n\n"
            
            if results:
                analysis_text += "반복별 상세 결과:\n"
                for res in results:
                    analysis_text += f"\n--- {res['rep']}회차: 등급 {res['grade']} ---\n"
                    if res['errors']:
                        analysis_text += "  [수행하지 못한 기준]\n"
                        for error_key in sorted(res['errors']):
                            error_description = ERROR_CRITERIA_MAP.get(error_key, "알 수 없는 오류")
                            analysis_text += f"  - {error_description}\n"
                    else:
                        analysis_text += "  - 모든 기준을 만족했습니다.\n"
    except Exception as e:
        print(f"리포트 파일 읽기 오류: {e}")
        import traceback
        traceback.print_exc()
        # 오류 발생 시 기본 정보 생성
        analysis_text = f"실시간 런지 자세 분석 리포트 (TTS 피드백 포함)\n"
        analysis_text += f"총 런지 횟수: {total_reps}회\n\n"
        analysis_text += f"리포트 파일 읽기 오류: {str(e)}"
    
    # JSON 데이터 구성
    json_data = {
        "pose_type": "LUNGE",
        "duration": total_duration,
        "reps": total_reps,
        "total_score": most_common_grade,
        "video_path": None,  # 영상 경로는 null로 설정
        "analysis_text": analysis_text,
        "score_details": final_body_part_scores
    }
    
    # JSON 파일 저장
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"JSON 리포트가 '{json_path}'에 저장되었습니다.")
    return json_data

# def run_lunge_analysis(duration_seconds=120, stop_callback=None):
def run_lunge_analysis(duration_seconds=120, stop_callback=None, frame_callback=None, is_gui_mode=False, api_client=None):
    """실시간 카메라를 통한 런지 분석 함수 (TTS 피드백 포함)
    
    Args:
        duration_seconds (int): 분석할 시간 (초), 기본값 120초 (2분)
        stop_callback (callable): 분석 중지 여부를 확인하는 콜백 함수
        frame_callback (callable): 프레임 처리 콜백 함수
        is_gui_mode (bool): GUI 모드 여부 (PySide6 환경에서는 True)
        api_client: API 클라이언트 (선택사항)
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
    
    # 카메라 설정 (젯슨 딜레이 최소화)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 원래 해상도 유지
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  # 원래 해상도 유지
    cap.set(cv2.CAP_PROP_FPS, 15)            # 15 FPS로 설정
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)      # 버퍼 크기 최소화
    
    # 영상 저장을 위한 설정
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 30.0
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    # output 디렉토리 가져오기 (사용자 쓰기 가능한 위치)
    output_dir = get_output_dir()
    print(f"output 디렉토리: {output_dir}")
    
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
    print("운동 자세를 잡아주세요!")
    print("종료하려면 'q'를 누르세요.")
    
    # 시작 안내 메시지
    tts_manager.add_feedback("운동 자세를 잡아주세요!", "encouragement")
    
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
        
        # OpenCV 창 표시 (GUI 모드가 아닐 때만)
        if not is_gui_mode:
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
            # GUI 모드에서는 OpenCV 창을 생성하지 않음 (PySide6와 충돌 방지)
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
    
    # JSON 리포트 저장
    output_json_path = os.path.join(output_dir, f"lunge_realtime_tts_analysis_{timestamp}.json")
    json_data = save_json_report(output_json_path, counter, all_rep_results, duration_seconds)
    
    # API로 데이터 전송 (API 클라이언트가 제공된 경우)
    api_result = send_record_and_upload(api_client, json_data, output_video_path, "lunge")
    
    print(f"분석 영상이 '{output_video_path}'에 저장되었습니다.")
    print(f"분석 리포트가 '{output_report_path}'에 저장되었습니다.")
    print(f"JSON 리포트가 '{output_json_path}'에 저장되었습니다.")
    print(f"총 {counter}회의 런지를 분석했습니다.")
    print("TTS 피드백이 실시간으로 제공되었습니다.")
    
    # 결과 파일 경로 반환 (JSON 데이터와 API 결과 포함)
    return output_video_path, output_report_path, output_json_path, json_data, api_result

def main():
    """기존 main 함수 (호환성 유지)"""
    result = run_lunge_analysis(120)  # 기본 2분
    if result and len(result) >= 2:
        video_path, report_path = result[0], result[1]
        print(f"분석 완료: {video_path}, {report_path}")
    else:
        print("분석 실패")

if __name__ == "__main__":
    main()