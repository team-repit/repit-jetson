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
            "허리 말림": "허리를 펴세요. 엉덩이가 안으로 말리지 않도록 주의하세요.",
            "무릎 모임": "무릎이 발끝 방향을 향하도록 하세요. 안쪽으로 무너지지 마세요.",
            "굿모닝 스쿼트": "상체를 일으키세요. 엉덩이만 먼저 올라가지 않도록 하세요.",
            "상체 숙임": "가슴을 펴고 상체를 일으키세요.",
            "뒤꿈치 들림": "뒤꿈치를 바닥에 붙이세요. 무게중심이 앞으로 쏠리지 않도록 하세요.",
            "골반 치우침": "골반을 중앙에 유지하세요. 좌우로 치우치지 마세요.",
            "깊이 부족": "더 깊게 앉으세요. 허벅지가 지면과 평행이 될 때까지.",
            "발목 가동성 부족": "발목을 더 굽혀보세요. 가동성을 높이세요."
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

    def _speak_jetson_espeak(self, message: str, priority: str):
        """젯슨 espeak TTS (안정적이고 빠름)"""
        try:
            # espeak TTS 시도
            rate = 150 if priority == "urgent" else 120
            subprocess.run(['espeak', '-s', str(rate), message], check=True)
            print("젯슨 espeak TTS 사용됨 (안정적)")
        except Exception as e:
            print(f"espeak TTS 실패: {e}")
            # Riva TTS 시도
            try:
                self._speak_jetson_riva(message, priority)
            except:
                # 기본 젯슨 TTS로 폴백
                self._speak_jetson(message, priority)

    def _speak_jetson_riva(self, message: str, priority: str):
        """젯슨 Riva TTS (최고 성능)"""
        try:
            # Riva TTS 시도
            self._speak_riva_tts(message, priority)
            print("젯슨 Riva TTS 사용됨")
        except Exception as e:
            print(f"Riva TTS 실패: {e}")
            # 기존 젯슨 TTS로 폴백
            self._speak_jetson(message, priority)

    def _speak_riva_tts(self, message: str, priority: str):
        """NVIDIA Riva TTS 사용"""
        try:
            # Riva 클라이언트 임포트 시도
            from nvidia.riva.client import RivaClient

            # Riva 서버에 연결 (기본 포트 8000)
            client = RivaClient("localhost:8000")

            # TTS 설정
            sample_rate = 22050
            language_code = "ko-KR"  # 한국어

            # 우선순위에 따른 음성 속도 조절
            if priority == "urgent":
                speed = 1.2  # 빠르게
            else:
                speed = 1.0  # 보통 속도

            # TTS 생성
            audio = client.tts(
                text=message,
                language_code=language_code,
                sample_rate_hz=sample_rate,
                voice_name="ljspeech",  # 기본 음성
                speed=speed
            )

            # 오디오 재생
            self._play_audio_data(audio, sample_rate)

        except ImportError:
            print("Riva 클라이언트가 설치되지 않았습니다.")
            print("설치 방법: pip install nvidia-riva-client")
            raise Exception("Riva TTS를 사용할 수 없습니다")
        except Exception as e:
            print(f"Riva TTS 실행 오류: {e}")
            raise

    def _play_audio_data(self, audio_data, sample_rate):
        """오디오 데이터를 재생"""
        try:
            # numpy 배열로 변환
            import numpy as np
            audio_np = np.frombuffer(audio_data, dtype=np.int16)

            # WAV 파일로 저장 후 재생
            import wave
            wav_file = "temp_riva_speech.wav"

            with wave.open(wav_file, 'wb') as wf:
                wf.setnchannels(1)  # 모노
                wf.setsampwidth(2)  # 16비트
                wf.setframerate(sample_rate)
                wf.writeframes(audio_np.tobytes())

            # aplay로 재생
            subprocess.run(['aplay', wav_file], check=True)
            os.remove(wav_file)

        except Exception as e:
            print(f"오디오 재생 오류: {e}")
            raise

    def _speak_jetson(self, message: str, priority: str):
        """젯슨 전용 TTS (Festival 우선, Pico 백업)"""
        try:
            # Festival TTS 시도
            rate = 0.8 if priority == "urgent" else 1.0
            subprocess.run(['festival', '--tts', f'(SayText "{message}")'], check=True)
            print("젯슨 TTS (Festival) 사용됨")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Festival TTS 실패, Pico TTS 시도")
            try:
                # Pico TTS 시도
                subprocess.run(['pico2wave', '-w', 'temp_speech.wav', message], check=True)
                subprocess.run(['aplay', 'temp_speech.wav'], check=True)
                os.remove('temp_speech.wav')
                print("젯슨 TTS (Pico) 사용됨")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Pico TTS도 실패, Flite TTS 시도")
                try:
                    # Flite TTS 시도
                    subprocess.run(['flite', '-t', message], check=True)
                    print("젯슨 TTS (Flite) 사용됨")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("모든 젯슨 TTS 실패")
                    raise Exception("젯슨 TTS를 사용할 수 없습니다")

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

    def _speak_macos(self, message: str, priority: str):
        """macOS say 명령어"""
        rate = 200 if priority == "urgent" else 150
        subprocess.run(['say', '-r', str(rate), message], check=True)

    def _speak_pyttsx3(self, message: str, priority: str):
        """pyttsx3 (Windows/Linux)"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            rate = 200 if priority == "urgent" else 150
            engine.setProperty('rate', rate)
            engine.say(message)
            engine.runAndWait()
        except ImportError:
            print("pyttsx3가 설치되지 않았습니다. 백업 TTS를 사용합니다.")
            self._speak_backup(message)

    def _speak_espeak(self, message: str, priority: str):
        """Linux espeak"""
        rate = 200 if priority == "urgent" else 150
        subprocess.run(['espeak', '-s', str(rate), message], check=True)

    def _speak_backup(self, message: str):
        """플랫폼별 백업 TTS"""
        try:
            if self.platform == "Jetson":
                # 젯슨 백업 TTS
                self._speak_jetson_backup(message)
            elif self.backup_tts == "native_say":
                self._speak_macos(message, "normal")
            elif self.backup_tts == "pyttsx3":
                self._speak_pyttsx3(message, "normal")
            elif self.backup_tts == "festival":
                self._speak_festival(message, "normal")
            elif self.backup_tts == "espeak":
                self._speak_espeak(message, "normal")
            else:
                self._speak_pyttsx3(message, "normal")
            print(f"백업 TTS ({self.backup_tts}) 사용됨")

        except Exception as e:
            print(f"백업 TTS도 실패: {e}")
            print("음성 피드백을 제공할 수 없습니다.")

    def _speak_jetson_backup(self, message: str):
        """젯슨 백업 TTS (Festival → espeak 순서로 시도)"""
        try:
            # Festival TTS (한국어 품질 양호)
            subprocess.run(['festival', '--tts', f'(SayText "{message}")'], check=True)
            print("젯슨 백업 TTS (Festival) 사용됨")
        except:
            try:
                # Pico TTS
                subprocess.run(['pico2wave', '-w', 'temp_speech.wav', message], check=True)
                subprocess.run(['aplay', 'temp_speech.wav'], check=True)
                os.remove('temp_speech.wav')
                print("젯슨 백업 TTS (Pico) 사용됨")
            except:
                try:
                    # Flite TTS
                    subprocess.run(['flite', '-t', message], check=True)
                    print("젯슨 백업 TTS (Flite) 사용됨")
                except:
                    # espeak TTS (최종 백업)
                    subprocess.run(['espeak', '-s', '120', message], check=True)
                    print("젯슨 백업 TTS (espeak) 사용됨")

    def _speak_festival(self, message: str, priority: str):
        """Festival TTS (Linux/젯슨)"""
        rate = 0.8 if priority == "urgent" else 1.0
        subprocess.run(['festival', '--tts', f'(SayText "{message}")'], check=True)

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

    def get_smart_feedback_summary(self, errors: List[str]) -> str:
        """지능적 피드백 요약 메시지 생성"""
        if not errors:
            return "완벽한 자세입니다!"

        if len(errors) == 1:
            return self.feedback_messages.get(errors[0], f"{errors[0]}을 수정하세요.")

        # 2개 이상일 때는 우선순위 기반 요약
        priority_errors = self.get_priority_order(errors)
        if len(priority_errors) >= 2:
            main_error = priority_errors[0]
            return f"가장 중요한 것은 {main_error}입니다. {self.feedback_messages.get(main_error, '')}"

        return "자세를 점검해보세요."

    def get_priority_order(self, errors: List[str]) -> List[str]:
        """오류를 우선순위 순서로 정렬 (안전성 > 효과성 > 최적화)"""
        priority_order = [
            "허리 말림",  # 🚨 안전성 최우선
            "무릎 모임",  # 🚨 안전성 최우선
            "굿모닝 스쿼트",  # 🚨 안전성 최우선
            "상체 숙임",  # ⚠️ 효과성
            "뒤꿈치 들림",  # ⚠️ 효과성
            "골반 치우침",  # ⚠️ 효과성
            "깊이 부족",  # 💡 최적화
            "발목 가동성 부족"  # 💡 최적화
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
        print("\n" + "=" * 60)
        print("젯슨 TTS 도구 설치 확인 중...")
        print("=" * 60)

        tools_status = {}

        # Google TTS 확인 (한국어 품질 최고)
        try:
            import gtts
            tools_status['Google TTS (gTTS)'] = "✅ 설치됨 (한국어 품질 최고)"
        except ImportError:
            tools_status['Google TTS (gTTS)'] = "❌ 설치 필요 (1순위)"

        # Festival TTS 확인 (한국어 품질 양호)
        try:
            subprocess.run(['festival', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            tools_status['Festival TTS'] = "✅ 설치됨 (2순위)"
        except:
            tools_status['Festival TTS'] = "❌ 설치 필요"

        # Pico TTS 확인
        try:
            subprocess.run(['pico2wave', '--help'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            tools_status['Pico TTS'] = "✅ 설치됨"
        except:
            tools_status['Pico TTS'] = "❌ 설치 필요"

        # Flite TTS 확인
        try:
            subprocess.run(['flite', '--help'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            tools_status['Flite TTS'] = "✅ 설치됨"
        except:
            tools_status['Flite TTS'] = "❌ 설치 필요"

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
            print("sudo apt-get install festival festvox-kallpc16k")  # Festival TTS
            print("sudo apt-get install pico-utils")  # Pico TTS
            print("sudo apt-get install flite")  # Flite TTS
            print("sudo apt-get install espeak")  # espeak TTS
            print("sudo apt-get install mpg123")  # MP3 재생

            print("\n📦 Python 패키지:")
            print("pip install gtts pydub numpy")

        print("=" * 60 + "\n")

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

class ComprehensiveSquatGrader:
    """
    'AI 자세 교정을 위한 종합 평가 기준'을 기반으로 한 새로운 평가 클래스.
    계층적 피드백 구조(안전성 > 효과성 > 최적화)를 따릅니다.
    """
    def __init__(self):
        pass

    def evaluate_errors(self, landmarks: dict, angles: dict, phase: str, rep_start_hip_y: float) -> List[str]:
        """
        자세를 평가하고 발생한 모든 오류 목록을 계층적으로 반환합니다.
        """
        errors = []

        # 레벨 1: 안전성 (Safety) - 즉시 교정 대상
        if phase in ["DESCEND", "BOTTOM", "ASCEND"]:
            # 1-1. 허리 말림 (Butt Wink)
            if 'hip' in angles and angles['hip'] < 65:
                errors.append("허리 말림")

            # 1-2. 무릎 모임 (Knee Valgus)
            lk_pos, rk_pos = landmarks.get('left_knee'), landmarks.get('right_knee')
            la_pos, ra_pos = landmarks.get('left_ankle'), landmarks.get('right_ankle')
            if all([lk_pos, rk_pos, la_pos, ra_pos]):
                knee_dist = abs(lk_pos[0] - rk_pos[0])
                ankle_dist = abs(la_pos[0] - ra_pos[0])
                if ankle_dist > 0 and knee_dist < ankle_dist * 0.85:
                    errors.append("무릎 모임")

            # 1-3. "굿모닝" 스쿼트
            if phase == "ASCEND":
                hip_y = (landmarks['left_hip'][1] + landmarks['right_hip'][1]) / 2
                shoulder_y = (landmarks['left_shoulder'][1] + landmarks['right_shoulder'][1]) / 2
                # 엉덩이가 어깨보다 유의미하게 먼저 올라가는지 확인
                if hip_y < (rep_start_hip_y * 0.9) and shoulder_y > (rep_start_hip_y * 0.95):
                    errors.append("굿모닝 스쿼트")

        # 레벨 2: 효과성 (Effectiveness) - 주요 교정 대상
        if phase in ["DESCEND", "BOTTOM"]:
            # 2-1. 과도한 상체 숙임 (Chest Drop)
            if 'torso' in angles and angles['torso'] < 45 and "허리 말림" not in errors:
                errors.append("상체 숙임")

            # 2-2. 뒤꿈치 들림 (Heel Lift)
            left_heel_vis = landmarks.get('left_heel_visibility', 1.0)
            right_heel_vis = landmarks.get('right_heel_visibility', 1.0)
            if left_heel_vis < 0.7 or right_heel_vis < 0.7:
                errors.append("뒤꿈치 들림")

            # 2-3. 골반 치우침 (Pelvic Shift)
            hip_center_x = (landmarks['left_hip'][0] + landmarks['right_hip'][0]) / 2
            ankle_center_x = (landmarks['left_ankle'][0] + landmarks['right_ankle'][0]) / 2
            shoulder_width = abs(landmarks['left_shoulder'][0] - landmarks['right_shoulder'][0])
            if shoulder_width > 0 and abs(hip_center_x - ankle_center_x) > shoulder_width * 0.15:
                errors.append("골반 치우침")

        # 레벨 3: 최적화 (Optimization) - 미세 조정
        if phase == "BOTTOM":
            # 3-1. 깊이 부족 (Insufficient Depth)
            if 'knee' in angles and angles['knee'] > 120:
                errors.append("깊이 부족")

            # 3-2. 발목 가동성 부족 (Ankle Mobility)
            if 'ankle' in angles and angles['ankle'] > 80:  # 배굴곡 각도가 충분하지 않음
                errors.append("발목 가동성 부족")

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
        safety_errors = ["허리 말림", "무릎 모임", "굿모닝 스쿼트"]
        if error in safety_errors:
            return "urgent"
        return "normal"

# 오류 키와 상세 설명을 매핑하는 딕셔너리
ERROR_CRITERIA_MAP = {
    "허리 말림": "허리 말림 (Butt Wink): 하강 최저점에서 엉덩이가 안으로 말리며 허리의 중립이 무너지는 현상.",
    "무릎 모임": "무릎 모임 (Knee Valgus): 하강 또는 상승 시 무릎이 발보다 안쪽으로 무너지는 현상.",
    "굿모닝 스쿼트": '"굿모닝" 스쿼트: 상승 시 엉덩이가 상체보다 현저히 빠르게 올라와 허리에 과부하가 걸리는 현상.',
    "상체 숙임": "과도한 상체 숙임 (Chest Drop): 힙 힌지 범위를 넘어 상체가 과도하게 앞으로 쏠리는 자세.",
    "뒤꿈치 들림": "뒤꿈치 들림 (Heel Lift): 무게 중심이 앞으로 쏠려 뒤꿈치가 바닥에서 뜨는 현상.",
    "골반 치우침": "골반 치우침 (Pelvic Shift): 하강 또는 상승 시 골반이 좌우 한쪽으로 쏠리는 현상.",
    "깊이 부족": "깊이 부족 (Insufficient Depth): 허벅지가 지면과 평행이 되는 지점까지 충분히 하강하지 못하는 경우.",
    "발목 가동성 부족": "발목 가동성 부족 (Ankle Mobility): 스쿼트 최저점에서 발목 각도(배굴곡)가 충분하지 않은 경우."
}

def save_report(report_path: str, total_reps: int, results: List[Dict]):
    """분석 결과와 전체 평가 기준을 텍스트 파일로 저장합니다."""
    grades = [res['grade'] for res in results]
    grade_counts = GradeCounter(grades)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("실시간 스쿼트 자세 분석 리포트 (TTS 피드백 포함)\n")
        f.write("=" * 50 + "\n")
        f.write(f"총 스쿼트 횟수: {total_reps}회\n\n")

        f.write("등급별 요약:\n")
        for grade in ["A", "B", "C", "D", "F"]:
            count = grade_counts.get(grade, 0)
            f.write(f"- 등급 {grade}: {count}회\n")

        f.write("\n" + "=" * 50 + "\n")
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
        f.write("\n\n" + "=" * 50 + "\n")
        f.write("          자세 평가 기준 (참고)\n")
        f.write("=" * 50 + "\n\n")

        f.write("1. 스쿼트 (Squat) 종합 기준\n")
        f.write("-------------------------\n")
        f.write("레벨 1: 안전성 (Safety) - 즉시 교정 대상\n")
        f.write("- 허리 말림 (Butt Wink): 하강 최저점에서 엉덩이가 안으로 말리며 허리의 중립이 무너지는 현상.\n")
        f.write("- 무릎 모임 (Knee Valgus): 하강 또는 상승 시 무릎이 발보다 안쪽으로 무너지는 현상.\n")
        f.write("- \"굿모닝\" 스쿼트: 상승 시 엉덩이가 상체보다 현저히 빠르게 올라와 허리에 과부하가 걸리는 현상.\n\n")
        f.write("레벨 2: 효과성 (Effectiveness) - 주요 교정 대상\n")
        f.write("- 과도한 상체 숙임 (Chest Drop): 힙 힌지 범위를 넘어 상체가 과도하게 앞으로 쏠리는 자세.\n")
        f.write("- 뒤꿈치 들림 (Heel Lift): 무게 중심이 앞으로 쏠려 뒤꿈치가 바닥에서 뜨는 현상.\n")
        f.write("- 골반 치우침 (Pelvic Shift): 하강 또는 상승 시 골반이 좌우 한쪽으로 쏠리는 현상.\n\n")
        f.write("레벨 3: 최적화 (Optimization) - 미세 조정\n")
        f.write("- 깊이 부족 (Insufficient Depth): 허벅지가 지면과 평행이 되는 지점(무릎 각도 약 110~120도)까지 충분히 하강하지 못하는 경우.\n")
        f.write("- 발목 가동성 부족 (Ankle Mobility): 스쿼트 최저점에서 발목 각도(배굴곡)가 약 20도 미만으로, 가동 범위가 제한되는 경우.\n\n")

    print(f"리포트가 '{report_path}'에 저장되었습니다.")

def run_squat_analysis(duration_seconds=120, stop_callback=None, frame_callback=None):
    """실시간 카메라를 통한 스쿼트 분석 함수 (TTS 피드백 포함)
    
    Args:
        duration_seconds (int): 분석할 시간 (초), 기본값 120초 (2분)
        stop_callback (callable): 분석 중지 여부를 확인하는 콜백 함수
        frame_callback (callable): 처리된 프레임을 GUI로 전달하는 콜백 함수
    """
    
    # 중지 플래그 초기화
    run_squat_analysis._stop_analysis = False
    
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
    output_video_path = os.path.join(output_dir, f"squat_realtime_tts_analysis_{timestamp}.mp4")
    output_report_path = os.path.join(output_dir, f"squat_realtime_tts_report_{timestamp}.txt")
    
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))
    
    try:
        # TTS 피드백 매니저 초기화
        print("TTS 매니저 초기화 중...")
        tts_manager = UniversalTTS()
        
        # 스쿼트 등급 평가기 초기화
        print("스쿼트 등급 평가기 초기화 중...")
        grader = ComprehensiveSquatGrader()
        
        # 변수 초기화
        counter = 0 
        stage = None
        all_rep_results = []
        current_rep_errors = set()
        last_rep_grade = "N/A"
        rep_start_hip_y = 0
        
        print("초기화 완료!")
        
    except Exception as e:
        print(f"초기화 오류: {str(e)}")
        cap.release()
        out.release()
        return None, None
    
    # 타이머 설정
    start_time = time.time()
    recording_duration = duration_seconds
    
    print(f"스쿼트 분석을 시작합니다. {duration_seconds}초간 카메라가 켜집니다.")
    print("TTS 피드백이 실시간으로 제공됩니다!")
    print("스쿼트 동작을 시작하세요!")
    print("종료하려면 'q'를 누르세요.")
    
    # 시작 안내 메시지
    tts_manager.add_feedback("시작", "encouragement")
    
    while cap.isOpened():
        try:
            ret, frame = cap.read()
            if not ret: 
                print("프레임을 읽을 수 없습니다.")
                break

            # 좌우반전 제거 - GUI에서 한 번만 반전하도록
            # frame = cv2.flip(frame, 1)  # 주석 처리

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
            
            # GUI로 프레임 전달
            if frame_callback:
                frame_callback(image.copy())
            
            out.write(image)
            continue

        try:
            landmarks = results.pose_landmarks.landmark
            h, w, _ = image.shape

            lm_data = {
                'left_shoulder': [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x * w,
                                  landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y * h],
                'left_hip': [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x * w,
                             landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y * h],
                'left_knee': [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x * w,
                              landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y * h],
                'left_ankle': [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x * w,
                               landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y * h],
                'left_foot_index': [landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].x * w,
                                    landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].y * h],
                'right_shoulder': [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x * w,
                                   landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y * h],
                'right_hip': [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x * w,
                              landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y * h],
                'right_knee': [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x * w,
                               landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y * h],
                'right_ankle': [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x * w,
                                landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y * h],
                'right_foot_index': [landmarks[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value].x * w,
                                     landmarks[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value].y * h],
                'left_heel_visibility': landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].visibility,
                'right_heel_visibility': landmarks[mp_pose.PoseLandmark.RIGHT_HEEL.value].visibility,
            }

            angles = {}
            use_left_side = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].visibility > landmarks[
                mp_pose.PoseLandmark.RIGHT_HIP.value].visibility
            if use_left_side:
                angles['hip'] = calculate_angle(lm_data['left_shoulder'], lm_data['left_hip'], lm_data['left_knee'])
                angles['knee'] = calculate_angle(lm_data['left_hip'], lm_data['left_knee'], lm_data['left_ankle'])
                angles['ankle'] = calculate_angle(lm_data['left_knee'], lm_data['left_ankle'],
                                                  lm_data['left_foot_index'])
                angles['torso'] = calculate_angle(lm_data['left_hip'], lm_data['left_shoulder'],
                                                  [lm_data['left_shoulder'][0], lm_data['left_shoulder'][1] - 1])
            else:
                angles['hip'] = calculate_angle(lm_data['right_shoulder'], lm_data['right_hip'], lm_data['right_knee'])
                angles['knee'] = calculate_angle(lm_data['right_hip'], lm_data['right_knee'], lm_data['right_ankle'])
                angles['ankle'] = calculate_angle(lm_data['right_knee'], lm_data['right_ankle'],
                                                   lm_data['right_foot_index'])
                angles['torso'] = calculate_angle(lm_data['right_hip'], lm_data['right_shoulder'],
                                                   [lm_data['right_shoulder'][0], lm_data['right_shoulder'][1] - 1])

            if 'knee' in angles:
                knee_angle = angles['knee']

                if knee_angle > 160:
                    if stage == 'down':
                        final_grade = grader.get_grade_from_errors(list(current_rep_errors))
                        all_rep_results.append(
                            {'rep': counter, 'grade': final_grade, 'errors': list(current_rep_errors)})
                        last_rep_grade = final_grade

                        # 스쿼트 완료 시 격려 메시지
                        if counter > 0:
                            tts_manager.add_encouragement(counter)

                        current_rep_errors.clear()
                    stage = "up"

                if knee_angle < 100 and stage == 'up':
                    stage = "down"
                    counter += 1
                    rep_start_hip_y = (lm_data['left_hip'][1] + lm_data['right_hip'][1]) / 2

                current_phase = ""
                if stage == "up":
                    current_phase = "ASCEND" if knee_angle < 170 else "READY"
                elif stage == "down":
                    current_phase = "BOTTOM" if knee_angle < 90 else "DESCEND"

                if stage == "down" or stage == "up":
                    errors_in_frame = grader.evaluate_errors(lm_data, angles, current_phase, rep_start_hip_y)

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

        # ------------------ 화면 표시 정보 수정 ------------------
        # 스켈레톤 그리기 (포즈 랜드마크가 있을 때만)
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                      mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                                      mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2))

        # 상단 정보 박스
        cv2.rectangle(image, (0, 0), (frame_width, 120), (245, 117, 16), -1)

        # 타이머 표시
        cv2.putText(image, f'TIME: {remaining_time:.1f}s', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2, cv2.LINE_AA)

        # REPS
        cv2.putText(image, 'REPS', (int(frame_width * 0.3), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255),
                    2, cv2.LINE_AA)
        cv2.putText(image, str(counter), (int(frame_width * 0.3), 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5,
                    (255, 255, 255), 3, cv2.LINE_AA)

        # PHASE
        cv2.putText(image, 'PHASE', (int(frame_width * 0.5), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255),
                    2, cv2.LINE_AA)
        cv2.putText(image, current_phase if 'current_phase' in locals() else "READY",
                    (int(frame_width * 0.5), 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3,
                    cv2.LINE_AA)

        # LAST REP GRADE
        cv2.putText(image, 'GRADE', (int(frame_width * 0.7), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, last_rep_grade, (int(frame_width * 0.7), 65), cv2.FONT_HERSHEY_SIMPLEX, 1.5,
                    (255, 255, 255), 3, cv2.LINE_AA)

        # TTS 상태 표시
        cv2.putText(image, 'TTS: ON', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

        # 하단 안내 메시지
        cv2.rectangle(image, (0, frame_height - 50), (frame_width, frame_height), (0, 0, 0), -1)
        cv2.putText(image, 'Press Q to quit early | TTS Feedback Active', (10, frame_height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        # ----------------------------------------------------

        # GUI로 처리된 프레임 전달 (저장되는 영상과 동일)
        if frame_callback:
            frame_callback(image.copy())  # image는 처리된 프레임 (BGR 형식)

        # 동영상 저장
        out.write(image)

        # macOS에서는 GUI 없이 콘솔 모드로 실행
        print(
            f"프레임 처리 중... REP: {counter}, PHASE: {current_phase if 'current_phase' in locals() else 'READY'}, GRADE: {last_rep_grade}")

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
                cv2.namedWindow('Real-time Squat Analysis with TTS', cv2.WINDOW_NORMAL)
                cv2.resizeWindow('Real-time Squat Analysis with TTS', 1280, 720)
                cv2.imshow('Real-time Squat Analysis with TTS', image)

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
            print(f"스쿼트 분석 진행 중... 시간: {remaining_time:.1f}초, 반복: {counter}")
            _last_status_time = int(time.time())

        # 분석 중지 체크 (전역 변수로 제어)
        if hasattr(run_squat_analysis, '_stop_analysis') and run_squat_analysis._stop_analysis:
            print("분석이 중지되었습니다.")
            break

        # 분석 중지 체크 (콜백 함수로 제어)
        if stop_callback and stop_callback():
            print("분석이 중지되었습니다.")
            break

        # 더 자주 중지 체크 (매 10프레임마다)
        if counter % 10 == 0 and stop_callback and stop_callback():
            print("분석이 중지되었습니다.")
            break

    # 마지막 스쿼트가 완료되지 않았다면 처리
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
    print(f"총 {counter}회의 스쿼트를 분석했습니다.")
    print("TTS 피드백이 실시간으로 제공되었습니다.")
    
    # 결과 파일 경로 반환
    return output_video_path, output_report_path
def main():
    """기존 main 함수 (호환성 유지)"""
    video_path, report_path = run_squat_analysis(120)  # 기본 2분
    if video_path and report_path:
        print(f"분석 완료: {video_path}, {report_path}")
    else:
        print("분석 실패")

if __name__ == "__main__":
    main()