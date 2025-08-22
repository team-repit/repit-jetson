#!/usr/bin/env python3
"""
카메라 테스트 스크립트
OpenCV와 MediaPipe가 정상 작동하는지 확인
"""

import cv2
import mediapipe as mp
import sys

def test_camera():
    """카메라 테스트"""
    print("🔍 카메라 테스트 시작...")
    
    try:
        # 카메라 초기화
        print("1. 카메라 초기화 중...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ 카메라를 열 수 없습니다.")
            return False
        
        print("✅ 카메라 열기 성공")
        
        # 카메라 설정
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 프레임 읽기 테스트
        print("2. 프레임 읽기 테스트 중...")
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임을 읽을 수 없습니다.")
            cap.release()
            return False
        
        print(f"✅ 프레임 읽기 성공: {frame.shape}")
        
        # MediaPipe 테스트
        print("3. MediaPipe 테스트 중...")
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        # RGB 변환
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        
        if results.pose_landmarks:
            print("✅ MediaPipe 포즈 감지 성공")
        else:
            print("⚠️ MediaPipe 포즈 감지 실패 (사람이 보이지 않음)")
        
        pose.close()
        cap.release()
        
        print("🎉 모든 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
        return False

def test_tts():
    """TTS 테스트"""
    print("\n🔊 TTS 테스트 시작...")
    
    try:
        # gTTS 테스트
        print("1. gTTS 테스트 중...")
        from gtts import gTTS
        import tempfile
        import os
        
        tts = gTTS(text="테스트", lang='ko')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        
        print("✅ gTTS 생성 성공")
        
        # 파일 삭제
        os.unlink(temp_file.name)
        
        return True
        
    except Exception as e:
        print(f"❌ TTS 테스트 실패: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🎯 카메라 및 TTS 테스트")
    print("=" * 50)
    
    camera_ok = test_camera()
    tts_ok = test_tts()
    
    print("\n" + "=" * 50)
    print("📊 테스트 결과")
    print("=" * 50)
    print(f"카메라: {'✅ 정상' if camera_ok else '❌ 오류'}")
    print(f"TTS: {'✅ 정상' if tts_ok else '❌ 오류'}")
    
    if camera_ok and tts_ok:
        print("\n🎉 모든 테스트가 통과했습니다!")
        print("스쿼트 분석을 실행할 수 있습니다.")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")
        print("문제를 해결한 후 다시 시도하세요.")
    
    print("=" * 50) 