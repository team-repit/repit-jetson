import cv2
import mediapipe as mp
import numpy as np
from pytube import YouTube # pytube 라이브러리 추가
import urllib.request
import os

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

# 웹캠 또는 샘플 비디오 사용
print("비디오 소스를 초기화하는 중...")
print("웹캠 권한이 필요합니다. 시스템 환경설정 > 보안 및 개인정보 보호 > 개인정보 보호 > 카메라에서 터미널에 권한을 허용해주세요.")

# 먼저 웹캠을 시도
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("웹캠을 사용할 수 없습니다. 대안을 시도합니다...")
    
    # 대안 1: 기존 샘플 비디오 파일이 있는지 확인
    if os.path.exists('pose_sample.mp4'):
        print("기존 샘플 비디오를 사용합니다...")
        cap = cv2.VideoCapture('pose_sample.mp4')
    elif os.path.exists('real_pose_sample.mp4'):
        print("실제 사람 포즈 샘플 비디오를 사용합니다...")
        cap = cv2.VideoCapture('real_pose_sample.mp4')
    else:
        # 실제 사람 포즈 샘플 비디오 다운로드 시도
        print("실제 사람 포즈 샘플 비디오를 다운로드 시도합니다...")
        try:
            # 공개 도메인 샘플 비디오 URL (실제 사람 포즈)
            sample_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
            print("샘플 비디오를 다운로드하는 중...")
            urllib.request.urlretrieve(sample_url, 'real_pose_sample.mp4')
            print("샘플 비디오 다운로드 완료!")
            cap = cv2.VideoCapture('real_pose_sample.mp4')
        except Exception as e:
            print(f"샘플 비디오 다운로드 실패: {e}")
            print("대체 샘플 비디오를 생성합니다...")
        
        # 더 현실적인 사람 포즈 샘플 비디오 생성
        height, width = 480, 640
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter('pose_sample.mp4', fourcc, 20.0, (width, height))
        
        # 15초간의 샘플 비디오 생성 (더 현실적인 포즈)
        for i in range(300):  # 300프레임 (15초)
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # 배경 그라데이션
            for y in range(height):
                color = int(40 + (y / height) * 30)
                frame[y, :] = [color, color, color + 15]
            
            # 사람 모양 그리기 (더 현실적인 비율)
            center_x = width // 2
            center_y = height // 2
            
            # 머리 (더 큰 원)
            head_radius = 25
            head_y = center_y - 140 + int(8 * np.sin(i * 0.08))
            cv2.circle(frame, (center_x, head_y), head_radius, (255, 220, 180), -1)
            cv2.circle(frame, (center_x, head_y), head_radius, (200, 180, 140), 2)
            
            # 몸통 (더 현실적인 비율)
            body_start = (center_x, head_y + head_radius)
            body_end = (center_x, center_y + 60)
            cv2.line(frame, body_start, body_end, (100, 150, 255), 10)
            
            # 팔 (더 자연스러운 움직임)
            arm_angle = i * 0.15
            arm_length = 80
            
            # 왼쪽 팔 (더 자연스러운 각도)
            left_arm_end = (
                int(center_x - arm_length * np.cos(arm_angle + 0.5)),
                int(center_y - 10 + arm_length * np.sin(arm_angle + 0.5))
            )
            cv2.line(frame, (center_x, center_y - 10), left_arm_end, (100, 150, 255), 8)
            
            # 오른쪽 팔 (다른 각도)
            right_arm_end = (
                int(center_x + arm_length * np.cos(arm_angle + 2.0)),
                int(center_y - 10 + arm_length * np.sin(arm_angle + 2.0))
            )
            cv2.line(frame, (center_x, center_y - 10), right_arm_end, (100, 150, 255), 8)
            
            # 다리 (더 현실적인 비율)
            leg_start = (center_x, center_y + 60)
            left_leg_end = (center_x - 25, center_y + 160)
            right_leg_end = (center_x + 25, center_y + 160)
            cv2.line(frame, leg_start, left_leg_end, (100, 150, 255), 8)
            cv2.line(frame, leg_start, right_leg_end, (100, 150, 255), 8)
            
            # 손과 발 추가
            cv2.circle(frame, left_arm_end, 8, (255, 220, 180), -1)
            cv2.circle(frame, right_arm_end, 8, (255, 220, 180), -1)
            cv2.circle(frame, left_leg_end, 10, (100, 150, 255), -1)
            cv2.circle(frame, right_leg_end, 10, (100, 150, 255), -1)
            
            # 텍스트 추가
            cv2.putText(frame, f"Pose Analysis Demo {i//20 + 1}/15", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, "Press 'q' to quit", (10, height - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
            
            out.write(frame)
        
        out.release()
        print("샘플 비디오가 생성되었습니다.")
        
        # 생성된 비디오 파일 사용
        cap = cv2.VideoCapture('pose_sample.mp4')
    
    if not cap.isOpened():
        print("비디오 파일을 열 수 없습니다.")
        exit()
    
    print("샘플 비디오가 성공적으로 열렸습니다.")
    print("💡 팁: 더 정확한 포즈 분석을 위해 웹캠 권한을 허용하거나 실제 사람이 있는 비디오를 사용하세요.")
else:
    print("웹캠이 성공적으로 열렸습니다.")
    print("실시간 포즈 분석을 시작합니다!")

print("'q' 키를 눌러 종료하세요.")
print("\n💡 더 정확한 포즈 분석을 위한 옵션:")
print("1. 웹캠 권한 허용: 시스템 환경설정 > 보안 및 개인정보 보호 > 개인정보 보호 > 카메라")
print("2. 로컬 비디오 파일 사용: 코드에서 cap = cv2.VideoCapture('your_video.mp4')로 변경")
print("3. YouTube 영상: pytube 라이브러리 업데이트 후 YouTube URL 사용")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("스트림이 종료되었거나 프레임을 가져올 수 없습니다.")
        break

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

            # 각도 정보 시각화 (영상 크기에 맞게 좌표 계산)
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
            cv2.putText(image, "Pose Detected! Press 'q' to quit", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        except Exception as e:
            cv2.putText(image, f"Landmark Error: {str(e)[:30]}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    else:
        cv2.putText(image, "No pose detected. Press 'q' to quit", 
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