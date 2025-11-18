import cv2
import mediapipe as mp
import numpy as np
from pytube import YouTube
import urllib.request
import os
import ssl

# SSL 인증서 문제 해결
ssl._create_default_https_context = ssl._create_unverified_context

# MediaPipe Pose 모델 초기화
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

def calculate_angle(a, b, c):
    """세 점 사이의 각도를 계산하는 함수"""
    a = np.array(a)  # 첫 번째 점
    b = np.array(b)  # 중간 점 (꼭짓점)
    c = np.array(c)  # 세 번째 점

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
              np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

def analyze_youtube_video(youtube_url):
    """YouTube 영상에서 포즈 분석을 수행하는 함수"""
    print(f"YouTube 영상 분석을 시작합니다: {youtube_url}")
    
    try:
        # YouTube 영상 정보 가져오기
        print("YouTube 영상 정보를 가져오는 중...")
        yt = YouTube(youtube_url)
        print(f"영상 제목: {yt.title}")
        print(f"영상 길이: {yt.length}초")
        
        # 가장 좋은 품질의 스트림 선택
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if stream is None:
            print("사용 가능한 스트림을 찾을 수 없습니다.")
            return False
            
        print(f"선택된 스트림: {stream.resolution}")
        
        # 영상 다운로드
        print("영상을 다운로드하는 중...")
        video_path = yt.streams.first().download(filename="temp_youtube_video.mp4")
        print(f"다운로드 완료: {video_path}")
        
        # 영상 파일 열기
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print("영상 파일을 열 수 없습니다.")
            return False
            
        print("포즈 분석을 시작합니다. 'q' 키를 눌러 종료하세요.")
        
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("영상이 끝났습니다.")
                break
                
            frame_count += 1
            
            # BGR 이미지를 RGB로 변환
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False

            # Pose 감지 수행
            results = pose.process(image)

            # 이미지를 다시 BGR로 변환
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            # 랜드마크 추출 및 각도 계산
            if results.pose_landmarks:
                try:
                    landmarks = results.pose_landmarks.landmark

                    # 오른쪽 어깨, 팔꿈치, 손목 좌표 추출
                    shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                                landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                    elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                             landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
                    wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                             landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]

                    # 팔꿈치 각도 계산
                    angle = calculate_angle(shoulder, elbow, wrist)

                    # 각도 정보 시각화
                    h, w, _ = image.shape
                    elbow_pixel = tuple(np.multiply(elbow, [w, h]).astype(int))
                    
                    # 각도에 따른 색상 변경
                    if angle > 150:
                        color = (0, 255, 0)  # 초록색 (좋은 각도)
                    elif angle > 90:
                        color = (0, 255, 255)  # 노란색 (보통 각도)
                    else:
                        color = (0, 0, 255)  # 빨간색 (주의 각도)
                    
                    cv2.putText(image, f"Right Arm Angle: {int(angle)}°",
                                (elbow_pixel[0] - 50, elbow_pixel[1] - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
                    
                    # 왼쪽 팔도 분석
                    left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                    landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                    left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                                 landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                    left_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                                 landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
                    
                    left_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
                    left_elbow_pixel = tuple(np.multiply(left_elbow, [w, h]).astype(int))
                    
                    if left_angle > 150:
                        left_color = (0, 255, 0)
                    elif left_angle > 90:
                        left_color = (0, 255, 255)
                    else:
                        left_color = (0, 0, 255)
                    
                    cv2.putText(image, f"Left Arm Angle: {int(left_angle)}°",
                                (left_elbow_pixel[0] - 50, left_elbow_pixel[1] - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, left_color, 2, cv2.LINE_AA)
                    
                    # 상태 메시지
                    cv2.putText(image, f"YouTube Pose Analysis - Frame {frame_count}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    cv2.putText(image, "Press 'q' to quit", 
                               (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

                except Exception as e:
                    cv2.putText(image, f"Landmark Error: {str(e)[:30]}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                cv2.putText(image, "No pose detected", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

            # 랜드마크 그리기
            mp_drawing.draw_landmarks(
                image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            cv2.imshow('YouTube Pose Analysis', image)

            # 'q' 키를 누르면 종료
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        
        # 임시 파일 삭제
        if os.path.exists(video_path):
            os.remove(video_path)
            print("임시 파일이 삭제되었습니다.")
            
        return True
        
    except Exception as e:
        print(f"YouTube 영상 분석 중 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    print("=== YouTube 포즈 분석 프로그램 ===")
    print("기본 YouTube 영상을 사용합니다...")
    
    # 기본 YouTube 영상 (운동 관련)
    youtube_url = "https://www.youtube.com/watch?v=pcyrlkHXAdE"
    print(f"분석할 영상: {youtube_url}")
    
    # YouTube 영상 분석 실행
    success = analyze_youtube_video(youtube_url)
    
    if success:
        print("포즈 분석이 완료되었습니다!")
    else:
        print("포즈 분석에 실패했습니다.")

if __name__ == "__main__":
    main()
