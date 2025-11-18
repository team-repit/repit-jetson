import cv2
import mediapipe as mp
import numpy as np
import yt_dlp
import os
import json
import pickle
from datetime import datetime

# MediaPipe Pose 모델 초기화
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

def calculate_angle(a, b, c):
    """세 점 사이의 각도를 계산하는 함수"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
              np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

def extract_pose_landmarks(image):
    """이미지에서 포즈 랜드마크를 추출"""
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb_image)
    
    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        return landmarks
    return None

def save_reference_poses(video_path, output_file="reference_poses.json"):
    """YouTube 영상에서 기준 포즈들을 추출하고 저장"""
    print(f"YouTube 영상에서 기준 포즈를 추출하는 중: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    reference_poses = []
    frame_count = 0
    
    # 10초마다 포즈 추출 (또는 전체 영상에서 균등하게)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    interval = max(1, int(fps * 2))  # 2초마다 추출
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % interval == 0:
            landmarks = extract_pose_landmarks(frame)
            if landmarks:
                # 주요 관절 각도 계산
                pose_data = calculate_pose_angles(landmarks)
                pose_data['frame'] = frame_count
                pose_data['timestamp'] = frame_count / fps
                reference_poses.append(pose_data)
                print(f"기준 포즈 추출: {len(reference_poses)}개")
        
        frame_count += 1
    
    cap.release()
    
    # 기준 포즈 저장
    with open(output_file, 'w') as f:
        json.dump(reference_poses, f, indent=2)
    
    print(f"기준 포즈 {len(reference_poses)}개가 {output_file}에 저장되었습니다.")
    return reference_poses

def calculate_pose_angles(landmarks):
    """포즈 랜드마크에서 주요 각도들을 계산"""
    angles = {}
    
    try:
        # 오른쪽 팔 각도
        right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                         landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        right_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                      landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
        right_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                      landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
        angles['right_arm'] = calculate_angle(right_shoulder, right_elbow, right_wrist)
        
        # 왼쪽 팔 각도
        left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                        landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                     landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        left_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                     landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
        angles['left_arm'] = calculate_angle(left_shoulder, left_elbow, left_wrist)
        
        # 오른쪽 다리 각도
        right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                    landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
        right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,
                     landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
        right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,
                      landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
        angles['right_leg'] = calculate_angle(right_hip, right_knee, right_ankle)
        
        # 왼쪽 다리 각도
        left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                   landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                     landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        angles['left_leg'] = calculate_angle(left_hip, left_knee, left_ankle)
        
    except Exception as e:
        print(f"각도 계산 오류: {e}")
    
    return angles

def find_closest_reference_pose(current_angles, reference_poses):
    """현재 포즈와 가장 유사한 기준 포즈를 찾기"""
    if not reference_poses:
        return None
    
    min_diff = float('inf')
    closest_pose = None
    
    for ref_pose in reference_poses:
        total_diff = 0
        for key in ['right_arm', 'left_arm', 'right_leg', 'left_leg']:
            if key in current_angles and key in ref_pose:
                diff = abs(current_angles[key] - ref_pose[key])
                total_diff += diff
        
        if total_diff < min_diff:
            min_diff = total_diff
            closest_pose = ref_pose
    
    return closest_pose

def compare_poses(current_angles, reference_angles):
    """현재 포즈와 기준 포즈를 비교"""
    comparison = {}
    
    for key in ['right_arm', 'left_arm', 'right_leg', 'left_leg']:
        if key in current_angles and key in reference_angles:
            current = current_angles[key]
            reference = reference_angles[key]
            diff = current - reference
            
            comparison[key] = {
                'current': current,
                'reference': reference,
                'difference': diff,
                'status': 'good' if abs(diff) < 15 else 'needs_improvement'
            }
    
    return comparison

def draw_comparison(image, comparison, landmarks):
    """비교 결과를 이미지에 그리기"""
    h, w, _ = image.shape
    
    # 제목
    cv2.putText(image, "Real-time Pose Comparison", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # 비교 결과 표시
    y_offset = 70
    for key, data in comparison.items():
        color = (0, 255, 0) if data['status'] == 'good' else (0, 0, 255)
        
        text = f"{key}: {data['current']:.1f}° (ref: {data['reference']:.1f}°)"
        cv2.putText(image, text, (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # 차이점 표시
        diff_text = f"Diff: {data['difference']:+.1f}°"
        cv2.putText(image, diff_text, (w - 200, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        y_offset += 30
    
    # 상태 메시지
    good_count = sum(1 for data in comparison.values() if data['status'] == 'good')
    total_count = len(comparison)
    
    status_text = f"Pose Match: {good_count}/{total_count}"
    status_color = (0, 255, 0) if good_count == total_count else (0, 255, 255)
    
    cv2.putText(image, status_text, (10, h - 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    cv2.putText(image, "Press 'q' to quit", (10, h - 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

def real_time_comparison_with_video(reference_poses_file="reference_poses.json", video_file="temp_youtube_video.mp4"):
    """실시간 웹캠과 YouTube 영상을 나란히 비교"""
    print("실시간 포즈 비교를 시작합니다...")
    
    # 기준 포즈 로드
    if not os.path.exists(reference_poses_file):
        print(f"기준 포즈 파일이 없습니다: {reference_poses_file}")
        return False
    
    with open(reference_poses_file, 'r') as f:
        reference_poses = json.load(f)
    
    print(f"기준 포즈 {len(reference_poses)}개를 로드했습니다.")
    
    # 웹캠과 YouTube 영상 시작
    webcam_cap = cv2.VideoCapture(0)
    video_cap = cv2.VideoCapture(video_file)
    
    if not webcam_cap.isOpened():
        print("웹캠을 열 수 없습니다.")
        return False
    
    if not video_cap.isOpened():
        print(f"YouTube 영상을 열 수 없습니다: {video_file}")
        return False
    
    print("웹캠과 YouTube 영상이 시작되었습니다. 'q' 키를 눌러 종료하세요.")
    
    # 영상 크기 조정
    target_width = 640
    target_height = 480
    
    while webcam_cap.isOpened() and video_cap.isOpened():
        # 웹캠 프레임 읽기
        webcam_ret, webcam_frame = webcam_cap.read()
        if not webcam_ret:
            break
        
        # YouTube 영상 프레임 읽기
        video_ret, video_frame = video_cap.read()
        if not video_ret:
            # 영상이 끝나면 처음부터 다시 시작
            video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            video_ret, video_frame = video_cap.read()
        
        # 프레임 크기 조정
        webcam_frame = cv2.resize(webcam_frame, (target_width, target_height))
        video_frame = cv2.resize(video_frame, (target_width, target_height))
        
        # 웹캠 포즈 분석
        webcam_rgb = cv2.cvtColor(webcam_frame, cv2.COLOR_BGR2RGB)
        webcam_results = pose.process(webcam_rgb)
        
        # YouTube 영상 포즈 분석
        video_rgb = cv2.cvtColor(video_frame, cv2.COLOR_BGR2RGB)
        video_results = pose.process(video_rgb)
        
        # 웹캠 포즈 분석 및 비교
        if webcam_results.pose_landmarks:
            webcam_landmarks = webcam_results.pose_landmarks.landmark
            current_angles = calculate_pose_angles(webcam_landmarks)
            
            # 가장 유사한 기준 포즈 찾기
            closest_ref = find_closest_reference_pose(current_angles, reference_poses)
            
            if closest_ref:
                # 포즈 비교
                comparison = compare_poses(current_angles, closest_ref)
                
                # 웹캠에 비교 결과 그리기
                draw_comparison(webcam_frame, comparison, webcam_landmarks)
            
            # 웹캠 랜드마크 그리기
            mp_drawing.draw_landmarks(
                webcam_frame, webcam_results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        else:
            cv2.putText(webcam_frame, "No pose detected", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # YouTube 영상 랜드마크 그리기
        if video_results.pose_landmarks:
            mp_drawing.draw_landmarks(
                video_frame, video_results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        
        # 제목 추가
        cv2.putText(webcam_frame, "YOUR POSE (Webcam)", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(video_frame, "REFERENCE POSE (YouTube)", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 두 영상을 나란히 합치기
        combined_frame = np.hstack((webcam_frame, video_frame))
        
        # 전체 제목
        cv2.putText(combined_frame, "Real-time Pose Comparison", 
                   (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(combined_frame, "Press 'q' to quit", 
                   (10, combined_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        cv2.imshow('Real-time Pose Comparison', combined_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    webcam_cap.release()
    video_cap.release()
    cv2.destroyAllWindows()
    return True

def download_youtube_video(url):
    """YouTube 영상 다운로드"""
    print(f"YouTube 영상을 다운로드하는 중: {url}")
    
    ydl_opts = {
        'format': 'best[height<=720]',
        'outtmpl': 'temp_youtube_video.%(ext)s',
        'noplaylist': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"영상 제목: {info.get('title', 'Unknown')}")
            
            ydl.download([url])
            
            for file in os.listdir('.'):
                if file.startswith('temp_youtube_video.'):
                    print(f"다운로드 완료: {file}")
                    return file
                    
    except Exception as e:
        print(f"다운로드 실패: {e}")
        return None

def main():
    """메인 함수"""
    print("=== 실시간 포즈 비교 프로그램 (사이드바이사이드) ===")
    
    # YouTube 영상 URL
    youtube_url = "https://www.youtube.com/watch?v=pcyrlkHXAdE"
    
    # 1단계: YouTube 영상에서 기준 포즈 추출
    if not os.path.exists("reference_poses.json"):
        print("1단계: YouTube 영상에서 기준 포즈를 추출합니다...")
        video_file = download_youtube_video(youtube_url)
        
        if video_file:
            reference_poses = save_reference_poses(video_file)
            print(f"기준 포즈 추출 완료! 영상 파일을 보관합니다: {video_file}")
        else:
            print("YouTube 영상 다운로드에 실패했습니다.")
            return
    else:
        print("기존 기준 포즈 파일을 사용합니다.")
        # YouTube 영상이 없으면 다시 다운로드
        if not os.path.exists("temp_youtube_video.mp4"):
            print("YouTube 영상을 다시 다운로드합니다...")
            video_file = download_youtube_video(youtube_url)
            if not video_file:
                print("YouTube 영상 다운로드에 실패했습니다.")
                return
    
    # 2단계: 실시간 포즈 비교 (사이드바이사이드)
    print("\n2단계: 실시간 포즈 비교를 시작합니다...")
    print("웹캠 권한이 필요합니다.")
    print("왼쪽: 당신의 자세 (웹캠)")
    print("오른쪽: 기준 자세 (YouTube 영상)")
    
    success = real_time_comparison_with_video()
    
    if success:
        print("포즈 비교가 완료되었습니다!")
    else:
        print("포즈 비교에 실패했습니다.")

if __name__ == "__main__":
    main()
